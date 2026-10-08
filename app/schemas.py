from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# User Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    balance: float
    avatar_color: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserStats(BaseModel):
    total_bets: int
    total_won: int
    total_lost: int
    win_rate: float
    total_wagered: float
    total_payout: float
    total_winnings: float
    total_losses: float
    successful_cashouts: int
    net_profit: float
    highest_win_multiplier: float

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

# Bet Schemas
class BetCreate(BaseModel):
    bet_amount: float = Field(..., gt=0)
    auto_cashout: Optional[float] = Field(None, gt=1.0)
    panel_index: int = Field(1, ge=1, le=2)

class CashOutRequest(BaseModel):
    bet_id: int

class BetResponse(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    round_id: int
    bet_amount: float
    auto_cashout: Optional[float] = None
    cashout_multiplier: Optional[float] = None
    payout: float
    status: str
    panel_index: int
    created_at: datetime

    class Config:
        from_attributes = True

# Round Schemas
class RoundResponse(BaseModel):
    id: int
    round_uuid: str
    crash_multiplier: float
    status: str
    combined_hash: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RoundHistoryItem(BaseModel):
    id: int
    round_uuid: str
    crash_multiplier: float
    combined_hash: str
    ended_at: Optional[datetime] = None

class LeaderboardItem(BaseModel):
    rank: int
    username: str
    rounds_played: int
    demo_coins_won: float
    balance: float
    highest_multiplier: float
    avatar_color: str

class FaucetResponse(BaseModel):
    success: bool
    message: str
    new_balance: float
    added_amount: float

# Section 14: Comprehensive Game History Schemas
class FlightHistoryItem(BaseModel):
    id: int
    round_number: Optional[int] = None
    round_id: int
    round_uuid: str
    date_time: datetime
    virtual_stake: float
    cashout_multiplier: Optional[float] = None
    result: str  # "CASHED_OUT", "BUSTED", "CANCELLED"
    virtual_coins_won_lost: float
    panel_index: int

class PaginatedHistoryResponse(BaseModel):
    total_items: int
    page: int
    limit: int
    total_pages: int
    items: List[FlightHistoryItem]

# Section 15: Admin Dashboard Schemas
class AdminStats(BaseModel):
    total_users: int
    total_rounds: int
    total_bets: int
    total_transactions: int
    active_connections: int
    total_virtual_wagered: float
    total_virtual_payout: float
    current_round_id: int
    current_round_status: str
    manipulation_guard: str = "Architecturally Disabled: Server-authoritative Pareto RNG cannot be tampered."

class AdminUserItem(BaseModel):
    id: int
    username: str
    email: str
    virtual_balance: float
    rounds_played: int
    created_at: datetime

class AdminRoundItem(BaseModel):
    id: int
    round_number: Optional[int] = None
    round_uuid: str
    end_multiplier: float
    status: str
    server_seed: str
    client_seed: str
    combined_hash: str
    created_at: datetime
    ended_at: Optional[datetime] = None

class AdminTransactionItem(BaseModel):
    id: int
    user_id: int
    username: str
    amount: float
    balance_after: float
    tx_type: str
    description: Optional[str] = None
    created_at: datetime
