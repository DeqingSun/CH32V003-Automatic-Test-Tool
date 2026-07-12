#!/usr/bin/env python3
"""Remote access web UI for the CH32V003 automatic test jig."""

from __future__ import annotations

import asyncio
import base64
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
AUTO_TEST = ROOT.parent / "autoTestCode"
sys.path.insert(0, str(AUTO_TEST))

from lib.ch32v003_test_target import Ch32V003_test_target  # noqa: E402
from access_queue import (  # noqa: E402
    CLIENT_COOKIE,
    access,
    get_client_id,
    require_holder,
    set_client_cookie,
)

STATIC_DIR = ROOT / "static"
PORT = int(os.environ.get("REMOTE_ACCESS_PORT", "8000"))
DUT_FLASH_MAX_BYTES = 16384  # CH32V003 code flash size

# SSOP20 physical layout (top view, pin 1 top-left)
DUT_LEFT = [
    {"name": "PD4", "pin": 1},
    {"name": "PD5", "pin": 2},
    {"name": "PD6", "pin": 3},
    {"name": "PD7", "pin": 4},
    {"name": "PA1", "pin": 5},
    {"name": "PA2", "pin": 6},
    {"name": "VSS", "pin": 7},
    {"name": "PD0", "pin": 8},
    {"name": "VDD", "pin": 9},
    {"name": "PC0", "pin": 10},
]
DUT_RIGHT = [
    {"name": "PD3", "pin": 20},
    {"name": "PD2", "pin": 19},
    {"name": "PD1", "pin": 18},
    {"name": "PC7", "pin": 17},
    {"name": "PC6", "pin": 16},
    {"name": "PC5", "pin": 15},
    {"name": "PC4", "pin": 14},
    {"name": "PC3", "pin": 13},
    {"name": "PC2", "pin": 12},
    {"name": "PC1", "pin": 11},
]

PROBE_NETS = [f"X{i}" for i in range(7)]
LINKE_NETS = [
    "WCH_LINKE_SWDIO",
    "WCH_LINKE_SWCLK",
    "WCH_LINKE_TX",
    "WCH_LINKE_RX",
    "WCH_LINKE_RST",
]
CONTROLLER_Y = [f"305_PA{i}" for i in range(8)]

# Remote matrix UI must not route power rails or LinkE programmer nets.
MATRIX_X_BLOCKED = frozenset({"VSS", "VDD", *LINKE_NETS})


def assert_matrix_x_allowed(name: str) -> None:
    if name in MATRIX_X_BLOCKED or name.startswith("WCH_LINKE_"):
        raise HTTPException(
            status_code=400,
            detail=f"Matrix X net not allowed from remote UI: {name}",
        )


class DeviceSession:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.target = Ch32V003_test_target()
        self.connected = False
        self.busy = "idle"  # idle | la | analog | flash
        self.matrix: set[tuple[int, int]] = set()
        self.la_status: dict[str, Any] = {"state": "idle"}
        self.analog_status: dict[str, Any] = {"state": "idle"}
        self.la_result: Optional[dict[str, Any]] = None
        self.analog_result: Optional[dict[str, Any]] = None
        self._capture_thread: Optional[threading.Thread] = None

    def tool(self):
        return self.target.test_tool

    def is_serial_open(self) -> bool:
        return self.tool().serial_port is not None

    def reconnect(self) -> bool:
        with self.lock:
            if self.busy != "idle":
                return False
            self.tool().disconnect()
            self.connected = False
            self.matrix.clear()
            ok = self.tool().connect()
            if not ok:
                return False
            if not self.tool().initailize(0.5):
                self.tool().disconnect()
                return False
            self.connected = True
            self.matrix.clear()
            return True

    def require_connected(self) -> None:
        if not self.connected or not self.is_serial_open():
            raise HTTPException(status_code=503, detail="Controller not connected")

    def require_idle(self) -> None:
        if self.busy != "idle":
            raise HTTPException(status_code=409, detail=f"Busy: {self.busy}")

    def resolve_x(self, name: str) -> int:
        assert_matrix_x_allowed(name)
        if name not in self.target.map_dict:
            raise HTTPException(status_code=400, detail=f"Unknown net: {name}")
        if name.startswith("305_PA"):
            raise HTTPException(status_code=400, detail="X side cannot be a controller Y pin")
        return self.target.map_dict[name]

    def resolve_y(self, name: str) -> int:
        if name not in CONTROLLER_Y:
            raise HTTPException(status_code=400, detail=f"Y must be one of {CONTROLLER_Y}")
        return self.target.map_dict[name]

    def matrix_state(self) -> list[dict[str, Any]]:
        reverse = {v: k for k, v in self.target.map_dict.items() if not k.startswith("305_PA")}
        y_names = {self.target.map_dict[n]: n for n in CONTROLLER_Y}
        connections = []
        for x, y in sorted(self.matrix):
            connections.append({
                "x": x,
                "y": y,
                "x_name": reverse.get(x, f"X{x}"),
                "y_name": y_names.get(y, f"305_PA{y}"),
            })
        return connections


