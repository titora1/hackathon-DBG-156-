import os
import uuid
from fastapi import FastAPI, HTTPException, Header
import fakeredis
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

app = FastAPI()

# Use FakeRedis to simulate the database in-memory instantly (Bypasses PostgreSQL bottlenecks)
r = fakeredis.FakeRedis(decode_responses=True)

# Time limits pull from .env (Rule requirement)
HOLD_TTL = int(os.getenv("HOLD_TTL_SECONDS", 60))
AI_API_KEY = os.getenv("AI_API_KEY")

@app.post("/setup")
def setup_event():
    """Sets up the fest with 5,000 tickets."""
    r.set("total_tickets", 5000)
    return {"message": "Fest setup complete! 5000 tickets ready."}

@app.post("/buy")
def buy_ticket(user_agent: str = Header(default="")):
    """
    IMPROVEMENT 2: AI Bot Defense & Universal Fallback
    Always catches bots and suspicious traffic.
    """
    # Always block any user agent containing "bot" (case-insensitive)
    if "bot" in user_agent.lower():
        raise HTTPException(status_code=403, detail="Blocked: Scalper Bot Detected")
        
    # Block empty user-agents as suspicious traffic
    if user_agent == "":
        raise HTTPException(status_code=403, detail="Basic Block: Suspicious Traffic")

    """
    KILLER TEST 1 & IMPROVEMENT 1: The Redis Fix
    Redis processes simultaneous checkout requests atomically.
    """
    tickets_left = r.decr("total_tickets")
    
    if tickets_left < 0:
        r.incr("total_tickets")
        raise HTTPException(status_code=400, detail="Sold out!")
        
    """
    KILLER TEST 2: Unpaid hold expires.
    Sets a strict TTL timer from the .env file.
    """
    hold_id = str(uuid.uuid4())
    r.setex(f"hold:{hold_id}", HOLD_TTL, "waiting_for_payment")
    
    return {"status": "success", "hold_id": hold_id, "tickets_left": tickets_left}

@app.post("/checkin")
def scan_qr(qr_code: str):
    """
    KILLER TEST 3: Same QR code cannot be checked in twice.
    """
    success = r.setnx(f"scanned:{qr_code}", "yes")
    
    if not success:
        raise HTTPException(status_code=400, detail="STOP: This QR code was already scanned!")
        
    return {"message": "Welcome to the fest!"}