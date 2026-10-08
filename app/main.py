import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .database import engine as db_engine, Base
from .models import User, GameRound, Bet, Transaction
from .game_engine import engine as game_engine
from .websocket import ws_manager
from .routes import auth_routes, game_routes, wallet_routes, admin_routes

# Create database tables
Base.metadata.create_all(bind=db_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background game loop
    print("Starting Aviator Game Engine...")
    await game_engine.start()
    yield
    # Shutdown: Stop the game loop
    print("Stopping Aviator Game Engine...")
    await game_engine.stop()


app = FastAPI(
    title="Aviator Demo - Virtual Coins Flight Multiplier",
    description="Online Aviator-style multiplier game using virtual demo currency only. Portfolio demonstration.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include HTTP API routes
app.include_router(auth_routes.router)
app.include_router(game_routes.router)
app.include_router(wallet_routes.router)
app.include_router(admin_routes.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "game_status": game_engine.status,
        "round_id": game_engine.round_id,
        "multiplier": game_engine.current_multiplier,
        "notice": "Demo Coins — No Real Money"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send current game snapshot immediately upon connection
        await ws_manager.send_personal(websocket, {
            "type": "snapshot",
            "state": game_engine.get_snapshot()
        })
        
        while True:
            data = await websocket.receive_text()
            await ws_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