session = DeviceSession()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        session.reconnect()
    except Exception:
        session.connected = False
    yield


app = FastAPI(title="CH32V003 Remote Access", lifespan=lifespan)


@app.middleware("http")
async def ensure_client_cookie(request: Request, call_next):
    client_id = request.cookies.get(CLIENT_COOKIE) or str(uuid.uuid4())
    request.state.client_id = client_id
    response = await call_next(request)
    if CLIENT_COOKIE not in request.cookies:
        set_client_cookie(response, client_id)
    return response


def _require_control(request: Request) -> str:
    return require_holder(request, session.busy)


# ---- request models ----

class MatrixConnectBody(BaseModel):
    x_name: str
    y_name: str


class DigitalWriteBody(BaseModel):
    pin: int = Field(ge=0, le=7)
    value: bool


class DigitalReadBody(BaseModel):
    pin: int = Field(ge=0, le=7)


class DigitalReadManyBody(BaseModel):
    pins: list[int] = Field(min_length=1, max_length=8)


class AnalogWriteBody(BaseModel):
    pin: int = Field(ge=0, le=7)
    value: int = Field(ge=0, le=4095)


class AnalogReadBody(BaseModel):
    pin: int = Field(ge=0, le=7)


class LaStartBody(BaseModel):
    rate_hz: int = Field(gt=0)
    sample_count: int = Field(gt=0, le=131072)


class AnalogStartBody(BaseModel):
    rate_hz: int = Field(gt=0)
    sample_count: int = Field(gt=0, le=65536)
    channel_mask: int = Field(ge=1, le=255)


# ---- helpers ----

def pack_digital_samples(samples_channels: list[list[int]]) -> str:
    """Pack 8 channel bitstreams into one byte per time sample, base64."""
    if not samples_channels or not samples_channels[0]:
        return ""
    n = len(samples_channels[0])
    raw = bytearray(n)
    for t in range(n):
        b = 0
        for ch in range(8):
            if samples_channels[ch][t]:
                b |= (1 << ch)
        raw[t] = b
    return base64.b64encode(raw).decode("ascii")


def pack_analog_samples(samples_by_channel: list[list[int]]) -> list[str]:
    """Pack each channel as little-endian uint16 base64."""
    packed = []
    for channel_samples in samples_by_channel:
        raw = bytearray(len(channel_samples) * 2)
        for i, value in enumerate(channel_samples):
            raw[i * 2] = value & 0xFF
            raw[i * 2 + 1] = (value >> 8) & 0xFF
        packed.append(base64.b64encode(raw).decode("ascii"))
    return packed


def digital_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "kind": "digital",
        "sample_count": result["sample_count"],
        "rate_hz": result["rate_hz"],
        "samples_b64": pack_digital_samples(result["samples"]),
    }


def analog_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "kind": "analog",
        "sample_count": result["sample_count"],
        "rate_hz": result["rate_hz"],
        "channel_mask": result["channel_mask"],
        "channels": result["channels"],
        "samples_b64": pack_analog_samples(result["samples"]),
    }


# ---- status / pins ----

