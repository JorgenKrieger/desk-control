"""Local service exposing the desk over a small HTTP API, for development.

The live, always-on deployment is ../raspberry-pi/ -- this is for local
testing on the Mac only, bound to 127.0.0.1 (not meant to be reachable from
other devices). Only one of dev/ and raspberry-pi/ can hold the desk's BLE
connection at a time.

Run directly:
    poetry run uvicorn service:app --host 127.0.0.1 --port 8842
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
from controller import Desk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("desk_control.service")

RECONNECT_DELAY_SECONDS = 5.0

desk = Desk()


async def _connection_loop():
    """Keep the desk connected, reconnecting if it drops.

    Broadly catches any connection error (not just DeskNotConnected) --
    bleak can raise its own exceptions (timeouts, OS-level BLE errors) that
    must not be allowed to kill this background task, or the service would
    silently stop retrying and never reconnect.
    """
    while True:
        if not desk.is_connected:
            try:
                await desk.connect(device_id=config.load().get("device_id"))
            except Exception:
                logger.warning("Could not connect to desk, will retry", exc_info=True)
        await asyncio.sleep(RECONNECT_DELAY_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_connection_loop())
    yield
    task.cancel()
    await desk.disconnect()


app = FastAPI(title="desk-control", lifespan=lifespan)


def _require_connected():
    if not desk.is_connected:
        raise HTTPException(status_code=503, detail="Desk is not connected")


@app.get("/status")
async def status():
    height_cm = desk.height_cm
    if desk.is_connected and height_cm is None:
        height_cm = await desk.refresh_height()
    return {
        "connected": desk.is_connected,
        "height_cm": height_cm,
        "is_moving": desk.is_moving,
    }


@app.post("/up")
async def up():
    _require_connected()
    await desk.move_up()
    return {"ok": True}


@app.post("/down")
async def down():
    _require_connected()
    await desk.move_down()
    return {"ok": True}


@app.post("/stop")
async def stop():
    _require_connected()
    await desk.stop()
    return {"ok": True}


class MoveToRequest(BaseModel):
    height_cm: float


@app.post("/move_to")
async def move_to(body: MoveToRequest):
    _require_connected()
    await desk.move_to(body.height_cm)
    return {"ok": True}


@app.post("/sit")
async def sit():
    _require_connected()
    await desk.move_to(config.load()["sit_height_cm"])
    return {"ok": True}


@app.post("/stand")
async def stand():
    _require_connected()
    await desk.move_to(config.load()["stand_height_cm"])
    return {"ok": True}


@app.get("/config")
async def get_config():
    return config.load()


class ConfigRequest(BaseModel):
    sit_height_cm: float | None = None
    stand_height_cm: float | None = None
    device_id: str | None = None


@app.post("/config")
async def set_config(body: ConfigRequest):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    config.save(updates)
    return config.load()
