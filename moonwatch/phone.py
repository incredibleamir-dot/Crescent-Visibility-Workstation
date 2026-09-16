"""Phone link: streams the Android phone's sensors into the app via SensorCast.

The phone runs the SensorCast Android app (https://sensorcast.app) and
broadcasts sensor frames (Rotation Vector + optional GPS).  This desktop class
connects to the SensorCast WebSocket API as a subscriber and re-emits the
frames as Qt signals that LivePage consumes to drive the horizon sky map and,
optionally, the observer location.

    wss://api.sensorcast.app   /socket.io/   namespace /stream/<username>

After connecting, the subscriber must emit ``role`` == ``"subscriber"`` within
5 seconds and keep sending a ``heartbeat`` event every ~20 s.

Frame formats handled: JSON, CSV, COMPACT, TIMESTAMP (see sensorcast.app/docs).
The parsing / quaternion helpers themselves live in ``moonwatch.sensorcast`` so
the desktop link and the capture tool share one definition.
"""

import threading
import time

from PySide6.QtCore import QObject, Signal

from .sensorcast import SERVER, parse_frame, q_to_aim


class PhoneLink(QObject):
    """Subscribe to a SensorCast stream and re-emit Qt signals.

    The socket client runs in a daemon thread; signals are queued to the GUI
    thread automatically by Qt.
    """

    orient = Signal(float, float, float, float, float, float)
    #                                  qx    qy    qz    qw    az   alt
    loc = Signal(float, float, float)                     # lat lon acc-m
    status = Signal(bool, str)                            # connected, username
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._sio = None
        self._stop = threading.Event()
        self._connected = False
        self._seen_plain_rv = False
        self.username = ""

    # ------------------------------------------------------------- lifecycle
    def is_connected(self):
        return self._connected

    def connect_stream(self, username):
        self.disconnect()
        username = (username or "").strip()
        if not username:
            self.error.emit("Enter a SensorCast username first")
            return
        self.username = username
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(username,),
                                        daemon=True)
        self._thread.start()

    def disconnect(self):
        self._stop.set()
        sio = self._sio
        self._sio = None
        if sio is not None:
            try:
                sio.disconnect()
            except Exception:
                pass
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2.0)
        was = self._connected
        self._connected = False
        if was or self.username:
            self.status.emit(False, self.username)

    # --------------------------------------------------------------- socket
    def _run(self, username):
        try:
            import socketio
        except ImportError:
            self.error.emit('Missing dependency: run  '
                            'pip install "python-socketio[client]"')
            self.status.emit(False, username)
            return
        try:
            self._run_client(socketio, username)
        except Exception as exc:
            if not self._stop.is_set():
                self.error.emit("SensorCast connection failed: %s" % exc)
                self.status.emit(False, username)
        finally:
            self._sio = None

    def _run_client(self, socketio, username):
        ns = "/stream/%s" % username
        sio = socketio.Client()
        self._sio = sio

        @sio.event(namespace=ns)
        def connect():
            sio.emit("role", "subscriber", namespace=ns)

        @sio.on("connected", namespace=ns)
        def on_connected(data):
            self._connected = True
            self.status.emit(True, username)

        @sio.on("frame", namespace=ns)
        def on_frame(data):
            self._handle_frame(data)

        @sio.on("publisher_disconnected", namespace=ns)
        def on_pub_gone():
            if not self._stop.is_set():
                self.error.emit("Publisher disconnected - stream ended")
                self.status.emit(False, username)

        @sio.on("connect_error", namespace=ns)
        def on_conn_error(e):
            if not self._stop.is_set():
                self.error.emit("Connection error: %s" % e)
                self.status.emit(False, username)

        @sio.on("auth_error", namespace=ns)
        def on_auth_error(e):
            if not self._stop.is_set():
                self.error.emit("Auth error: %s" % e)
                self.status.emit(False, username)

        @sio.event(namespace=ns)
        def disconnect():
            if self._connected:
                self._connected = False
                self.status.emit(False, username)

        def heartbeat():
            while not self._stop.is_set():
                time.sleep(20)
                if sio.connected:
                    try:
                        sio.emit("heartbeat", namespace=ns)
                    except Exception:
                        pass

        threading.Thread(target=heartbeat, daemon=True).start()

        sio.connect(SERVER, namespaces=[ns], socketio_path="/socket.io/")
        try:
            while not self._stop.is_set() and sio.connected:
                sio.sleep(0.3)
        finally:
            try:
                sio.disconnect()
            except Exception:
                pass
            self._connected = False

    # --------------------------------------------------------------- frames
    def _handle_frame(self, data):
        parsed = parse_frame(data)
        sensor = parsed.get("sensor") or ""
        values = parsed.get("values") or {}
        if not values:
            return
        s_low = str(sensor).lower()

        # --- GPS fix -----------------------------------------------------
        if "gps" in s_low:
            try:
                lat = float(values.get("latitude", values.get("lat")))
                lon = float(values.get("longitude", values.get("lon")))
                acc = float(values.get("accuracy", values.get("acc", -1.0)))
            except (TypeError, ValueError):
                return
            self.loc.emit(lat, lon, acc)
            return

        # --- rotation vector quaternion (absolute heading) ---------------
        if "rotation vector" in s_low:
            try:
                qx = float(values.get("x", 0.0))
                qy = float(values.get("y", 0.0))
                qz = float(values.get("z", 0.0))
                qw = float(values.get("w", -1.0))
            except (TypeError, ValueError):
                return
            if "game" not in s_low:
                self._seen_plain_rv = True
            elif self._seen_plain_rv:
                return                      # prefer the compass RV sensor
            az, alt = q_to_aim(qx, qy, qz, qw)
            self.orient.emit(qx, qy, qz, qw, az, alt)
            return

        # --- euler / legacy orientation (fallback only) ------------------
        if "orientation" in s_low and not self._seen_plain_rv:
            try:
                yaw = float(values.get("yaw", values.get("z",
                          values.get("azimuth", values.get("x")))))
                pitch = float(values.get("pitch", values.get("y")))
            except (TypeError, ValueError):
                return
            self.orient.emit(0.0, 0.0, 0.0, 1.0,
                             (float(yaw) + 180.0) % 360.0, -float(pitch))