from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import User, Transaction
from ..schemas import FaucetResponse
from ..auth import get_current_user

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


@router.get("/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    return {
        "balance": round(current_user.balance, 2),
        "currency": "Demo Coins",
        "disclaimer": "Demo Coins — No Real Money"
    }


@router.post("/faucet", response_model=FaucetResponse)
def request_faucet(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Virtual Faucet / Refill:
    Grants 10,000 free virtual Demo Coins for portfolio testing.
    """
    refill_amount = 10000.0
    current_user.balance = round(current_user.balance + refill_amount, 2)

    tx = Transaction(
        user_id=current_user.id,
        amount=refill_amount,
        balance_after=current_user.balance,
        tx_type="FAUCET_RELOAD",
        description="Demo Faucet Refill: +10,000 Demo Coins (Demo Coins — No Real Money)"
    )
    db.add(tx)
    db.commit()

    return FaucetResponse(
        success=True,
        message="10,000 Demo Coins added to your demo balance!",
        new_balance=current_user.balance,
        added_amount=refill_amount
    )


@router.get("/transactions")
def get_transactions(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(desc(Transaction.id))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "tx_type": t.tx_type,
            "description": t.description,
            "created_at": t.created_at
        }
        for t in txs
    ]
