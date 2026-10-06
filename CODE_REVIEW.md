# HACKBACK code review · DBG-156 · Rush-proof Event Ticketing
- Reviewed at: 2026-10-06T08:24:45Z (2026-10-06T13:54:45+05:30 IST)
- Judged commit: 9b6010d76777633ce8a6c6ed0e84db75f7244008 (2026-10-06T13:16:33+05:30) · the last commit before the code freeze
- Reviewer: AI agent run by a HACKBACK judge

### DBG-156 · Rush-proof Event Ticketing
Commit: 9b6010d76777633ce8a6c6ed0e84db75f7244008 · 2026-10-06T13:16:33+05:30 · Clean-room: OK / see flags

| Section | Score | Why (path:line) |
|---|---|---|
| A. Core flow | 10/30 | Disconnected fragments only. Ticket tiers with individual capacity/price are absent (main.py:19 only sets a flat global `total_tickets`); checkout holds never convert to paid tickets/orders (no payment route, tickets are never created); promo codes and refunds/cancellations are not implemented (not found); check-in API accepts raw strings without validating issued tickets (main.py:70-79). |
| B. Killer Tests | 16/30 | KT1 is atomic and tested (10/10; main.py:49-53). KT2 has a fatal hole: hold key has TTL, but expiring holds never restore inventory or increment `total_tickets` (3/10; main.py:56, 60-68). KT3 has a hole: check-in deduplication is atomic via `SETNX`, but QR is unauthenticated raw string with no token/HMAC validation against tickets (3/10; main.py:70-79). |
| C. Two improvements | 10/20 | Improvement 1 (Atomic Redis locks) partly built (5/10; main.py:49, 56, 73 uses `decr`/`setex`/`setnx` in fakeredis, but missing promised Lua scripts, PostgreSQL persistence, and keyspace notification restock). Improvement 2 (Bot defense / velocity lock) partly built (5/10; main.py:33-46 implements Redis IP velocity limiter and User-Agent check, but promised AI telemetry model was not built). |
| D. Built from their docs | 5/10 | Substantial drift between docs and code. `docs/API.txt:10` specifies `POST /api/tickets/checkout` which is completely missing in main.py; endpoint paths, schemas, and models drift from `docs/API.txt` and `docs/DATA_MODEL.txt`; PostgreSQL cold path was dropped entirely for in-memory fakeredis. |
| E. Engineering | 4/10 | Minimal input validation; zero route authorization (unprotected `POST /setup` allows anyone to reset inventory to 10 at runtime; main.py:16-23); error handling uses basic HTTPExceptions; no .env.example provided (not found); all state is ephemeral in-process fakeredis; prices and money handling are omitted. |
| Total | 45/100 | |

Killer Tests:
1. READY · 10/10 · Atomic capacity decrement via Redis `r.decr("total_tickets")` with negative roll-back (`main.py:49-53`). Proven with concurrent multi-threaded execution test where 2 competing threads for 1 remaining ticket resulted in exactly one HTTP 200 and one HTTP 400 with 0 overselling.
2. PARTIAL · 3/10 · `r.setex(f"hold:{hold_id}", HOLD_TTL, "waiting_for_payment")` sets a 30s TTL from `.env` (`main.py:14, 56`), and `GET /hold/{hold_id}` cosmetically displays `"The hold timer ran out. Ticket released!"` when TTL expires (`main.py:65-66`), but neither the endpoint nor any background listener or keyspace handler increments `total_tickets` back. Expired holds permanently consume inventory (proven via test: `total_tickets` remained 9 after hold expired).
3. PARTIAL · 3/10 · Atomic check-in state change is enforced using Redis `r.setnx(f"scanned:{qr_code}", "yes")` (`main.py:73-77`), proven by second scan returning HTTP 400. However, the QR is an unauthenticated client string (`qr_code: str`) with no unguessable token or HMAC payload, and the system never generates tickets or verifies if the code was legitimately purchased.

Improvements:
1. Redis-backed in-memory atomic state management · 5/10 · Partly built. `main.py:49, 56, 73` uses `r.decr`, `r.setex`, and `r.setnx` via `fakeredis`. However, promised single-threaded Redis Lua scripts (`docs/GAPS.txt:4`), persistent PostgreSQL tables (`docs/ARCHITECTURE.txt:14`), and automatic keyspace notification inventory restock (`docs/ARCHITECTURE.txt:20`) were omitted.
2. AI-Driven Bot Defense & Anti-Spam Velocity Lock · 5/10 · Partly built. `docs/GAPS.txt:6-10` promised an AI model evaluating telemetry to generate a live "bot probability score", but `main.py:34` uses only a basic substring filter `if "bot" in x_user_agent.lower()`. However, the team built and wired an active Redis velocity lock (`main.py:38-46`) enforcing a sliding-window rate limit of 3 requests per 5s per IP.

Flags:
- Clean-room: OK. Commits began after Oct 5 4:00 PM IST (first commit `a052fec` at 2026-10-05T23:03:41+05:30); docs were committed prior to code; all commits completed before the Oct 6 1:30 PM IST freeze; code is original Python/FastAPI rather than copied Hi.Events PHP code.
- Fake: `docs/GAPS.txt:6-9` and `submission.txt:8` advertise an "AI-driven traffic sentinel" sending telemetry to an AI model for bot scoring, but the code merely inspects `x_user_agent` for the substring `"bot"` (`main.py:34`).
- Fake: `main.py:66` returns `{"status": "expired", "message": "The hold timer ran out. Ticket released!"}`, but `total_tickets` is never incremented back in storage, so expired holds never release inventory.

3 questions for the judges to ask this team in their Defence:
1. In `main.py:66`, the `/hold/{hold_id}` endpoint returns `"The hold timer ran out. Ticket released!"`, but Redis `total_tickets` is never incremented back. When an unpaid hold expires, what mechanism restores that seat to available inventory so other students can buy it?
2. In `docs/GAPS.txt` and `submission.txt`, you promised an AI-driven traffic sentinel generating a live bot probability score. In `main.py:34`, this is implemented as `if "bot" in x_user_agent.lower()`. Why was the AI integration omitted, and how would an AI model evaluate telemetry within a sub-50ms Tatkal rush window?
3. `docs/API.txt:10-15` specifies a `POST /api/tickets/checkout` endpoint to convert holds into purchased tickets with PostgreSQL persistence, but `main.py` omits this endpoint entirely. What is the complete lifecycle of a ticket from hold to payment, and how does `/checkin` verify that a scanned QR code was actually paid for?

The very last line, exactly:
SCORE core=10 kt=16 imp=10 docs=5 eng=4 total=45