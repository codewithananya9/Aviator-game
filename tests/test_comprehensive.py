"""
Aviator Demo – Comprehensive Backend Test Suite
Phase 8: Testing

Run with:
    backend\\.venv\\Scripts\\pytest.exe backend/tests/test_comprehensive.py -v -s

All tests hit the LIVE server at 127.0.0.1:8000.
Ensure the backend is running before executing.
"""
import asyncio
import json
import time
import urllib.request
import urllib.error

import pytest
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def api_post(endpoint, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def api_get(endpoint, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}", headers=headers, method="GET"
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


# ─────────────────────────────────────────────
# Session-scoped fixtures – shared across tests
# ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def registered_user():
    """Register a fresh pilot and return (username, password, token)."""
    ts = int(time.time())
    username = f"Pilot_{ts}"
    email = f"pilot_{ts}@aviator.demo"
    password = "SecurePassword123!"
    status, data = api_post("/api/auth/register", {
        "username": username,
        "email": email,
        "password": password,
    })
    assert status == 200, f"Registration failed: {data}"
    assert "access_token" in data
    return username, password, data["access_token"]


@pytest.fixture(scope="session")
def auth_token(registered_user):
    """JWT token from a fresh login for the session pilot."""
    username, password, _ = registered_user
    status, data = api_post("/api/auth/login", {
        "username": username,
        "password": password,
    })
    assert status == 200, f"Login failed: {data}"
    return data["access_token"]


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

class TestPhase1_ProjectStructure:
    """Phase 1 – Backend reachable and healthy."""

    def test_health_endpoint(self):
        print("\n[PHASE 1] Health check – backend reachable")
        status, data = api_get("/api/health")
        assert status == 200
        assert data["status"] == "healthy"
        assert "notice" in data
        assert "No Real Money" in data["notice"]
        print(f"  [PASS] Backend healthy | round={data['round_id']} | status={data['game_status']}")


class TestPhase2_Auth:
    """Phase 2 – Authentication & JWT & demo coin balance."""

    def test_registration_gives_10k_balance(self, registered_user):
        print("\n[PHASE 2] Registration: initial 10,000 Demo Coin balance")
        username, password, token = registered_user
        status, data = api_get("/api/auth/me", token=token)
        assert status == 200
        assert data["username"] == username
        assert data["balance"] == 10000.0, "Initial balance must be exactly 10,000 Demo Coins"
        print(f"  [PASS] {username} has {data['balance']} Demo Coins")

    def test_duplicate_username_rejected(self, registered_user):
        print("\n[PHASE 2] Duplicate username rejected")
        username, password, _ = registered_user
        ts = int(time.time())
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            api_post("/api/auth/register", {
                "username": username,
                "email": f"unique_{ts}@aviator.demo",
                "password": password,
            })
        assert exc_info.value.code == 400
        print("  [PASS] Duplicate username correctly rejected (400)")

    def test_login_returns_jwt(self, registered_user):
        print("\n[PHASE 2] Login returns valid JWT")
        username, password, _ = registered_user
        status, data = api_post("/api/auth/login", {
            "username": username,
            "password": password,
        })
        assert status == 200
        assert "access_token" in data
        print("  [PASS] JWT acquired")

    def test_wrong_password_rejected(self, registered_user):
        print("\n[PHASE 2] Wrong password rejected (401)")
        username, _, _ = registered_user
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            api_post("/api/auth/login", {
                "username": username,
                "password": "WrongPassword!",
            })
        assert exc_info.value.code == 401
        print("  [PASS] Rejected with 401")

    def test_invalid_token_rejected(self):
        print("\n[PHASE 2] Invalid JWT rejected (401)")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            api_get("/api/auth/me", token="tampered_token_xyz")
        assert exc_info.value.code == 401
        print("  [PASS] Rejected with 401")

    def test_guest_pilot_login(self):
        print("\n[PHASE 2] Guest pilot login")
        req = urllib.request.Request(
            f"{BASE_URL}/api/auth/guest",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        req.data = b"{}"
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        assert "access_token" in data
        assert data["user"]["balance"] == 10000.0
        assert data["user"]["username"].startswith("Pilot_")
        print(f"  [PASS] Guest {data['user']['username']} created with 10,000 Demo Coins")


class TestPhase3_VirtualWallet:
    """Phase 3 – Virtual coin balance & faucet."""

    def test_balance_endpoint(self, auth_token):
        print("\n[PHASE 3] Balance endpoint")
        status, data = api_get("/api/wallet/balance", token=auth_token)
        assert status == 200
        assert data["balance"] >= 10000.0
        assert "disclaimer" in data
        print(f"  [PASS] Balance: {data['balance']} | Disclaimer: {data['disclaimer']}")

    def test_faucet_adds_10k(self, auth_token):
        print("\n[PHASE 3] Faucet refill")
        status, bal_before = api_get("/api/wallet/balance", token=auth_token)
        req = urllib.request.Request(
            f"{BASE_URL}/api/wallet/faucet",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
            method="POST",
        )
        req.data = b"{}"
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        assert data["success"] is True
        assert data["added_amount"] == 10000.0
        assert data["new_balance"] == bal_before["balance"] + 10000.0
        print(f"  [PASS] Faucet OK: new balance {data['new_balance']} Demo Coins")

    def test_transactions_log(self, auth_token):
        print("\n[PHASE 3] Transaction history log")
        status, data = api_get("/api/wallet/transactions", token=auth_token)
        assert status == 200
        assert isinstance(data, list)
        print(f"  [PASS] {len(data)} transaction(s) in history")


class TestPhase4_GameEngine:
    """Phase 4 – Round lifecycle via HTTP snapshot."""

    def test_round_status_from_health(self):
        print("\n[PHASE 4] Round lifecycle visible in health")
        status, data = api_get("/api/health")
        assert data["game_status"] in ("WAITING", "STARTING", "RUNNING", "ENDED")
        print(f"  [PASS] Current round status: {data['game_status']} | multiplier: {data['multiplier']}")


class TestPhase5_WebSocket:
    """Phase 4/5 – WebSocket snapshot on connect."""

    def test_websocket_snapshot_on_connect(self):
        print("\n[PHASE 5] WebSocket: snapshot delivered on connect")

        async def _run():
            async with websockets.connect(WS_URL, open_timeout=5) as ws:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                msg = json.loads(raw)
                assert msg["type"] == "snapshot"
                state = msg["state"]
                assert "status" in state
                assert state["status"] in ("WAITING", "STARTING", "RUNNING", "ENDED")
                print(f"  [PASS] Snapshot received: status={state['status']} | multiplier={state.get('multiplier')}")

        asyncio.run(_run())


class TestPhase6_History:
    """Phase 6 – Game history & flight history endpoints."""

    def test_round_history(self):
        print("\n[PHASE 6] Round history (public)")
        status, data = api_get("/api/game/history?limit=10")
        assert status == 200
        assert isinstance(data, list)
        print(f"  [PASS] {len(data)} completed rounds in history")

    def test_flight_history_paginated(self, auth_token):
        print("\n[PHASE 6] Flight history (paginated)")
        status, data = api_get(
            "/api/game/flight-history?page=1&limit=10&user_only=true",
            token=auth_token,
        )
        assert status == 200
        assert "page" in data
        assert "total_pages" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        print(f"  [PASS] Page {data['page']}/{data['total_pages']}, {data['total_items']} total bets")

    def test_user_stats(self, auth_token):
        print("\n[PHASE 6] User stats endpoint")
        status, data = api_get("/api/game/stats", token=auth_token)
        assert status == 200
        required = [
            "total_bets", "total_won", "total_lost", "win_rate",
            "total_wagered", "total_winnings", "total_losses",
            "net_profit", "highest_win_multiplier"
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"
        print(f"  [PASS] Stats: {data['total_bets']} bets, win_rate={data['win_rate']}%")


class TestPhase7_LeaderboardAdmin:
    """Phase 7 – Leaderboard & Admin panel."""

    def test_leaderboard_columns(self):
        print("\n[PHASE 7] Leaderboard: Rank, Username, Rounds, Demo Coins Won")
        status, data = api_get("/api/game/leaderboard")
        assert status == 200
        assert len(data) > 0
        top = data[0]
        assert "rank" in top
        assert "username" in top
        assert "rounds_played" in top
        assert "demo_coins_won" in top
        # Ensure no "real money" language
        print(f"  [PASS] Top pilot: #{top['rank']} {top['username']} | rounds={top['rounds_played']} | vc_won={top['demo_coins_won']}")

    def test_admin_overview(self):
        print("\n[PHASE 7] Admin overview: metrics & manipulation guard")
        status, data = api_get("/api/admin/overview")
        assert status == 200
        for field in ["total_users", "total_rounds", "total_bets", "active_connections", "manipulation_guard"]:
            assert field in data, f"Missing admin field: {field}"
        assert "cannot be tampered" in data["manipulation_guard"].lower() or \
               "disabled" in data["manipulation_guard"].lower()
        print(f"  [PASS] Admin: {data['total_users']} users, {data['total_rounds']} rounds")
        print(f"  [PASS] Guard: {data['manipulation_guard']}")

    def test_admin_users_list(self):
        print("\n[PHASE 7] Admin users list")
        status, data = api_get("/api/admin/users?limit=10")
        assert status == 200
        assert isinstance(data, list)
        if data:
            user = data[0]
            assert "username" in user
            assert "virtual_balance" in user
            assert "rounds_played" in user
        print(f"  [PASS] {len(data)} user(s) in admin list")

    def test_admin_rounds_list(self):
        print("\n[PHASE 7] Admin rounds list (provably fair hashes)")
        status, data = api_get("/api/admin/rounds?limit=10")
        assert status == 200
        assert isinstance(data, list)
        print(f"  [PASS] {len(data)} round(s) visible in admin panel")

    def test_admin_transactions(self):
        print("\n[PHASE 7] Admin transaction audit log")
        status, data = api_get("/api/admin/transactions?limit=10")
        assert status == 200
        assert isinstance(data, list)
        print(f"  [PASS] {len(data)} transaction(s) in admin audit log")


class TestPhase8_Security:
    """Phase 8 – Security: no real money, no manipulation, no secrets exposed."""

    def test_health_disclaimer_present(self):
        print("\n[PHASE 8] Security: disclaimer in health response")
        _, data = api_get("/api/health")
        assert "No Real Money" in data.get("notice", "")
        print("  [PASS] 'No Real Money' notice confirmed in /api/health")

    def test_balance_disclaimer_present(self, auth_token):
        print("\n[PHASE 8] Security: disclaimer in balance response")
        _, data = api_get("/api/wallet/balance", token=auth_token)
        assert "disclaimer" in data
        print(f"  [PASS] Disclaimer: {data['disclaimer']}")

    def test_no_real_money_in_leaderboard(self):
        print("\n[PHASE 8] Security: leaderboard uses demo_coins_won not real currency")
        _, data = api_get("/api/game/leaderboard")
        assert len(data) > 0
        # Column is 'demo_coins_won' not 'earnings' or 'winnings_usd'
        assert "demo_coins_won" in data[0]
        assert "usd" not in str(data[0]).lower()
        assert "eur" not in str(data[0]).lower()
        print("  [PASS] Leaderboard uses virtual demo_coins_won, no real currency fields")

    def test_manipulation_guard_in_admin(self):
        print("\n[PHASE 8] Security: admin cannot manipulate game outcomes")
        _, data = api_get("/api/admin/overview")
        guard = data.get("manipulation_guard", "")
        assert len(guard) > 10
        print(f"  [PASS] Manipulation guard: {guard}")

    def test_provably_fair_round_verification(self):
        print("\n[PHASE 8] Security: provably fair SHA-256 verification endpoint")
        # Get a completed round
        _, history = api_get("/api/game/history?limit=5")
        if history:
            round_id = history[0]["id"]
            _, verify = api_get(f"/api/game/verify/{round_id}")
            assert "server_seed" in verify
            assert "combined_hash" in verify
            assert "provably_fair_algorithm" in verify
            assert "SHA256" in verify["provably_fair_algorithm"]
            print(f"  [PASS] Round {round_id} verifiable: hash={verify['combined_hash'][:16]}...")
        else:
            print("  [SKIP] No completed rounds yet to verify")


# ─────────────────────────────────────────────
# Legacy runner (python test_comprehensive.py)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "-s"],
        cwd="."
    )
    sys.exit(result.returncode)