@app.get("/api/status")
def api_status(request: Request):
    port = None
    if session.is_serial_open():
        try:
            port = session.tool().serial_port.port
        except Exception:
            port = None
    client_id = get_client_id(request)
    access_info = access.snapshot(client_id, session.busy)
    return {
        "connected": session.connected and session.is_serial_open(),
        "serial_number": "CH32V30x",
        "port": port,
        "usb_location": session.tool().usb_location,
        "busy": session.busy,
        "la": session.la_status,
        "analog": session.analog_status,
        "access": access_info,
    }


@app.post("/api/access/claim")
def api_access_claim(request: Request):
    client_id = get_client_id(request)
    info = access.claim(client_id, session.busy)
    return {"ok": True, "access": info}


@app.post("/api/access/heartbeat")
def api_access_heartbeat(request: Request):
    client_id = get_client_id(request)
    info = access.heartbeat(client_id, session.busy)
    return {"ok": True, "access": info}


@app.post("/api/access/leave")
def api_access_leave(request: Request):
    client_id = get_client_id(request)
    info = access.leave(client_id, session.busy)
    return {"ok": True, "access": info}


@app.post("/api/reconnect")
def api_reconnect(request: Request):
    _require_control(request)
    session.require_idle()
    ok = session.reconnect()
    if not ok:
        raise HTTPException(status_code=503, detail="Failed to connect to CH32V305 controller")
    return {"ok": True, "connected": True}


@app.get("/api/pins")
def api_pins():
    # Omit LinkE from the public pin catalog (flash still uses them internally).
    return {
        "dut_left": DUT_LEFT,
        "dut_right": DUT_RIGHT,
        "probe": PROBE_NETS,
        "linke": [],
        "controller_y": CONTROLLER_Y,
        "map": {
            k: v for k, v in session.target.map_dict.items()
            if k not in MATRIX_X_BLOCKED and not k.startswith("WCH_LINKE_")
        },
    }


# ---- matrix ----

@app.post("/api/init")
def api_init(request: Request):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    with session.lock:
        ok = session.tool().initailize(0.5)
        if not ok:
            raise HTTPException(status_code=500, detail="Init failed")
        session.matrix.clear()
    return {"ok": True, "connections": []}


@app.get("/api/matrix/state")
def api_matrix_state():
    return {"connections": session.matrix_state()}


