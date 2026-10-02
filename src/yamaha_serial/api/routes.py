"""FastAPI REST and WebSocket routes for Yamaha RX-Z1 Serial Controller."""

import asyncio
import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from yamaha_serial.controller import YamahaController, ReceiverState
from yamaha_serial.protocol.commands import PowerState, InputSource, DSPProgram

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class PowerRequest(BaseModel):
    power: PowerState


class VolumePercentRequest(BaseModel):
    percent: int


class MuteRequest(BaseModel):
    mute: bool


class InputRequest(BaseModel):
    source: InputSource


class DSPRequest(BaseModel):
    dsp: DSPProgram


class RawCommandRequest(BaseModel):
    code: str


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


ws_manager = ConnectionManager()
_controller: YamahaController = None


def setup_routes(controller: YamahaController):
    global _controller
    _controller = controller

    async def on_state_change(state: ReceiverState):
        await ws_manager.broadcast(state.model_dump_json())

    _controller.add_listener(on_state_change)


@router.get("/state", response_model=ReceiverState)
async def get_state():
    return _controller.state


@router.post("/power", response_model=ReceiverState)
async def set_power(req: PowerRequest):
    return await _controller.set_power(req.power)


@router.post("/volume/percent", response_model=ReceiverState)
async def set_volume_percent(req: VolumePercentRequest):
    return await _controller.set_volume_percent(req.percent)


@router.post("/volume/up", response_model=ReceiverState)
async def volume_up():
    return await _controller.volume_up()


@router.post("/volume/down", response_model=ReceiverState)
async def volume_down():
    return await _controller.volume_down()


@router.post("/mute", response_model=ReceiverState)
async def set_mute(req: MuteRequest):
    return await _controller.set_mute(req.mute)


@router.post("/mute/toggle", response_model=ReceiverState)
async def toggle_mute():
    return await _controller.toggle_mute()


@router.post("/input", response_model=ReceiverState)
async def set_input(req: InputRequest):
    return await _controller.set_input(req.source)


@router.post("/dsp", response_model=ReceiverState)
async def set_dsp(req: DSPRequest):
    return await _controller.set_dsp(req.dsp)


@router.post("/raw")
async def send_raw(req: RawCommandRequest):
    try:
        await _controller.send_raw_code(req.code)
        return {"status": "ok", "sent_code": req.code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    # Send current state upon initial connection
    await websocket.send_text(_controller.state.model_dump_json())
    try:
        while True:
            # Keep connection open; clients can also send ping/requests
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
