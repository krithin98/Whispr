from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio

# Import our existing modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from database import log_event, get_db
from rules import check_rules, load_rules, seed_test_rules
from llm import call_llm

app = FastAPI(title="Seer Rules Engine", version="0.4.0")

@app.on_event("startup")
async def startup_event():
    """Seed test rules on startup."""
    try:
        await seed_test_rules()
        await log_event("startup", {"message": "Rules engine started, test rules seeded"})
    except Exception as e:
        await log_event("startup_error", {"error": str(e)})

class TickData(BaseModel):
    tick: int
    value: float
    timestamp: Optional[str] = None
    extras: Optional[Dict[str, Any]] = None

class EvaluationRequest(BaseModel):
    tick_data: TickData
    strategy_id: Optional[int] = None  # For future multi-strategy support

class RuleSuggestion(BaseModel):
    rule_id: int
    rule_name: str
    prompt: str
    suggestion: str
    cost: Optional[float] = None
    model: Optional[str] = None

class EvaluationResponse(BaseModel):
    triggered_rules: List[RuleSuggestion]
    evaluation_time_ms: float

@app.get("/healthz")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "rules-engine", "version": "0.4.0"}

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_tick(request: EvaluationRequest):
    """
    Evaluate a tick against all active rules.
    Returns triggered rules and their suggestions.
    """
    import time
    start_time = time.time()
    
    try:
        # Convert tick data to dict for rule evaluation
        tick_dict = request.tick_data.dict()
        
        # Log the incoming tick
        await log_event("tick", tick_dict)
        
        triggered_rules = []
        
        # Get triggered rules as a list
        triggered = await check_rules(tick_dict)
        for rule in triggered:
            try:
                # Format prompt template with tick data
                prompt = rule["tpl"].format(**tick_dict)
                # For now, skip LLM call if no API key (we'll add this later)
                # llm_response = await call_llm([{"role": "user", "content": prompt}])
                # Create suggestion (placeholder for now)
                suggestion = f"Rule '{rule['name']}' triggered with prompt: {prompt}"
                rule_suggestion = RuleSuggestion(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    prompt=prompt,
                    suggestion=suggestion,
                    cost=0.0,  # Placeholder
                    model="placeholder"  # Placeholder
                )
                triggered_rules.append(rule_suggestion)
                # Log the rule trigger
                await log_event("rule_trigger", {
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "prompt": prompt,
                    "suggestion": suggestion,
                    "tick_data": tick_dict
                })
            except Exception as e:
                # Log rule evaluation errors
                await log_event("rule_error", {
                    "rule_id": rule["id"],
                    "error": str(e)
                })
        evaluation_time = (time.time() - start_time) * 1000  # Convert to ms
        return EvaluationResponse(
            triggered_rules=triggered_rules,
            evaluation_time_ms=round(evaluation_time, 2)
        )
    except Exception as e:
        await log_event("evaluation_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.get("/events")
async def get_events(limit: int = 10):
    """Get recent events for debugging."""
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT ts, event_type, payload FROM events ORDER BY id DESC LIMIT ?", (limit,)
    )
    return [{"ts": r[0], "type": r[1], "payload": json.loads(r[2])} for r in rows]

@app.get("/rules")
async def get_rules():
    """Get all active rules."""
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules ORDER BY id"
    )
    return [{"id": r[0], "name": r[1], "trigger_expr": r[2], "prompt_tpl": r[3], "is_active": bool(r[4])} for r in rows] 