# ✈️ Aviator Demo

> **⚠️ IMPORTANT DISCLAIMER**  
> This is a **portfolio / educational demonstration project**.  
> It uses **100% free virtual Demo Coins (VC)** with **zero real-money value**.  
> There are **NO real-money bets, deposits, withdrawals, payment gateways, cryptocurrencies, or gambling features** of any kind.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Getting Started](#-getting-started)
- [Development Phases](#-development-phases)
- [API Reference](#-api-reference)
- [Provably Fair Algorithm](#-provably-fair-algorithm)
- [Running Tests](#-running-tests)
- [Production Deployment](#-production-deployment)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Server-authoritative game engine** | Round lifecycle: `WAITING → STARTING → RUNNING → ENDED`, looping automatically |
| **Virtual Demo Coins (VC)** | Every account starts with 10,000 VC. Faucet refill available (+10,000 anytime) |
| **Dual Bet Panels** | Place two independent bets per round with auto-cash-out targets |
| **Provably Fair** | SHA-256 seed verification – players can inspect any round's hash |
| **Real-time WebSocket** | Live multiplier ticks, bet events, and crash broadcasts |
| **60 FPS Canvas Animation** | Supersonic jet, Bézier flight arc, particles, radar sweep, crash shockwave |
| **Web Audio FX** | Procedural engine hum, takeoff whoosh, cashout arpeggio, crash bass drop |
| **Leaderboard** | Rank, Username, Rounds Played, Demo Coins Won |
| **Game History** | Paginated flight log: Round#, Date, Stake, Cash-out×, Result, VC Won/Lost |
| **Admin Dashboard** | Read-only: users, rounds, stats, active connections, transaction audit |
| **JWT Authentication** | Register / Login / 1-Click Guest Pilot |
| **Responsive UI** | Mobile-friendly, white/cream + blue accent design system |

---

## 🏗️ Architecture

```
aviator-demo/
│
├── backend/                        # Python FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint, WebSocket handler, lifespan
│   │   ├── database.py             # SQLAlchemy engine + session factory
│   │   ├── models.py               # User, GameRound, Bet, Transaction ORM models
│   │   ├── schemas.py              # Pydantic v2 request/response schemas
│   │   ├── auth.py                 # bcrypt hashing + JWT encode/decode
│   │   ├── game_engine.py          # Authoritative async game loop (Pareto RNG)
│   │   ├── websocket.py            # ConnectionManager + message routing
│   │   └── routes/
│   │       ├── auth_routes.py      # POST /api/auth/{register,login,guest} · GET /api/auth/me
│   │       ├── game_routes.py      # GET /api/game/{stats,leaderboard,history,flight-history,verify}
│   │       ├── wallet_routes.py    # GET /api/wallet/balance · POST /api/wallet/faucet
│   │       └── admin_routes.py     # GET /api/admin/{overview,users,rounds,transactions}
│   ├── tests/
│   │   └── test_comprehensive.py   # 25 pytest tests covering all 9 phases
│   ├── requirements.txt
│   ├── .env.example                # ← copy to .env and fill in
│   └── aviator.db                  # SQLite (auto-created on first run)
│
├── frontend/                       # React 19 + Vite
│   ├── src/
│   │   ├── App.jsx                 # Root orchestrator, WebSocket consumer
│   │   ├── components/
│   │   │   ├── Header.jsx          # Nav: History | Leaderboard | Fairness | Admin | Profile
│   │   │   ├── DisclaimerBanner.jsx
│   │   │   ├── FlightCanvas.jsx    # 60 FPS HTML5 Canvas visualizer
│   │   │   ├── BetPanel.jsx        # Dual betting controls (auto cash-out, chip presets)
│   │   │   ├── LiveBetsTable.jsx   # Real-time bet feed
│   │   │   ├── MultiplierHistory.jsx
│   │   │   ├── AuthModal.jsx
│   │   │   ├── ProfileModal.jsx    # Pilot dashboard: stats, tabs, recent history
│   │   │   ├── LeaderboardModal.jsx
│   │   │   ├── HistoryModal.jsx    # Paginated flight history
│   │   │   ├── AdminModal.jsx      # Admin dashboard (read-only)
│   │   │   ├── FairnessModal.jsx   # SHA-256 provably fair verifier
│   │   │   └── HowToPlayModal.jsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.js     # Auto-reconnecting WebSocket hook
│   │   ├── services/
│   │   │   ├── api.js              # Typed REST API client
│   │   │   └── audio.js            # Web Audio API synthesizer (no mp3 files)
│   │   └── styles/
│   │       └── index.css           # CSS design system (1017 lines)
│   ├── package.json
│   └── vite.config.js              # Vite proxy: /api → :8000, /ws → ws://localhost:8000
│
├── README.md
└── .gitignore
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm

### 1 – Clone

```bash
git clone <repo-url>
cd aviator-demo
```

### 2 – Backend

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if needed (defaults work for local dev)

# Start backend (auto-creates aviator.db on first run)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**FastAPI interactive docs:** http://127.0.0.1:8000/docs

### 3 – Frontend

```bash
cd frontend

npm install
npm run dev
```

**Open:** http://127.0.0.1:3000

---

## 🔄 Development Phases

This project was built phase-by-phase, with each phase verified before continuing:

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Project structure, frontend + backend scaffold, database, run both servers | ✅ |
| 2 | Authentication, User model, JWT, demo coin balance | ✅ |
| 3 | Game engine, round lifecycle, virtual coin logic | ✅ |
| 4 | WebSocket real-time communication, live multiplier | ✅ |
| 5 | Plane animation, main game UI | ✅ |
| 6 | Cash-out, game history, pilot dashboard | ✅ |
| 7 | Leaderboard, admin panel | ✅ |
| 8 | Testing (25 pytest tests), security review, responsive design | ✅ |
| 9 | README, production config, deployment preparation | ✅ |

---

## 🌐 API Reference

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register: `{username, email, password}` |
| `POST` | `/api/auth/login` | Login: `{username, password}` → JWT |
| `POST` | `/api/auth/guest` | Create guest pilot with 10,000 VC |
| `GET`  | `/api/auth/me` | Get current user (requires JWT) |

### Wallet

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/wallet/balance` | Current VC balance + disclaimer |
| `POST` | `/api/wallet/faucet` | Claim +10,000 Demo Coins refill |
| `GET`  | `/api/wallet/transactions` | Transaction history log |

### Game

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/game/stats` | User stats (bets, win rate, VC won/lost) |
| `GET`  | `/api/game/leaderboard` | Top 20 pilots by VC balance |
| `GET`  | `/api/game/history` | Recent crash multipliers (public) |
| `GET`  | `/api/game/flight-history` | Paginated personal bet history |
| `GET`  | `/api/game/verify/{round_id}` | Provably fair seed verification |

### Admin (read-only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/admin/overview` | System stats + manipulation guard notice |
| `GET`  | `/api/admin/users` | Registered users list |
| `GET`  | `/api/admin/rounds` | All game rounds with hashes |
| `GET`  | `/api/admin/transactions` | Full transaction audit log |

### WebSocket

Connect to `ws://127.0.0.1:8000/ws`

**Server → Client messages:**

| Type | Description |
|------|-------------|
| `snapshot` | Full game state on connection |
| `round_waiting` | Countdown to next round |
| `round_starting` | Engines spool up, bets locked |
| `tick` | Live multiplier update during flight |
| `round_ended` | Crash multiplier + round summary |
| `bet_accepted` | Server confirmed bet placement |
| `cashout_success` | Cash-out confirmed, payout credited |
| `cashout_error` | Cash-out rejected (duplicate, late, etc.) |

**Client → Server messages:**

| Type | Payload | Description |
|------|---------|-------------|
| `auth` | `{token}` | Authenticate WebSocket session |
| `place_bet` | `{bet_amount, panel_index, auto_cashout?}` | Place a bet during WAITING |
| `cash_out` | `{bet_id}` | Cash out during RUNNING |
| `cancel_bet` | `{bet_id}` | Cancel unmatched bet during WAITING |

---

## 🛡️ Provably Fair Algorithm

Each round's crash multiplier is deterministically derived from a SHA-256 hash:

1. **Seeds combined:** `hash = SHA256(server_seed : client_seed : timestamp)`
2. **Extract 52 bits:** `int_value = int(hash[:13], 16)`
3. **House edge (4%):** if `int_value % 25 == 0` → `M = 1.00x` (instant crash)
4. **Multiplier curve:**

$$M = \max\left(1.00,\ \min\left(500.00,\ \frac{0.97}{1.0 - \text{ratio}}\right)\right)$$

Players can verify any historical round via the **Fairness modal** in-app or the `/api/game/verify/{round_id}` endpoint.

---

## 🧪 Running Tests

Ensure the backend is running at `http://127.0.0.1:8000`, then:

```bash
cd aviator-demo

# Run the full Phase 8 test suite (25 tests)
backend\.venv\Scripts\pytest.exe backend/tests/test_comprehensive.py -v -s

# Linux/macOS:
backend/.venv/bin/pytest backend/tests/test_comprehensive.py -v -s
```

**Coverage:**
- Phase 1: Backend health / reachability
- Phase 2: Registration, JWT, login, duplicate rejection, guest login
- Phase 3: Virtual wallet balance, faucet, transaction log
- Phase 4: Round lifecycle visible in health endpoint
- Phase 5: WebSocket snapshot on connect
- Phase 6: History (public & paginated personal), user stats
- Phase 7: Leaderboard columns, admin overview/users/rounds/transactions
- Phase 8: Security – disclaimers, no real currency, manipulation guard, provably fair

---

## 🚀 Production Deployment

### Environment

1. Set `SECRET_KEY` to a cryptographically random value:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Set `DATABASE_URL` to a PostgreSQL connection string
3. Set `ALLOWED_ORIGINS` to your production frontend domain
4. Set `ENVIRONMENT=production`

### Backend (Gunicorn + uvicorn workers)

```bash
pip install gunicorn
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend (static build)

```bash
cd frontend
npm run build
# Serve dist/ with nginx, Caddy, or any static host
```

### Sample nginx config

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Static frontend
    root /var/www/aviator-demo/frontend/dist;
    index index.html;
    try_files $uri $uri/ /index.html;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 📜 License

MIT License — Built strictly as an **educational portfolio demonstration**.  
No real-money transactions. No gambling. Virtual Demo Coins only.
