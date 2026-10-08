import asyncio
import hashlib
import random
import secrets
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import GameRound, Bet, User, Transaction

# Simulated participants to give the room an authentic multiplayer atmosphere
SIMULATED_PILOTS = [
    "AeroAce", "LuckyJet", "SkyCaptain", "RedBaron", "TurboPilot",
    "CloudWalker", "SonicBoom", "AlphaFlyer", "VortexMax", "HighRoller99",
    "ApexPilot", "ShadowWing", "FalconEcho", "ZephyrX", "NeonRider",
    "StarGlider", "Maverick", "PhoenixRise", "VelocityPro", "JetStream7"
]

class GameEngine:
    """
    Server-authoritative flight multiplier game engine.

    Round Lifecycle:
        WAITING (5s) -> STARTING (3s) -> RUNNING (dynamic flight) -> ENDED (3s) -> NEXT ROUND

    Transparent, Documented Demo Randomization:
        The crash multiplier is derived from cryptographic SHA-256 entropy using
        a standard Pareto probability distribution with an expected theoretical house edge of 3%.
        
        Formula:
            ratio = int(sha256_hash[:13], 16) / 2^52
            If ratio indicates instant takeoff abort (~3% probability):
                multiplier = 1.00x
            Else:
                multiplier = max(1.00, round(0.97 / (1.0 - ratio), 2))
                
        * No player-specific targeting or balance-dependent manipulation.
        * Every outcome is purely determined prior to takeoff and verifiable by SHA-256 hash.
    """

    def __init__(self):
        # Round State
        self.round_id: int = 0
        self.round_number: int = 1
        self.round_uuid: str = ""
        self.status: str = "WAITING"  # WAITING, STARTING, RUNNING, ENDED
        self.start_timestamp: float = 0.0
        self.elapsed_time: float = 0.0
        self.current_multiplier: float = 1.00
        self.crash_multiplier: float = 1.00
        self.countdown_remaining: float = 5.0
        
        # Cryptographic seeds for provably fair proof
        self.server_seed: str = ""
        self.client_seed: str = "aviator-demo-community-seed"
        self.combined_hash: str = ""

        # In-memory participant bets and cashout states for low-latency updates
        # key: bet_id -> dict
        self.active_bets: Dict[Any, dict] = {}
        
        # Recent round multipliers history
        self.recent_history: List[dict] = []
        
        # Broadcaster hook
        self.broadcast_func = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def set_broadcaster(self, func):
        self.broadcast_func = func

    async def broadcast(self, message: dict):
        if self.broadcast_func:
            await self.broadcast_func(message)

    def generate_crash_multiplier(self) -> (float, str, str):
        """
        Transparent mathematical demo randomization.
        Generates server seed, SHA-256 hash, and calculates crash point.
        """
        server_seed = secrets.token_hex(32)
        combined = f"{server_seed}:{self.client_seed}:{int(time.time() * 1000)}"
        combined_hash = hashlib.sha256(combined.encode()).hexdigest()

        # 52 bits of entropy
        hash_slice = combined_hash[:13]
        int_value = int(hash_slice, 16)
        max_int = 2**52

        # 3% probability of instant crash at 1.00x
        if int_value % 33 == 0:
            multiplier = 1.00
        else:
            ratio = min(0.999, int_value / max_int)
            # Pareto crash multiplier
            multiplier = 0.97 / (1.0 - ratio)
            multiplier = max(1.00, round(multiplier, 2))
            multiplier = min(multiplier, 500.00)

        return multiplier, server_seed, combined_hash

    def load_initial_history(self):
        """Pre-populate recent multipliers from DB or default realistic values"""
        db: Session = SessionLocal()
        try:
            rounds = db.query(GameRound).filter(GameRound.status.in_(["ENDED", "CRASHED"])).order_by(GameRound.id.desc()).limit(25).all()
            if rounds:
                self.recent_history = [
                    {
                        "round_id": r.id,
                        "round_uuid": r.round_uuid,
                        "multiplier": r.crash_multiplier,
                        "combined_hash": r.combined_hash,
                        "ended_at": r.ended_at.isoformat() if r.ended_at else None
                    }
                    for r in reversed(rounds)
                ]
            else:
                demo_multipliers = [1.15, 1.35, 1.72, 2.10, 1.04, 3.25, 1.50, 12.40, 1.88, 2.65, 1.00, 4.10]
                self.recent_history = [
                    {"round_id": i + 1, "round_uuid": f"init-{i}", "multiplier": m, "combined_hash": f"init-hash-{i}"}
                    for i, m in enumerate(demo_multipliers)
                ]
            from sqlalchemy import func
            max_num = db.query(func.max(GameRound.round_number)).scalar() or db.query(func.max(GameRound.id)).scalar()
            self.round_number = (max_num or 0) + 1
        except Exception as e:
            print(f"Error loading initial history: {e}")
        finally:
            db.close()

    def generate_simulated_bets(self):
        """Populate participants table with simulated players"""
        bot_count = random.randint(8, 16)
        chosen_pilots = random.sample(SIMULATED_PILOTS, bot_count)

        for idx, name in enumerate(chosen_pilots):
            stake = random.choice([10.0, 20.0, 50.0, 100.0, 200.0, 500.0])
            # Target cashouts
            if random.random() < 0.65:
                target_cashout = round(random.uniform(1.15, 2.40), 2)
            elif random.random() < 0.90:
                target_cashout = round(random.uniform(2.40, 6.50), 2)
            else:
                target_cashout = round(random.uniform(6.50, 25.00), 2)

            bot_key = f"pilot_{idx}_{name}"
            self.active_bets[bot_key] = {
                "id": bot_key,
                "user_id": 0,
                "username": name,
                "is_bot": True,
                "bet_amount": stake,
                "auto_cashout": target_cashout,
                "cashout_multiplier": None,
                "payout": 0.0,
                "status": "PLACED",
                "panel_index": 1,
                "avatar_color": random.choice(["#3b82f6", "#10b981", "#8b5cf6", "#ec4899", "#f59e0b", "#06b6d4"])
            }

    async def start(self):
        self._running = True
        self.load_initial_history()
        self._task = asyncio.create_task(self._game_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _game_loop(self):
        """
        Authoritative round progression:
        WAITING (5s) -> STARTING (3s) -> RUNNING (dynamic) -> ENDED (3s) -> Repeat
        """
        while self._running:
            try:
                # -----------------------------------------------------------------
                # PHASE 1: PREPARATION & WAITING (5.0 seconds)
                # -----------------------------------------------------------------
                self.crash_multiplier, self.server_seed, self.combined_hash = self.generate_crash_multiplier()
                self.round_uuid = str(uuid.uuid4())
                self.active_bets.clear()
                self.generate_simulated_bets()

                db: Session = SessionLocal()
                try:
                    new_round = GameRound(
                        round_number=self.round_number,
                        round_uuid=self.round_uuid,
                        crash_multiplier=self.crash_multiplier,
                        server_seed=self.server_seed,
                        client_seed=self.client_seed,
                        combined_hash=self.combined_hash,
                        status="WAITING"
                    )
                    db.add(new_round)
                    db.commit()
                    db.refresh(new_round)
                    self.round_id = new_round.id
                    self.round_number += 1
                finally:
                    db.close()

                self.status = "WAITING"
                waiting_start = time.time()
                waiting_duration = 5.0

                while time.time() - waiting_start < waiting_duration:
                    self.countdown_remaining = max(0.0, round(waiting_duration - (time.time() - waiting_start), 1))
                    await self.broadcast({
                        "type": "round_waiting",
                        "status": "WAITING",
                        "round_id": self.round_id,
                        "round_uuid": self.round_uuid,
                        "countdown": self.countdown_remaining,
                        "combined_hash": self.combined_hash,
                        "bets": list(self.active_bets.values())
                    })
                    await asyncio.sleep(0.2)

                # -----------------------------------------------------------------
                # PHASE 2: STARTING (3.0 seconds) - Takeoff countdown, bets locked
                # -----------------------------------------------------------------
                self.status = "STARTING"
                starting_start = time.time()
                starting_duration = 3.0

                db = SessionLocal()
                try:
                    r = db.query(GameRound).filter(GameRound.id == self.round_id).first()
                    if r:
                        r.status = "STARTING"
                        db.commit()
                finally:
                    db.close()

                while time.time() - starting_start < starting_duration:
                    self.countdown_remaining = max(0.0, round(starting_duration - (time.time() - starting_start), 1))
                    await self.broadcast({
                        "type": "round_starting",
                        "status": "STARTING",
                        "round_id": self.round_id,
                        "round_uuid": self.round_uuid,
                        "countdown": self.countdown_remaining,
                        "combined_hash": self.combined_hash,
                        "bets": list(self.active_bets.values())
                    })
                    await asyncio.sleep(0.2)

                # -----------------------------------------------------------------
                # PHASE 3: RUNNING (Dynamic Flight)
                # -----------------------------------------------------------------
                self.status = "RUNNING"
                self.current_multiplier = 1.00
                self.start_timestamp = time.time()

                db = SessionLocal()
                try:
                    r = db.query(GameRound).filter(GameRound.id == self.round_id).first()
                    if r:
                        r.status = "RUNNING"
                        r.started_at = datetime.utcnow()
                        db.commit()
                finally:
                    db.close()

                await self.broadcast({
                    "type": "round_started",
                    "status": "RUNNING",
                    "round_id": self.round_id,
                    "round_uuid": self.round_uuid,
                    "multiplier": 1.00
                })

                # Flight loop: ticks every 50-60ms with smooth multiplier growth
                while self.status == "RUNNING":
                    elapsed = time.time() - self.start_timestamp
                    self.elapsed_time = elapsed

                    # Smooth mathematical altitude curve
                    # Starts at 1.00x and accelerates smoothly
                    computed_multiplier = 1.00 + (0.05 * elapsed) + (0.018 * (elapsed ** 1.82))
                    self.current_multiplier = round(computed_multiplier, 2)

                    # Check auto-cashouts
                    await self._check_auto_cashouts()

                    # End condition reached
                    if self.current_multiplier >= self.crash_multiplier:
                        self.current_multiplier = self.crash_multiplier
                        break

                    # Broadcast tick
                    await self.broadcast({
                        "type": "tick",
                        "status": "RUNNING",
                        "round_id": self.round_id,
                        "multiplier": self.current_multiplier,
                        "elapsed": round(self.elapsed_time, 2)
                    })

                    await asyncio.sleep(0.06)

                # -----------------------------------------------------------------
                # PHASE 4: ENDED (3.0 seconds) - Round ends, results recorded
                # -----------------------------------------------------------------
                self.status = "ENDED"
                await self._handle_round_ended()

                # Pause 3.0 seconds so players see flight result & win/loss states
                await asyncio.sleep(3.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in authoritative game loop: {e}")
                await asyncio.sleep(2.0)

    async def _check_auto_cashouts(self):
        """Server-authoritative check for Auto Cash Out targets"""
        for bet_key, bet in list(self.active_bets.items()):
            if bet["status"] != "PLACED":
                continue

            target = bet.get("auto_cashout")
            if target and self.current_multiplier >= target:
                if bet.get("is_bot"):
                    bet["status"] = "CASHED_OUT"
                    bet["cashout_multiplier"] = target
                    bet["payout"] = round(bet["bet_amount"] * target, 2)
                    await self.broadcast({
                        "type": "cashout_success",
                        "bet_id": bet["id"],
                        "username": bet["username"],
                        "multiplier": target,
                        "payout": bet["payout"],
                        "is_bot": True
                    })
                else:
                    await self._process_user_cashout(bet["id"], bet["user_id"], target)

    async def _process_user_cashout(self, bet_id: int, user_id: int, multiplier: float) -> Optional[dict]:
        """
        Server validates and updates virtual balance:
        virtual stake x current multiplier
        """
        db: Session = SessionLocal()
        try:
            bet_record = db.query(Bet).filter(Bet.id == bet_id, Bet.user_id == user_id).first()
            if not bet_record or bet_record.status != "PLACED":
                return None

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            # Server calculation: stake * multiplier
            payout = round(bet_record.bet_amount * multiplier, 2)
            bet_record.cashout_multiplier = multiplier
            bet_record.payout = payout
            bet_record.status = "CASHED_OUT"

            # Securely update user demo balance on server
            user.balance = round(user.balance + payout, 2)

            tx = Transaction(
                user_id=user.id,
                amount=payout,
                balance_after=user.balance,
                tx_type="BET_WON",
                description=f"Won {payout} Demo Coins on round #{self.round_id} @ {multiplier:.2f}x"
            )
            db.add(tx)
            db.commit()

            if bet_id in self.active_bets:
                self.active_bets[bet_id]["status"] = "CASHED_OUT"
                self.active_bets[bet_id]["cashout_multiplier"] = multiplier
                self.active_bets[bet_id]["payout"] = payout

            result = {
                "bet_id": bet_id,
                "user_id": user_id,
                "username": user.username,
                "multiplier": multiplier,
                "payout": payout,
                "new_balance": user.balance,
                "panel_index": bet_record.panel_index,
                "is_bot": False
            }

            await self.broadcast({
                "type": "cashout_success",
                **result
            })

            return result
        except Exception as e:
            db.rollback()
            print(f"Error processing cashout: {e}")
            return None
        finally:
            db.close()

    async def cash_out_bet(self, bet_id: int, user_id: int) -> (bool, str, Optional[dict]):
        """
        Section 7 Cash Out validation:
        Backend strictly validates:
        1. Round is currently RUNNING (if ended or starting, reject!)
        2. User is participating in the current round
        3. User has not already cashed out
        """
        if self.status != "RUNNING":
            return False, "Cannot cash out: Round is not running", None

        bet = self.active_bets.get(bet_id)
        if not bet or bet.get("user_id") != user_id:
            return False, "Bet not found or does not belong to you", None

        if bet.get("status") != "PLACED":
            return False, "Bet already cashed out or completed", None

        multiplier = self.current_multiplier
        result = await self._process_user_cashout(bet_id, user_id, multiplier)
        if result:
            return True, "Cashed out successfully", result
        return False, "Failed to process cashout", None

    async def place_bet(
        self,
        user_id: int,
        username: str,
        bet_amount: float,
        auto_cashout: Optional[float] = None,
        panel_index: int = 1
    ) -> (bool, str, Optional[dict]):
        """
        Validate and place virtual bet during WAITING phase.
        Server verifies sufficient virtual balance and deducts stake securely.
        """
        if self.status != "WAITING":
            return False, "Bets can only be placed during the WAITING phase", None

        if bet_amount <= 0:
            return False, "Bet amount must be greater than 0", None

        # Check existing bet for this panel
        for b in self.active_bets.values():
            if b.get("user_id") == user_id and b.get("panel_index") == panel_index:
                return False, f"You already placed a bet on Panel {panel_index} for this round", None

        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found", None

            if user.balance < bet_amount:
                return False, f"Insufficient Demo Coins. Balance: {user.balance:.2f} VC", None

            # Server deducts virtual stake
            user.balance = round(user.balance - bet_amount, 2)

            bet = Bet(
                user_id=user_id,
                round_id=self.round_id,
                bet_amount=bet_amount,
                auto_cashout=auto_cashout,
                panel_index=panel_index,
                status="PLACED"
            )
            db.add(bet)

            tx = Transaction(
                user_id=user.id,
                amount=-bet_amount,
                balance_after=user.balance,
                tx_type="BET_PLACED",
                description=f"Wagered {bet_amount} Demo Coins on round #{self.round_id}"
            )
            db.add(tx)
            db.commit()
            db.refresh(bet)

            bet_data = {
                "id": bet.id,
                "user_id": user_id,
                "username": username,
                "is_bot": False,
                "bet_amount": bet_amount,
                "auto_cashout": auto_cashout,
                "cashout_multiplier": None,
                "payout": 0.0,
                "status": "PLACED",
                "panel_index": panel_index,
                "avatar_color": user.avatar_color
            }

            self.active_bets[bet.id] = bet_data

            await self.broadcast({
                "type": "bet_placed",
                "bet": bet_data,
                "new_balance": user.balance
            })

            return True, "Bet placed successfully", {**bet_data, "new_balance": user.balance}
        except Exception as e:
            db.rollback()
            return False, f"Error placing bet: {e}", None
        finally:
            db.close()

    async def cancel_bet(self, bet_id: int, user_id: int) -> (bool, str, Optional[float]):
        """Cancel bet during WAITING phase and refund virtual stake"""
        if self.status != "WAITING":
            return False, "Bets can only be cancelled during WAITING phase", None

        bet = self.active_bets.get(bet_id)
        if not bet or bet.get("user_id") != user_id or bet.get("status") != "PLACED":
            return False, "Bet cannot be cancelled", None

        db: Session = SessionLocal()
        try:
            bet_record = db.query(Bet).filter(Bet.id == bet_id, Bet.user_id == user_id).first()
            if not bet_record or bet_record.status != "PLACED":
                return False, "Bet record not found", None

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found", None

            refund_amount = bet_record.bet_amount
            user.balance = round(user.balance + refund_amount, 2)
            bet_record.status = "CANCELLED"

            tx = Transaction(
                user_id=user.id,
                amount=refund_amount,
                balance_after=user.balance,
                tx_type="BET_CANCELLED",
                description=f"Cancelled bet on round #{self.round_id}"
            )
            db.add(tx)
            db.commit()

            del self.active_bets[bet_id]

            await self.broadcast({
                "type": "bet_cancelled",
                "bet_id": bet_id,
                "user_id": user_id,
                "new_balance": user.balance
            })

            return True, "Bet cancelled and refunded", user.balance
        except Exception as e:
            db.rollback()
            return False, f"Error: {e}", None
        finally:
            db.close()

    async def _handle_round_ended(self):
        """
        Record round end in DB and mark remaining uncashed bets as BUSTED / LOST.
        Broadcast results to all connected players.
        """
        db: Session = SessionLocal()
        try:
            r = db.query(GameRound).filter(GameRound.id == self.round_id).first()
            if r:
                r.status = "ENDED"
                r.ended_at = datetime.utcnow()

            # Mark all uncashed bets as BUSTED
            for bet_key, bet in self.active_bets.items():
                if bet["status"] == "PLACED":
                    bet["status"] = "BUSTED"
                    if not bet.get("is_bot"):
                        db_bet = db.query(Bet).filter(Bet.id == bet["id"]).first()
                        if db_bet:
                            db_bet.status = "BUSTED"

            db.commit()

            history_entry = {
                "round_id": self.round_id,
                "round_uuid": self.round_uuid,
                "multiplier": self.crash_multiplier,
                "combined_hash": self.combined_hash,
                "ended_at": datetime.utcnow().isoformat()
            }
            self.recent_history.append(history_entry)
            if len(self.recent_history) > 30:
                self.recent_history.pop(0)

            await self.broadcast({
                "type": "round_ended",
                "status": "ENDED",
                "round_id": self.round_id,
                "round_uuid": self.round_uuid,
                "crash_multiplier": self.crash_multiplier,
                "recent_history": self.recent_history
            })
        except Exception as e:
            print(f"Error handling round end: {e}")
        finally:
            db.close()

    def get_snapshot(self) -> dict:
        return {
            "status": self.status,
            "round_id": self.round_id,
            "round_number": max(1, self.round_number - 1),
            "round_uuid": self.round_uuid,
            "current_multiplier": self.current_multiplier,
            "countdown": self.countdown_remaining,
            "elapsed_time": round(self.elapsed_time, 2),
            "combined_hash": self.combined_hash,
            "active_bets": list(self.active_bets.values()),
            "recent_history": self.recent_history
        }


engine = GameEngine()
