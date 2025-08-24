import os
import asyncio
import json
from fastapi import FastAPI, WebSocket

from database import log_event, get_db
from llm import get_cost_comparison, call_llm
from rules import check_rules, seed_test_rules
from data_providers import DataProvider, SimulatedProvider, SchwabProvider
from codezx_api import router as codezx_router

app = FastAPI(title="Whispr-MVP")
provider: DataProvider | None = None

# Include CodeZX agent API routes
app.include_router(codezx_router)

@app.on_event("startup")
async def startup_event() -> None:
    """Seed test rules and initialize the data provider."""
    await seed_test_rules()
    global provider
    name = os.getenv("DATA_PROVIDER", "simulated").lower()
    provider = SchwabProvider() if name == "schwab" else SimulatedProvider()
    await provider.connect()

@app.on_event("shutdown")
async def shutdown_event() -> None:
    if provider:
        await provider.disconnect()

@app.get("/")
async def root():
    return {"status": "OK", "message": "Whispr backend running"}

@app.websocket("/ws/ticks")
async def websocket_ticks(ws: WebSocket):
    await ws.accept()
    assert provider is not None
    async for tick_data in provider.subscribe():
        await log_event("tick", tick_data)
        await ws.send_json(tick_data)

        async for rule in check_rules(tick_data):
            try:
                prompt = rule["tpl"].format(**tick_data)
                llm_response = await call_llm(
                    [{"role": "user", "content": prompt}]
                )
                suggestion_payload = {
                    "type": "suggestion",
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "prompt": prompt,
                    "response": llm_response["content"],
                    "cost": llm_response["cost_estimate"],
                    "model": llm_response["model"],
                    "tick_data": tick_data,
                }
                await log_event(
                    "prompt",
                    {
                        "rule_id": rule["id"],
                        "prompt": prompt,
                        "response": llm_response["content"],
                        "cost": llm_response["cost_estimate"],
                        "model": llm_response["model"],
                    },
                )
                await ws.send_json(suggestion_payload)
            except Exception as e:
                await log_event(
                    "rule_error",
                    {
                        "rule_id": rule["id"],
                        "error": str(e),
                    },
                )

@app.get("/last_events")
async def last_events(limit: int = 5):
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT ts, event_type, payload FROM events ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return [{"ts": r[0], "type": r[1], "payload": json.loads(r[2])} for r in rows]

@app.get("/costs")
async def get_costs():
    """Get cost comparison for different LLM providers."""
    return get_cost_comparison()

@app.get("/rules")
async def get_rules():
    """Get all active rules."""
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules ORDER BY id",
    )
<<<<<<< Updated upstream
    return [{"id": r[0], "name": r[1], "trigger_expr": r[2], "prompt_tpl": r[3], "is_active": bool(r[4])} for r in rows] 
=======
    return [
        {
            "id": r[0],
            "name": r[1],
            "trigger_expr": r[2],
            "prompt_tpl": r[3],
            "is_active": bool(r[4]),
        }
        for r in rows
    ]

@app.post("/rules")
async def create_rule(name: str, trigger_expr: str, prompt_tpl: str):
    """Create a new rule."""
    from rules import add_rule
    await add_rule(name, trigger_expr, prompt_tpl)
    return {"status": "created"} 
>>>>>>> Stashed changes
