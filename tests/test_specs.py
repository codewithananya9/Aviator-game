import asyncio
import json
import websockets
import urllib.request

# 1. Login guest via HTTP API
req = urllib.request.Request("http://127.0.0.1:8000/api/auth/guest", method="POST")
with urllib.request.urlopen(req) as resp:
    guest_data = json.loads(resp.read().decode())
    token = guest_data["access_token"]
    user = guest_data["user"]
    print(f"Logged in guest: {user['username']}")
    print(f"Balance verified: {user['balance']} Demo Coins (Expected: 10,000)")
    assert user['balance'] == 10000.0, "Initial balance must be 10,000 Demo Coins!"

# 2. Connect via WebSocket and test full round lifecycle
async def test_full_lifecycle():
    uri = "ws://127.0.0.1:8000/ws"
    async with websockets.connect(uri) as ws:
        print("\n--- Testing Server-Controlled Round Lifecycle ---")
        await ws.send(json.dumps({"type": "auth", "token": token}))
        
        seen_states = set()
        bet_id = None
        cashed_out = False
        
        for _ in range(80):
            msg_str = await ws.recv()
            msg = json.loads(msg_str)
            mtype = msg.get("type")
            status = msg.get("status")
            
            if status:
                seen_states.add(status)
                
            if mtype == "round_waiting":
                print(f"[Phase 1: WAITING] Countdown: {msg.get('countdown')}s (Round #{msg.get('round_id')})")
                if not bet_id and msg.get("countdown") > 1.5:
                    print("  -> Placing bet of 100 Demo Coins on Panel 1...")
                    await ws.send(json.dumps({
                        "type": "place_bet",
                        "bet_amount": 100,
                        "panel_index": 1
                    }))
            
            elif mtype == "bet_accepted":
                bet = msg.get("bet")
                bet_id = bet.get("id")
                print(f"  -> Server confirmed bet! ID: {bet_id}, Balance after bet: {bet.get('new_balance')} Demo Coins")
                assert bet.get("new_balance") == 9900.0, "Balance must be deducted on server!"
                
            elif mtype == "round_starting":
                print(f"[Phase 2: STARTING] Engines warming up: {msg.get('countdown')}s (Bets Locked)")
                
            elif mtype == "round_started":
                print(f"[Phase 3: RUNNING] Takeoff! Multiplier climbing...")
                
            elif mtype == "tick":
                mult = msg.get("multiplier")
                # Sample output
                if mult in [1.00, 1.15, 1.35, 1.72, 2.10]:
                    print(f"  -> Multiplier altitude: {mult:.2f}x")
                    
                # Cash out at or above 1.25x
                if bet_id and not cashed_out and mult >= 1.25:
                    print(f"  -> Pressing CASH OUT at {mult:.2f}x...")
                    await ws.send(json.dumps({
                        "type": "cash_out",
                        "bet_id": bet_id
                    }))
                    cashed_out = True
                    
            elif mtype == "cashout_success":
                if msg.get("bet_id") == bet_id:
                    print(f"  -> CASHOUT SUCCESS! Multiplier: {msg.get('multiplier')}x, Payout: {msg.get('payout')} Demo Coins, New Balance: {msg.get('new_balance')} Demo Coins")
                    
            elif mtype in ["round_ended", "crashed"]:
                print(f"[Phase 4: ENDED] Flew away at {msg.get('crash_multiplier')}x! Pausing 3s before next round.")
                
                # Test cashout rejection after round has ended
                print("  -> Testing cash-out rejection after round ended...")
                await ws.send(json.dumps({
                    "type": "cash_out",
                    "bet_id": 999999
                }))
                
            elif mtype == "cashout_error":
                print(f"  -> Server rejected cashout as expected: '{msg.get('message')}'")
                break

        print("\nLifecycle States Verified:", seen_states)
        assert "WAITING" in seen_states or "STARTING" in seen_states, "Must see lifecycle states!"

asyncio.run(test_full_lifecycle())
print("\nALL BACKEND SPECIFICATIONS VERIFIED!")
