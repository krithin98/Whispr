from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket

from database import get_db, log_event
from llm import call_llm, get_cost_comparison
from models import Rule, Strategy
from rules import check_rules, load_rules, seed_test_rules
from strategies import check_strategies, load_strategies


app = FastAPI(title="Whispr-MVP")


@app.on_event("startup")
async def startup_event() -> None:
    """Seed test rules on startup."""
    await seed_test_rules()


@app.get("/")
async def root() -> dict:
    return {"status": "OK", "message": "Whispr backend running"}


@app.websocket("/ws/ticks")
async def websocket_ticks(ws: WebSocket) -> None:
    await ws.accept()
    tick = 0
    while True:
        tick_data = {"tick": tick, "value": 100 + tick}
        await log_event("tick", tick_data)
        await ws.send_json(tick_data)

        # Evaluate basic rules
        async for rule in check_rules(tick_data):
            try:
                prompt = rule.prompt_tpl.format(**tick_data)
                llm_response = await call_llm([
                    {"role": "user", "content": prompt}
                ])

                suggestion_payload = {
                    "type": "suggestion",
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "prompt": prompt,
                    "response": llm_response["content"],
                    "cost": llm_response["cost_estimate"],
                    "model": llm_response["model"],
                    "tick_data": tick_data,
                }

                await log_event("prompt", {
                    "rule_id": rule.id,
                    "prompt": prompt,
                    "response": llm_response["content"],
                    "cost": llm_response["cost_estimate"],
                    "model": llm_response["model"],
                })

                await ws.send_json(suggestion_payload)

            except Exception as e:  # pragma: no cover - logging only
                await log_event("rule_error", {"rule_id": rule.id, "error": str(e)})

        # Evaluate complex strategies (placeholder)
        async for strat in check_strategies(tick_data):
            await log_event(
                "strategy_trigger",
                {"strategy_id": strat.id, "name": strat.name},
            )

        await asyncio.sleep(1)
        tick += 1


@app.get("/last_events")
async def last_events(limit: int = 5) -> list:
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT ts, event_type, payload FROM events ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return [
        {"ts": r[0], "type": r[1], "payload": json.loads(r[2])}
        for r in rows
    ]


@app.get("/costs")
async def get_costs() -> dict:
    """Get cost comparison for different LLM providers and models."""
    return get_cost_comparison()


@app.get("/rules", response_model=list[Rule])
async def get_rules() -> list[Rule]:
    """Get all active rules."""
    return await load_rules()


@app.get("/strategies", response_model=list[Strategy])
async def get_strategies() -> list[Strategy]:
    """Get all active strategies."""
    return await load_strategies()

