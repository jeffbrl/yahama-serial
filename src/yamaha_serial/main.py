"""Main application entry point for Yamaha RX-Z1 Serial Controller."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from yamaha_serial.config import settings
from yamaha_serial.controller import create_controller
from yamaha_serial.api.routes import router as api_router, setup_routes

controller = create_controller()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await controller.start()
    yield
    # Shutdown
    await controller.stop()


app = FastAPI(
    title="Yamaha RX-Z1 Serial Controller",
    description="REST API and WebSocket server for controlling the Yamaha RX-Z1 AV Receiver over RS-232.",
    version="0.1.0",
    lifespan=lifespan,
)

# Attach API routes
setup_routes(controller)
app.include_router(api_router)

# Static files and Web UI
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")


def run():
    uvicorn.run(
        "yamaha_serial.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL,
        reload=False,
    )


if __name__ == "__main__":
    run()
