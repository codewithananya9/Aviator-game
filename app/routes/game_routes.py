from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..database import get_db
from ..models import GameRound, Bet, User
from ..schemas import (
    RoundHistoryItem,
    BetResponse,
    UserStats,
    LeaderboardItem,
    FlightHistoryItem,
    PaginatedHistoryResponse
)
from ..auth import get_current_user, get_current_user_optional
from ..game_engine import engine

router = APIRouter(prefix="/api/game", tags=["game"])


@router.get("/history", response_model=List[RoundHistoryItem])
def get_recent_history(limit: int = Query(30, ge=5, le=100), db: Session = Depends(get_db)):
    rounds = (
        db.query(GameRound)
        .filter(GameRound.status == "CRASHED")
        .order_by(desc(GameRound.id))
        .limit(limit)
        .all()
    )
    return [
        RoundHistoryItem(
            id=r.id,
            round_uuid=r.round_uuid,
            crash_multiplier=r.crash_multiplier,
            combined_hash=r.combined_hash,
            ended_at=r.ended_at
        )
        for r in rounds
    ]


@router.get("/my-bets", response_model=List[BetResponse])
def get_my_bets(
    limit: int = Query(25, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bets = (
        db.query(Bet)
        .filter(Bet.user_id == current_user.id)
        .order_by(desc(Bet.id))
        .limit(limit)
        .all()
    )
    return [
        BetResponse(
            id=b.id,
            user_id=b.user_id,
            username=current_user.username,
            round_id=b.round_id,
            bet_amount=b.bet_amount,
            auto_cashout=b.auto_cashout,
            cashout_multiplier=b.cashout_multiplier,
            payout=b.payout,
            status=b.status,
            panel_index=b.panel_index,
            created_at=b.created_at
        )
        for b in bets
    ]


@router.get("/stats", response_model=UserStats)
def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bets = db.query(Bet).filter(Bet.user_id == current_user.id).all()
    
    total_bets = len(bets)
    won_bets = [b for b in bets if b.status == "CASHED_OUT"]
    lost_bets = [b for b in bets if b.status in ["BUSTED", "LOST"]]
    total_won = len(won_bets)
    total_lost = total_bets - total_won
    
    win_rate = round((total_won / total_bets * 100), 1) if total_bets > 0 else 0.0
    total_wagered = round(sum(b.bet_amount for b in bets), 2)
    total_payout = round(sum(b.payout for b in won_bets), 2)
    total_winnings = total_payout
    total_losses = round(sum(b.bet_amount for b in lost_bets), 2)
    net_profit = round(total_payout - total_wagered, 2)
    
    highest_win = max([b.cashout_multiplier or 0.0 for b in won_bets], default=0.0)

    return UserStats(
        total_bets=total_bets,
        total_won=total_won,
        total_lost=total_lost,
        win_rate=win_rate,
        total_wagered=total_wagered,
        total_payout=total_payout,
        total_winnings=total_winnings,
        total_losses=total_losses,
        successful_cashouts=total_won,
        net_profit=net_profit,
        highest_win_multiplier=round(highest_win, 2)
    )


@router.get("/leaderboard", response_model=List[LeaderboardItem])
def get_leaderboard(db: Session = Depends(get_db)):
    # Section 13: Top pilots based on demo-game statistics
    # Show: Rank, Username, Rounds Played, Demo Coins Won
    top_users = db.query(User).order_by(desc(User.balance)).limit(20).all()

    leaderboard = []
    for rank, user in enumerate(top_users, start=1):
        highest_mult = (
            db.query(func.max(Bet.cashout_multiplier))
            .filter(Bet.user_id == user.id, Bet.status == "CASHED_OUT")
            .scalar()
        ) or 1.0

        total_won = (
            db.query(func.sum(Bet.payout))
            .filter(Bet.user_id == user.id, Bet.status == "CASHED_OUT")
            .scalar()
        ) or 0.0

        rounds_count = (
            db.query(func.count(Bet.id))
            .filter(Bet.user_id == user.id)
            .scalar()
        ) or 0

        leaderboard.append(
            LeaderboardItem(
                rank=rank,
                username=user.username,
                rounds_played=rounds_count,
                demo_coins_won=round(total_won, 2),
                balance=round(user.balance, 2),
                highest_multiplier=round(highest_mult, 2),
                avatar_color=user.avatar_color
            )
        )

    return leaderboard


@router.get("/flight-history", response_model=PaginatedHistoryResponse)
def get_flight_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    user_only: bool = Query(True),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Section 14: Comprehensive Game History Page
    Returns paginated flight records:
    Round number, Date/time, Virtual stake, Cash-out multiplier, Result, Virtual coins won/lost
    """
    query = db.query(Bet, GameRound).join(GameRound, Bet.round_id == GameRound.id)

    if user_only and current_user:
        query = query.filter(Bet.user_id == current_user.id)

    total_items = query.count()
    total_pages = max(1, (total_items + limit - 1) // limit)

    results = (
        query.order_by(desc(Bet.id))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for bet, r in results:
        is_won = bet.status == "CASHED_OUT"
        coins_won_lost = round(bet.payout - bet.bet_amount, 2) if is_won else round(-bet.bet_amount, 2)
        items.append(
            FlightHistoryItem(
                id=bet.id,
                round_number=r.round_number or r.id,
                round_id=r.id,
                round_uuid=r.round_uuid,
                date_time=bet.created_at,
                virtual_stake=bet.bet_amount,
                cashout_multiplier=bet.cashout_multiplier,
                result=bet.status,
                virtual_coins_won_lost=coins_won_lost,
                panel_index=bet.panel_index
            )
        )

    return PaginatedHistoryResponse(
        total_items=total_items,
        page=page,
        limit=limit,
        total_pages=total_pages,
        items=items
    )


@router.get("/verify/{round_id}")
def verify_round(round_id: int, db: Session = Depends(get_db)):
    round_record = db.query(GameRound).filter(GameRound.id == round_id).first()
    if not round_record:
        raise HTTPException(status_code=404, detail="Round not found")

    return {
        "round_id": round_record.id,
        "round_uuid": round_record.round_uuid,
        "crash_multiplier": round_record.crash_multiplier,
        "server_seed": round_record.server_seed,
        "client_seed": round_record.client_seed,
        "combined_hash": round_record.combined_hash,
        "status": round_record.status,
        "started_at": round_record.started_at,
        "ended_at": round_record.ended_at,
        "provably_fair_algorithm": "SHA256(server_seed:client_seed:timestamp)"
    }
