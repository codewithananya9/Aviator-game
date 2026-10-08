import json
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from .auth import decode_token
from .game_engine import engine
from .database import SessionLocal
from .models import User

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        # Mapping websocket -> user_id
        self.user_connections: Dict[WebSocket, Optional[int]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.user_connections[websocket] = None

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.user_connections.pop(websocket, None)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        payload = json.dumps(message)
        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            self.disconnect(websocket)

    async def handle_message(self, websocket: WebSocket, raw_data: str):
        try:
            data = json.loads(raw_data)
        except Exception:
            await self.send_personal(websocket, {"type": "error", "message": "Invalid JSON format"})
            return

        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send_personal(websocket, {"type": "pong", "time": data.get("time")})
            return

        elif msg_type == "auth":
            token = data.get("token")
            if not token:
                await self.send_personal(websocket, {"type": "auth_error", "message": "No token provided"})
                return

            token_data = decode_token(token)
            if not token_data or not token_data.user_id:
                await self.send_personal(websocket, {"type": "auth_error", "message": "Invalid or expired token"})
                return

            self.user_connections[websocket] = token_data.user_id
            
            # Fetch user info & balance
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == token_data.user_id).first()
                if user:
                    await self.send_personal(websocket, {
                        "type": "auth_success",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "balance": user.balance,
                            "avatar_color": user.avatar_color
                        }
                    })
                else:
                    await self.send_personal(websocket, {"type": "auth_error", "message": "User not found"})
            finally:
                db.close()
            return

        elif msg_type == "place_bet":
            user_id = self.user_connections.get(websocket)
            if not user_id:
                await self.send_personal(websocket, {"type": "bet_error", "message": "Please login to place bets"})
                return

            bet_amount = float(data.get("bet_amount", 0))
            auto_cashout = data.get("auto_cashout")
            auto_cashout = float(auto_cashout) if auto_cashout is not None and float(auto_cashout) > 1.0 else None
            panel_index = int(data.get("panel_index", 1))

            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    await self.send_personal(websocket, {"type": "bet_error", "message": "User not found"})
                    return
                username = user.username
            finally:
                db.close()

            success, message, bet_info = await engine.place_bet(
                user_id=user_id,
                username=username,
                bet_amount=bet_amount,
                auto_cashout=auto_cashout,
                panel_index=panel_index
            )

            if success:
                await self.send_personal(websocket, {
                    "type": "bet_accepted",
                    "bet": bet_info
                })
            else:
                await self.send_personal(websocket, {
                    "type": "bet_error",
                    "message": message,
                    "panel_index": panel_index
                })
            return

        elif msg_type == "cash_out":
            user_id = self.user_connections.get(websocket)
            if not user_id:
                await self.send_personal(websocket, {"type": "cashout_error", "message": "Unauthorized"})
                return

            bet_id = int(data.get("bet_id", 0))
            success, message, result = await engine.cash_out_bet(bet_id, user_id)
            if not success:
                await self.send_personal(websocket, {
                    "type": "cashout_error",
                    "bet_id": bet_id,
                    "message": message
                })
            return

        elif msg_type == "cancel_bet":
            user_id = self.user_connections.get(websocket)
            if not user_id:
                await self.send_personal(websocket, {"type": "error", "message": "Unauthorized"})
                return

            bet_id = int(data.get("bet_id", 0))
            success, message, new_balance = await engine.cancel_bet(bet_id, user_id)
            if success:
                await self.send_personal(websocket, {
                    "type": "bet_cancelled_confirm",
                    "bet_id": bet_id,
                    "new_balance": new_balance
                })
            else:
                await self.send_personal(websocket, {
                    "type": "error",
                    "message": message
                })
            return

        elif msg_type == "get_state":
            await self.send_personal(websocket, {
                "type": "snapshot",
                "state": engine.get_snapshot()
            })
            return


ws_manager = ConnectionManager()
# Link websocket manager broadcast to game engine
engine.set_broadcaster(ws_manager.broadcast)
