"""
AERIS — Aerospace Engine Risk & Intelligence System
FastAPI Application Entry Point

AI-Enabled Real-Time Digital Twin for Aero Piston Engines in MALE UAVs
SIH26054 — Smart India Hackathon

Physics-informed demonstrator model — NOT an exact DRDO engine model.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .core.orchestrator import get_orchestrator
from .api.telemetry import router as telemetry_router
from .api.simulation import router as simulation_router
from .api.missions import router as missions_router
from .api.faults import router as faults_router
from .api.health import router as health_router


config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    orchestrator = get_orchestrator()
    # Auto-start simulation on startup
    await orchestrator.start()
    yield
    await orchestrator.stop()


app = FastAPI(
    title="AERIS — Aerospace Engine Risk & Intelligence System",
    description=(
        "AI-Enabled Real-Time Digital Twin for Aero Piston Engines in MALE UAVs. "
        "Physics-informed demonstrator model for SIH26054."
    ),
    version=config.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(telemetry_router, prefix="/api", tags=["Telemetry"])
app.include_router(simulation_router, prefix="/api", tags=["Simulation"])
app.include_router(missions_router, prefix="/api", tags=["Missions"])
app.include_router(faults_router, prefix="/api", tags=["Faults"])
app.include_router(health_router, prefix="/api", tags=["Health"])


@app.get("/")
async def root():
    return {
        "name": config.app_name,
        "subtitle": config.app_subtitle,
        "version": config.app_version,
        "status": "operational",
        "note": "Physics-informed demonstrator model — not certified for flight safety",
    }


@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time telemetry streaming at ~20Hz."""
    await websocket.accept()
    orchestrator = get_orchestrator()
    orchestrator.register_ws_client(websocket)
    try:
        while True:
            # Keep connection alive, handle incoming commands
            data = await websocket.receive_text()
            # Could handle commands from frontend here
    except WebSocketDisconnect:
        orchestrator.unregister_ws_client(websocket)
    except Exception:
        orchestrator.unregister_ws_client(websocket)