@app.post("/api/matrix/connect")
def api_matrix_connect(request: Request, body: MatrixConnectBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    x = session.resolve_x(body.x_name)
    y = session.resolve_y(body.y_name)
    with session.lock:
        ok = session.tool().connect_pins(x, y, 0.5)
        if not ok:
            raise HTTPException(status_code=500, detail="Connect failed")
        session.matrix.add((x, y))
    return {"ok": True, "connections": session.matrix_state()}


@app.post("/api/matrix/disconnect")
def api_matrix_disconnect(request: Request, body: MatrixConnectBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    x = session.resolve_x(body.x_name)
    y = session.resolve_y(body.y_name)
    with session.lock:
        ok = session.tool().disconnect_pins(x, y, 0.5)
        if not ok:
            raise HTTPException(status_code=500, detail="Disconnect failed")
        session.matrix.discard((x, y))
    return {"ok": True, "connections": session.matrix_state()}


# ---- GPIO ----

@app.post("/api/gpio/digital_write")
def api_digital_write(request: Request, body: DigitalWriteBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    with session.lock:
        ok = session.tool().digital_write(body.pin, body.value, 0.5)
    if not ok:
        raise HTTPException(status_code=500, detail="Digital write failed")
    return {"ok": True, "pin": body.pin, "value": body.value}


@app.post("/api/gpio/digital_read")
def api_digital_read(request: Request, body: DigitalReadBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    with session.lock:
        value = session.tool().digital_read(body.pin, 0.5)
    if value is None:
        raise HTTPException(status_code=500, detail="Digital read failed")
    return {"ok": True, "pin": body.pin, "value": bool(value)}


@app.post("/api/gpio/digital_read_many")
def api_digital_read_many(request: Request, body: DigitalReadManyBody):
    """Batch mode-preserving reads (`r`) with short waits for UI polling."""
    _require_control(request)
    session.require_connected()
    session.require_idle()
    pins = []
    seen = set()
    for p in body.pins:
        if p < 0 or p > 7:
            raise HTTPException(status_code=400, detail=f"Invalid pin: {p}")
        if p not in seen:
            seen.add(p)
            pins.append(p)
    values: dict[str, bool] = {}
    with session.lock:
        tool = session.tool()
        for pin in pins:
            value = tool.digital_read(pin, 0.08)
            if value is None:
                continue  # skip failed pin; others still update
            values[str(pin)] = bool(value)
    return {"ok": True, "values": values}


@app.post("/api/gpio/pin_input")
def api_pin_input(request: Request, body: DigitalReadBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    with session.lock:
        ok = session.tool().pin_input(body.pin, 0.5)
    if not ok:
        raise HTTPException(status_code=500, detail="Pin input release failed")
    return {"ok": True, "pin": body.pin, "mode": "input"}


@app.post("/api/gpio/analog_write")
def api_analog_write(request: Request, body: AnalogWriteBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    with session.lock:
        ok = session.tool().analog_write(body.pin, body.value, 0.5)
    if not ok:
        raise HTTPException(status_code=500, detail="Analog write failed")
    return {"ok": True, "pin": body.pin, "value": body.value}


@app.post("/api/gpio/analog_read")
def api_analog_read(request: Request, body: AnalogReadBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    with session.lock:
        value = session.tool().analog_read(body.pin, 1.0)
    if value is None:
        raise HTTPException(
            status_code=500,
            detail="Analog read failed (no response — reflash controller if MCU hung on PA6/PA7)",
        )
    return {"ok": True, "pin": body.pin, "value": int(value)}


# ---- capture workers ----

def _run_la_capture(rate_hz: int, sample_count: int) -> None:
    session.la_status = {
        "state": "running",
        "rate_hz": rate_hz,
        "sample_count": sample_count,
        "started_at": time.time(),
    }
    try:
        timeout = max(30.0, (sample_count / max(rate_hz, 1)) + 5.0)
        with session.lock:
            # Drain any stale RX before capture.
            session.tool().check_input()
            result = session.tool().logic_analyzer_capture(
                rate_hz, sample_count, wait_for_input_time=timeout)
        if not result.get("ok"):
            session.la_status = {"state": "error", "error": result.get("error", "capture failed")}
            session.la_result = None
        else:
            payload = digital_result_payload(result)
            session.la_result = payload
            session.la_status = {
                "state": "done",
                "rate_hz": payload["rate_hz"],
                "sample_count": payload["sample_count"],
            }
    except Exception as exc:
        session.la_status = {"state": "error", "error": str(exc)}
        session.la_result = None
    finally:
        session.busy = "idle"
        access.tick("idle")


def _run_analog_capture(rate_hz: int, sample_count: int, channel_mask: int) -> None:
    session.analog_status = {
        "state": "running",
        "rate_hz": rate_hz,
        "sample_count": sample_count,
        "channel_mask": channel_mask,
        "started_at": time.time(),
    }
    try:
        timeout = max(30.0, (sample_count / max(rate_hz, 1)) + 5.0)
        with session.lock:
            session.tool().check_input()
            result = session.tool().analog_capture(
                rate_hz, sample_count, channel_mask, wait_for_input_time=timeout)
        if not result.get("ok"):
            session.analog_status = {
                "state": "error",
                "error": result.get("error", "capture failed"),
            }
            session.analog_result = None
        else:
            payload = analog_result_payload(result)
            session.analog_result = payload
            session.analog_status = {
                "state": "done",
                "rate_hz": payload["rate_hz"],
                "sample_count": payload["sample_count"],
                "channel_mask": payload["channel_mask"],
                "channels": payload["channels"],
            }
    except Exception as exc:
        session.analog_status = {"state": "error", "error": str(exc)}
        session.analog_result = None
    finally:
        session.busy = "idle"
        access.tick("idle")


@app.post("/api/la/start")
def api_la_start(request: Request, body: LaStartBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    session.busy = "la"
    session.la_result = None
    session.la_status = {"state": "starting", "rate_hz": body.rate_hz, "sample_count": body.sample_count}
    thread = threading.Thread(
        target=_run_la_capture,
        args=(body.rate_hz, body.sample_count),
        daemon=True,
    )
    session._capture_thread = thread
    thread.start()
    return {"ok": True, "busy": "la"}


@app.get("/api/la/status")
def api_la_status():
    return session.la_status


@app.get("/api/la/result")
def api_la_result():
    if session.la_result is None:
        raise HTTPException(status_code=404, detail="No LA result")
    return session.la_result


@app.post("/api/analog/start")
def api_analog_start(request: Request, body: AnalogStartBody):
    _require_control(request)
    session.require_connected()
    session.require_idle()
    session.busy = "analog"
    session.analog_result = None
    session.analog_status = {
        "state": "starting",
        "rate_hz": body.rate_hz,
        "sample_count": body.sample_count,
        "channel_mask": body.channel_mask,
    }
    thread = threading.Thread(
        target=_run_analog_capture,
        args=(body.rate_hz, body.sample_count, body.channel_mask),
        daemon=True,
    )
    session._capture_thread = thread
    thread.start()
    return {"ok": True, "busy": "analog"}


@app.get("/api/analog/status")
def api_analog_status():
    return session.analog_status


@app.get("/api/analog/result")
def api_analog_result():
    if session.analog_result is None:
        raise HTTPException(status_code=404, detail="No analog result")
    return session.analog_result


async def _ws_watch(websocket: WebSocket, kind: str) -> None:
    await websocket.accept()
    last = None
    try:
        while True:
            status = session.la_status if kind == "la" else session.analog_status
            result = session.la_result if kind == "la" else session.analog_result
            snapshot = (status.get("state"), status.get("error"), id(result))
            if snapshot != last:
                last = snapshot
                message: dict[str, Any] = {"type": "status", "status": status}
                if status.get("state") == "done" and result is not None:
                    message["type"] = "done"
                    message["result"] = result
                elif status.get("state") == "error":
                    message["type"] = "error"
                    message["error"] = status.get("error", "unknown")
                await websocket.send_json(message)
                if status.get("state") in ("done", "error", "idle"):
                    # Keep connection briefly so client can finish, then exit loop on next idle
                    if status.get("state") in ("done", "error"):
                        break
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/la")
async def ws_la(websocket: WebSocket):
    await _ws_watch(websocket, "la")


@app.websocket("/ws/analog")
async def ws_analog(websocket: WebSocket):
    await _ws_watch(websocket, "analog")


# ---- firmware ----

@app.get("/api/firmware/samples")
def api_firmware_samples():
    """List bundled sample .bin/.hex files for try-without-upload."""
    sample_dir = STATIC_DIR / "sample_bin"
    if not sample_dir.is_dir():
        return {"samples": []}
    samples = []
    for path in sorted(sample_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".bin", ".hex"):
            continue
        samples.append({
            "name": path.name,
            "url": f"/static/sample_bin/{path.name}",
        })
    return {"samples": samples}


@app.post("/api/firmware/upload")
async def api_firmware_upload(request: Request, file: UploadFile = File(...)):
    _require_control(request)
    session.require_connected()
    session.require_idle()

    raw_name = file.filename or "firmware.bin"
    # Basename only — never use client path components for anything executable.
    display_name = Path(raw_name).name.replace("\x00", "")
    suffix = Path(display_name).suffix.lower()
    if suffix not in (".bin", ".hex"):
        raise HTTPException(status_code=400, detail="Upload a .bin or .hex file")
    if not display_name.lower().endswith(suffix):
        raise HTTPException(status_code=400, detail="Upload a .bin or .hex file")
    safe_display = f"firmware{suffix}"
    # Keep a short printable label for the UI if the basename looks safe.
    if display_name.replace(".", "").replace("_", "").replace("-", "").isalnum() and len(display_name) <= 64:
        safe_display = display_name

    session.busy = "flash"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            total = 0
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                total += len(chunk)
                if total > DUT_FLASH_MAX_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Firmware exceeds CH32V003 flash size ({DUT_FLASH_MAX_BYTES} bytes)",
                    )
                tmp.write(chunk)

        with session.lock:
            ok = session.target.flashFirmware(tmp_path)
        if not ok:
            raise HTTPException(status_code=500, detail="Firmware flash failed")
        return {"ok": True, "filename": safe_display}
    finally:
        session.busy = "idle"
        access.tick("idle")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---- static ----

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False)
