from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, synonym
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    # Virtual demo balance only (10,000 Demo Coins)
    virtual_balance = Column(Float, default=10000.0, nullable=False)
    avatar_color = Column(String(20), default="#e53935")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Synonym so code using user.balance works seamlessly
    balance = synonym("virtual_balance")

    player_rounds = relationship("PlayerRound", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class GameRound(Base):
    __tablename__ = "game_rounds"

    id = Column(Integer, primary_key=True, index=True)
    round_number = Column(Integer, unique=True, index=True, nullable=True)
    round_uuid = Column(String(36), unique=True, index=True, nullable=False)
    status = Column(String(20), default="WAITING")  # WAITING, STARTING, RUNNING, ENDED
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    end_multiplier = Column(Float, nullable=False)

    # Provably Fair SHA-256 cryptographic fields
    server_seed = Column(String(64), nullable=False)
    client_seed = Column(String(64), default="aviator-demo-community-seed")
    combined_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Synonyms for backwards compatibility
    crash_multiplier = synonym("end_multiplier")
    started_at = synonym("start_time")
    ended_at = synonym("end_time")

    player_rounds = relationship("PlayerRound", back_populates="game_round", cascade="all, delete-orphan")


class PlayerRound(Base):
    """
    User participation in a specific GameRound (virtual stake & cashout).
    """
    __tablename__ = "player_rounds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    round_id = Column(Integer, ForeignKey("game_rounds.id"), nullable=False)
    virtual_stake = Column(Float, nullable=False)
    auto_cashout = Column(Float, nullable=True)
    cashout_multiplier = Column(Float, nullable=True)
    payout = Column(Float, default=0.0)
    result = Column(String(20), default="PENDING")  # PENDING, WON, LOST, CANCELLED
    panel_index = Column(Integer, default=1)  # 1 or 2 for dual bet panels
    created_at = Column(DateTime, default=datetime.utcnow)

    # Synonyms
    bet_amount = synonym("virtual_stake")
    status = synonym("result")

    user = relationship("User", back_populates="player_rounds")
    game_round = relationship("GameRound", back_populates="player_rounds")


# Alias Bet to PlayerRound for backward compatibility
Bet = PlayerRound


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    tx_type = Column(String(30), nullable=False)  # INITIAL_CREDIT, BET_PLACED, BET_WON, FAUCET_RELOAD
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
