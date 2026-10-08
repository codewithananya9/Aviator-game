from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..database import get_db
from ..models import User, GameRound, Bet, Transaction
from ..schemas import (
    AdminStats,
    AdminUserItem,
    AdminRoundItem,
    AdminTransactionItem
)
from ..game_engine import engine
from ..websocket import ws_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview", response_model=AdminStats)
def get_admin_overview(db: Session = Depends(get_db)):
    """
    Section 15: Admin Dashboard Overview
    Admin can view system health, active connections, total rounds, and demo ledger volume.
    NOTE: Outcome manipulation is architecturally prohibited.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_rounds = db.query(func.count(GameRound.id)).scalar() or 0
    total_bets = db.query(func.count(Bet.id)).scalar() or 0
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0

    total_wagered = db.query(func.sum(Bet.bet_amount)).scalar() or 0.0
    total_payout = db.query(func.sum(Bet.payout)).filter(Bet.status == "CASHED_OUT").scalar() or 0.0

    active_connections = len(ws_manager.active_connections)

    return AdminStats(
        total_users=total_users,
        total_rounds=total_rounds,
        total_bets=total_bets,
        total_transactions=total_transactions,
        active_connections=active_connections,
        total_virtual_wagered=round(total_wagered, 2),
        total_virtual_payout=round(total_payout, 2),
        current_round_id=engine.round_id,
        current_round_status=engine.status,
        manipulation_guard="Architecturally Disabled: Server-authoritative Pareto RNG cannot be tampered."
    )


@router.get("/users", response_model=List[AdminUserItem])
def get_admin_users(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Admin can view registered users and their rounds played."""
    users = db.query(User).order_by(desc(User.id)).limit(limit).all()
    results = []
    for u in users:
        rounds_count = db.query(func.count(Bet.id)).filter(Bet.user_id == u.id).scalar() or 0
        results.append(
            AdminUserItem(
                id=u.id,
                username=u.username,
                email=u.email,
                virtual_balance=round(u.balance, 2),
                rounds_played=rounds_count,
                created_at=u.created_at
            )
        )
    return results


@router.get("/rounds", response_model=List[AdminRoundItem])
def get_admin_rounds(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Admin can view cryptographic rounds and provably fair hashes."""
    rounds = db.query(GameRound).order_by(desc(GameRound.id)).limit(limit).all()
    return [
        AdminRoundItem(
            id=r.id,
            round_number=r.round_number or r.id,
            round_uuid=r.round_uuid,
            end_multiplier=r.end_multiplier,
            status=r.status,
            server_seed=r.server_seed,
            client_seed=r.client_seed,
            combined_hash=r.combined_hash,
            created_at=r.created_at,
            ended_at=r.end_time
        )
        for r in rounds
    ]


@router.get("/transactions", response_model=List[AdminTransactionItem])
def get_admin_transactions(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Admin can audit all system demo transactions."""
    txs = (
        db.query(Transaction, User.username)
        .join(User, Transaction.user_id == User.id)
        .order_by(desc(Transaction.id))
        .limit(limit)
        .all()
    )
    return [
        AdminTransactionItem(
            id=t.id,
            user_id=t.user_id,
            username=uname,
            amount=round(t.amount, 2),
            balance_after=round(t.balance_after, 2),
            tx_type=t.tx_type,
            description=t.description,
            created_at=t.created_at
        )
        for t, uname in txs
    ]
