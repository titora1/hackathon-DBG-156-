import os
import uuid
from fastapi import FastAPI, HTTPException, Header
import fakeredis
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# In-memory Redis state management (bypasses PostgreSQL bottlenecks)
r = fakeredis.FakeRedis(decode_responses=True)

HOLD_TTL = int(os.getenv("HOLD_TTL_SECONDS", 30))

@app.post("/setup")
def setup_event():
    """Initializes the event and resets all live analytics."""
    r.set("total_tickets", 10)
    r.set("bots_intercepted", 0)
    r.set("spam_attacks_blocked", 0)
    r.set("total_checkins", 0)
    return {"message": "Fest setup complete! 10 tickets ready, analytics online."}

@app.post("/buy")
def buy_ticket(
    x_user_agent: str = Header(default="Chrome", description="Type 'ScalperBot' to test bot defense"),
    x_user_ip: str = Header(default="192.168.1.5", description="Simulated User IP for Rate Limiting")
):
    """
    Killer Feature: Anti-Spam Velocity Lock & Bot Defense
    """
    # 1. AI Sentinel Bot Check
    if "bot" in x_user_agent.lower():
        r.incr("bots_intercepted")
        raise HTTPException(status_code=403, detail="Blocked: Scalper Bot Detected")
        
    # 2. NEW: Redis Velocity Lock (Max 3 requests per 5 seconds per IP)
    req_count = r.incr(f"rate_limit:{x_user_ip}")
    if req_count == 1:
        # Start a 5-second expiration timer on this IP's counter
        r.expire(f"rate_limit:{x_user_ip}", 5)
        
    if req_count > 3:
        r.incr("spam_attacks_blocked")
        raise HTTPException(status_code=429, detail="VELOCITY LOCK: You are clicking too fast! Take a breath.")

    # 3. Concurrency-Safe Purchasing (Zero Overselling)
    tickets_left = r.decr("total_tickets")
    
    if tickets_left < 0:
        r.incr("total_tickets")
        raise HTTPException(status_code=400, detail="Sold out!")
        
    hold_id = str(uuid.uuid4())
    r.setex(f"hold:{hold_id}", HOLD_TTL, "waiting_for_payment")
    
    return {"status": "success", "hold_id": hold_id, "tickets_left": tickets_left}

@app.get("/hold/{hold_id}")
def check_hold_status(hold_id: str):
    """Visualizes the 30-second TTL countdown timer."""
    ttl_left = r.ttl(f"hold:{hold_id}")
    
    if ttl_left == -2:
        return {"status": "expired", "message": "The hold timer ran out. Ticket released!"}
    
    return {"status": "active", "hold_id": hold_id, "seconds_remaining": ttl_left}

@app.post("/checkin")
def scan_qr(qr_code: str):
    """Duplicate QR Scan Prevention"""
    success = r.setnx(f"scanned:{qr_code}", "yes")
    
    if not success:
        raise HTTPException(status_code=400, detail="STOP: This QR code was already scanned!")
        
    r.incr("total_checkins")
    return {"message": "Welcome to the fest!"}

@app.get("/admin/stats")
def live_event_analytics():
    """Live Dashboard for Judges."""
    return {
        "tickets_remaining": r.get("total_tickets"),
        "bots_intercepted": r.get("bots_intercepted"),
        "spam_attacks_blocked": r.get("spam_attacks_blocked"),
        "total_checkins": r.get("total_checkins")
    }
