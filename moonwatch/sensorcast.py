"""SensorCast WebSocket phone-link protocol (framework-free helpers).

SensorCast (https://sensorcast.app) broadcasts phone sensor frames over a
Socket.IO WebSocket API:

    wss://api.sensorcast.app   /socket.io/   namespace /stream/<username>

After connecting, a subscriber must emit ``role`` == ``"subscriber"`` within
5 seconds and keep sending a ``heartbeat`` event every ~20 s.

This module holds the pure parsing / vector helpers shared by the desktop link
(``phone.py``) and the command-line capture tool (``tools/sensorcast_capture.py``)
so the wire format is defined exactly once.  It contains no Qt or network code.
"""

import json
import math
import re
import time

SERVER = "https://api.sensorcast.app"


def q_to_aim(qx, qy, qz, qw=-1.0):
    """(az, alt) the phone's back camera points at, from the Android
    rotation-vector quaternion (device -> world in east-north-up)."""
    if qw in (None, -1.0):
        qw = math.sqrt(max(0.0, 1.0 - (qx * qx + qy * qy + qz * qz)))
    vx, vy, vz = 0.0, 0.0, -1.0                    # device -Z (back camera)
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    ox = vx + qw * tx + (qy * tz - qz * ty)        # world: east
    oy = vy + qw * ty + (qz * tx - qx * tz)        # world: north
    oz = vz + qw * tz + (qx * ty - qy * tx)        # world: up
    az = (math.degrees(math.atan2(ox, oy)) + 360.0) % 360.0
    alt = math.degrees(math.asin(max(-1.0, min(1.0, oz))))
    return az, alt


def parse_frame(raw):
    """Best-effort parse of any SensorCast frame.

    Returns {"sensor":.., "type":.., "timestamp":.., "values":{..}}.
    """
    if isinstance(raw, dict):
        return raw

    s = str(raw).strip()

    if s.startswith("{"):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

    if s.startswith(",") and "," in s:                      # CSV format
        parts = s.split(",")
        try:
            ts = int(parts[0])
            sensor = parts[1]
            n = len(parts) - 2
            half = n // 2
            fields = parts[2: 2 + half]
            values = [float(v) for v in parts[2 + half:]]
            return {"sensor": sensor, "type": 0, "timestamp": ts,
                    "values": dict(zip(fields, values))}
        except (ValueError, IndexError):
            pass

    if ";" in s:                                        # COMPACT/TIMESTAMP
        m = re.match(r"^(\d+);(.+);(.+):(.+)$", s)
        if m:
            ts, sensor, fields_str, vals_str = (int(m.group(1)), m.group(2),
                                                m.group(3), m.group(4))
            fields = fields_str.split(",")
            values = [float(v) for v in vals_str.split(",")]
            return {"sensor": sensor, "type": 0, "timestamp": ts,
                    "values": dict(zip(fields, values))}
        m2 = re.match(r"^(.+);(.+):(.+)$", s)
        if m2:
            left, sensor, rest = m2.group(1), m2.group(2), m2.group(3)
            fields = sensor.split(",")
            values = [float(v) for v in rest.split(",")]
            ts = int(left) if left.isdigit() else int(time.time() * 1000)
            return {"sensor": fields[0] if len(fields) == 1 else left,
                    "type": 0, "timestamp": ts,
                    "values": dict(zip(fields, values))}

    return {"sensor": "unknown", "type": -1,
            "timestamp": int(time.time() * 1000), "values": {}, "raw": s}