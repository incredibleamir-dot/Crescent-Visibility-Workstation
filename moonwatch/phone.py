"""Phone link: streams the Android phone's IMU + GPS into the app.

The phone runs ``phone-app/termux/aim.py`` from Termux, which sends JSON packets
over UDP to this desktop listener on the same Wi-Fi:

    {"type":"orient","t":123.4,"qx":..,"qy":..,"qz":..,"qw":..,
     "az":..,"alt":..}                     aim of the back camera
    {"type":"loc","t":123.4,"lat":..,"lon":..,"acc":..}   GPS fix
    {"type":"ping","t":123.4}              keep-alive heartbeat
    {"type":"disc"}                         broadcast: "are you the server?"

``PhoneLink`` runs one daemon socket thread, parses datagrams and re-emits
Qt signals that LivePage consumes to drive the horizon sky map and, optionally,
the observer location.  ``status`` tracks when packets stop arriving so the UI
can show a live/disconnected indicator.
"""

import json
import socket
import threading
import time

from PySide6.QtCore import QObject, Signal

DEFAULT_PORT = 5555          # UDP port the phone streams to
STALE_SECONDS = 3.0          # no packets for this long  -> "disconnected"


def lan_ip():
    """Best guess of this machine's primary LAN IPv4 address (or None)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


class PhoneLink(QObject):
    """Receive UDP orientation / location packets and re-emit Qt signals.

    The listener thread emits signals directly (Qt queues them across the
    threads automatically), and only updates internal state under no locks
    that the GUI reads through those signals.
    """

    orient = Signal(float, float, float, float, float, float)
    #                                  qx    qy    qz    qw    az   alt
    loc = Signal(float, float, float)                     # lat lon acc-m
    status = Signal(bool, str)                            # connected, peer ip
    error = Signal(str)

    def __init__(self, port=DEFAULT_PORT, parent=None):
        super().__init__(parent)
        self.port = int(port)
        self._sock = None
        self._thread = None
        self._stop = threading.Event()
        self._last = 0.0
        self._connected = False
        self._peer = ""

    # ------------------------------------------------------------- lifecycle
    def start(self):
        if self._thread is not None:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except OSError:
                pass
            sock.bind(("0.0.0.0", self.port))
            sock.settimeout(0.5)
        except OSError as exc:
            self.error.emit("UDP port %d is unavailable: %s" % (self.port, exc))
            return
        self._sock = sock
        self._stop.clear()
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ---------------------------------------------------------------- recv
    def _recv_loop(self):
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(65507)
            except socket.timeout:
                self._check_stale()
                continue
            except OSError:
                break
            self._handle(data, addr)
            self._check_stale()

    def _handle(self, data, addr):
        try:
            msg = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        kind = msg.get("type")
        if kind == "disc":
            self._reply_discovery(addr)
            self._note_seen(addr)
        elif kind == "orient":
            self._note_seen(addr)
            self.orient.emit(
                float(msg.get("qx", 0.0)), float(msg.get("qy", 0.0)),
                float(msg.get("qz", 0.0)), float(msg.get("qw", 1.0)),
                float(msg.get("az", 0.0)), float(msg.get("alt", 0.0)))
        elif kind == "loc":
            self._note_seen(addr)
            self.loc.emit(float(msg.get("lat", 0.0)),
                          float(msg.get("lon", 0.0)),
                          float(msg.get("acc", -1.0)))
        elif kind == "ping":
            self._note_seen(addr)

    def _note_seen(self, addr):
        self._last = time.time()
        if not self._connected:
            self._connected = True
            self._peer = addr[0]
            self.status.emit(True, self._peer)

    def _check_stale(self):
        if self._connected and time.time() - self._last > STALE_SECONDS:
            self._connected = False
            self.status.emit(False, self._peer)
            return True
        return False

    def _reply_discovery(self, addr):
        ip = lan_ip()
        if not ip:
            return
        try:
            self._sock.sendto(json.dumps(
                {"type": "disc_reply", "ip": ip, "name": "moonwatch"}
            ).encode("utf-8"), (addr[0], addr[1]))
        except OSError:
            pass