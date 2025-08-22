from fastapi import FastAPI, WebSocket
import asyncio
import json
from database import log_event, get_db
from llm import get_cost_comparison, call_llm
from rules import check_rules, seed_test_rules

app = FastAPI(title="Whispr-MVP")

@app.on_event("startup")
async def startup_event():
    """Seed test rules on startup."""
    await seed_test_rules()

@app.get("/")
async def root():
    return {"status": "OK", "message": "Whispr backend running"}

@app.websocket("/ws/ticks")
async def websocket_ticks(ws: WebSocket):
    await ws.accept()
    tick = 0
    while True:
        tick_data = {"tick": tick, "value": 100 + tick}
        await log_event("tick", tick_data)  # Log before broadcasting
        await ws.send_json(tick_data)

        # NEW: evaluate rules
        async for rule in check_rules(tick_data):
            try:
                # Format prompt template with tick data
                prompt = rule["tpl"].format(**tick_data)
                
                # Call LLM with the prompt
                llm_response = await call_llm([
                    {"role": "user", "content": prompt}
                ])
                
                # Create suggestion payload
                suggestion_payload = {
                    "type": "suggestion",
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "prompt": prompt,
                    "response": llm_response["content"],
                    "cost": llm_response["cost_estimate"],
                    "model": llm_response["model"],
                    "tick_data": tick_data
                }
                
                # Log the prompt event
                await log_event("prompt", {
                    "rule_id": rule["id"],
                    "prompt": prompt,
                    "response": llm_response["content"],
                    "cost": llm_response["cost_estimate"],
                    "model": llm_response["model"]
                })
                
                # Send suggestion over WebSocket
                await ws.send_json(suggestion_payload)
                
            except Exception as e:
                # Log any errors
                await log_event("rule_error", {
                    "rule_id": rule["id"],
                    "error": str(e)
                })
        
        await asyncio.sleep(1)        # 1-Hz simulated stream
        tick += 1

@app.get("/last_events")
async def last_events(limit: int = 5):
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT ts, event_type, payload FROM events ORDER BY id DESC LIMIT ?", (limit,)
    )
    return [{"ts": r[0], "type": r[1], "payload": json.loads(r[2])} for r in rows]

@app.get("/costs")
async def get_costs():
    """Get cost comparison for different LLM providers and models."""
    return get_cost_comparison()

@app.get("/rules")
async def get_rules():
    """Get all active rules."""
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules ORDER BY id"
    )
    return [{"id": r[0], "name": r[1], "trigger_expr": r[2], "prompt_tpl": r[3], "is_active": bool(r[4])} for r in rows] 
