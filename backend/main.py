import asyncio
import json
import os

from fastapi import FastAPI, WebSocket

from database import log_event, get_db
from llm import get_cost_comparison, call_llm
from rules import check_rules, seed_test_rules

# Load environment variables if python-dotenv is available
try:  # pragma: no cover - best effort
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


DATA_PROVIDER = os.getenv("DATA_PROVIDER", "simulated").lower()


class SimulatedProvider:
    """Simple tick generator used for testing."""

    def __init__(self):
        self.tick = 0

    async def connect(self) -> bool:  # pragma: no cover - trivial
        return True

    async def stream(self):
        while True:
            data = {"tick": self.tick, "value": 100 + self.tick}
            self.tick += 1
            yield data
            await asyncio.sleep(1)

    async def disconnect(self):  # pragma: no cover - trivial
        return True


class SchwabProvider(SimulatedProvider):
    """Placeholder for real Schwab integration."""

    pass


PROVIDERS = {
    "simulated": SimulatedProvider,
    "schwab": SchwabProvider,
}


def get_provider(name: str):
    provider_cls = PROVIDERS.get(name)
    if not provider_cls:
        raise ValueError(f"Unsupported DATA_PROVIDER: {name}")
    return provider_cls()


app = FastAPI(title="Whispr-MVP")


@app.on_event("startup")
async def startup_event():
    """Seed test rules and initialize data provider."""

    await seed_test_rules()
    app.state.provider = get_provider(DATA_PROVIDER)
    await app.state.provider.connect()


@app.on_event("shutdown")
async def shutdown_event():
    provider = getattr(app.state, "provider", None)
    if provider:
        await provider.disconnect()


@app.get("/")
async def root():
    return {"status": "OK", "message": "Whispr backend running"}


@app.websocket("/ws/ticks")
async def websocket_ticks(ws: WebSocket):
    await ws.accept()
    provider = app.state.provider
    async for tick_data in provider.stream():
        await log_event("tick", tick_data)
        await ws.send_json(tick_data)

        async for rule in check_rules(tick_data):
            try:
                prompt = rule["tpl"].format(**tick_data)

                llm_response = await call_llm([
                    {"role": "user", "content": prompt}
                ])

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

                await log_event("prompt", {
                    "rule_id": rule["id"],
                    "prompt": prompt,
                    "response": llm_response["content"],
                    "cost": llm_response["cost_estimate"],
                    "model": llm_response["model"]
                })

                await ws.send_json(suggestion_payload)

            except Exception as e:  # pragma: no cover - logging
                await log_event("rule_error", {
                    "rule_id": rule["id"],
                    "error": str(e)
                })


@app.get("/last_events")
async def last_events(limit: int = 5):
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT ts, event_type, payload FROM events ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    return [
        {"ts": r[0], "type": r[1], "payload": json.loads(r[2])}
        for r in rows
    ]


@app.get("/costs")
async def get_costs():
    """Get cost comparison for different LLM providers and models."""

    return get_cost_comparison()


@app.get("/rules")
async def get_rules():
    """Get all active rules."""

    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules ORDER BY id",
    )
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

