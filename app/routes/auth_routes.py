import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Transaction
from ..schemas import UserCreate, UserLogin, UserResponse, Token
from ..auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATAR_COLORS = [
    "#ef4444", "#f97316", "#f59e0b", "#10b981", "#06b6d4",
    "#3b82f6", "#6366f1", "#8b5cf6", "#ec4899", "#14b8a6"
]


@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_pw = get_password_hash(user_in.password)
    color = random.choice(AVATAR_COLORS)

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        balance=10000.0,  # 10,000 Free Virtual Demo Coins
        avatar_color=color
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Record welcome bonus transaction
    tx = Transaction(
        user_id=user.id,
        amount=10000.0,
        balance_after=10000.0,
        tx_type="INITIAL_CREDIT",
        description="Welcome bonus: 10,000 free virtual demo credits (Demo Coins — No Real Money)"
    )
    db.add(tx)
    db.commit()

    token = create_access_token(data={"sub": user.username, "id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user.username, "id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/guest", response_model=Token)
def guest_login(db: Session = Depends(get_db)):
    """Instant 1-click guest login for frictionless portfolio demo evaluation"""
    guest_num = random.randint(1000, 99999)
    username = f"Pilot_{guest_num}"
    email = f"guest_{guest_num}@aviator.demo"
    password = f"demo_guest_{guest_num}"
    
    hashed_pw = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_pw,
        balance=10000.0,
        avatar_color=random.choice(AVATAR_COLORS)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    tx = Transaction(
        user_id=user.id,
        amount=10000.0,
        balance_after=10000.0,
        tx_type="INITIAL_CREDIT",
        description="Guest demo credit: 10,000 virtual demo coins (Demo Coins — No Real Money)"
    )
    db.add(tx)
    db.commit()

    token = create_access_token(data={"sub": user.username, "id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
