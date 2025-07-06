from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional, Union
import json
import asyncio

# Import our existing modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from database import log_event, get_db
from rules import check_rules, load_rules, seed_test_rules, safe_eval, create_rule, get_rule_by_id, update_rule, delete_rule, toggle_rule
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

# New CRUD models
class RuleCreate(BaseModel):
    name: str
    trigger_expr: str
    prompt_tpl: str
    
    @validator('trigger_expr')
    def validate_trigger_expr(cls, v):
        """Validate that the trigger expression is safe and syntactically correct."""
        try:
            # Test with sample data to ensure it works
            sample_data = {"value": 100, "tick": 50, "volume": 1000}
            result = safe_eval(v, sample_data)
            # If we get here, the expression is valid
            return v
        except Exception as e:
            raise ValueError(f"Invalid trigger expression: {str(e)}")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate rule name is not empty."""
        if not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip()

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_expr: Optional[str] = None
    prompt_tpl: Optional[str] = None
    
    @validator('trigger_expr')
    def validate_trigger_expr(cls, v):
        """Validate trigger expression if provided."""
        if v is not None:
            try:
                sample_data = {"value": 100, "tick": 50, "volume": 1000}
                result = safe_eval(v, sample_data)
                return v
            except Exception as e:
                raise ValueError(f"Invalid trigger expression: {str(e)}")
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate rule name if provided."""
        if v is not None and not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip() if v else v

class RuleToggle(BaseModel):
    is_active: bool

class RuleResponse(BaseModel):
    id: int
    name: str
    trigger_expr: str
    prompt_tpl: str
    is_active: bool

class TestExprRequest(BaseModel):
    expr: str
    context: Dict[str, Any]

class TestExprResponse(BaseModel):
    result: Union[bool, float, int, str, None] = None
    error: Optional[str] = None

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
    cursor = await conn.execute(
        "SELECT ts, event_type, payload FROM events ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [{"ts": r[0], "type": r[1], "payload": json.loads(r[2])} for r in rows]

@app.get("/rules")
async def get_rules():
    """Get all active rules."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules ORDER BY id"
    )
    rows = await cursor.fetchall()
    return [{"id": r[0], "name": r[1], "trigger_expr": r[2], "prompt_tpl": r[3], "is_active": bool(r[4])} for r in rows]

@app.post("/rules", response_model=RuleResponse)
async def create_new_rule(rule: RuleCreate):
    """Create a new rule."""
    try:
        created_rule = await create_rule(rule.name, rule.trigger_expr, rule.prompt_tpl)
        await log_event("rule_created", {
            "rule_id": created_rule["id"],
            "rule_name": created_rule["name"],
            "trigger_expr": created_rule["trigger_expr"]
        })
        return RuleResponse(**created_rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await log_event("rule_creation_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to create rule: {str(e)}")

@app.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: int):
    """Get a specific rule by ID."""
    rule = await get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule with id {rule_id} not found")
    return RuleResponse(**rule)

@app.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_existing_rule(rule_id: int, rule_update: RuleUpdate):
    """Update an existing rule."""
    try:
        # Only pass non-None values to update_rule
        update_data = {}
        if rule_update.name is not None:
            update_data["name"] = rule_update.name
        if rule_update.trigger_expr is not None:
            update_data["trigger_expr"] = rule_update.trigger_expr
        if rule_update.prompt_tpl is not None:
            update_data["prompt_tpl"] = rule_update.prompt_tpl
        
        if not update_data:
            # No changes requested
            rule = await get_rule_by_id(rule_id)
            if not rule:
                raise HTTPException(status_code=404, detail=f"Rule with id {rule_id} not found")
            return RuleResponse(**rule)
        
        updated_rule = await update_rule(
            rule_id,
            name=update_data.get("name"),
            trigger_expr=update_data.get("trigger_expr"),
            prompt_tpl=update_data.get("prompt_tpl")
        )
        
        await log_event("rule_updated", {
            "rule_id": rule_id,
            "updated_fields": list(update_data.keys())
        })
        
        return RuleResponse(**updated_rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await log_event("rule_update_error", {"rule_id": rule_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")

@app.delete("/rules/{rule_id}")
async def delete_existing_rule(rule_id: int):
    """Delete a rule."""
    try:
        deleted_rule = await delete_rule(rule_id)
        await log_event("rule_deleted", {
            "rule_id": rule_id,
            "rule_name": deleted_rule["name"]
        })
        return {
            "message": "Rule deleted successfully",
            "deleted_rule": RuleResponse(**deleted_rule)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log_event("rule_deletion_error", {"rule_id": rule_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")

@app.patch("/rules/{rule_id}", response_model=RuleResponse)
async def toggle_rule_status(rule_id: int, toggle: RuleToggle):
    """Toggle a rule's active status."""
    try:
        updated_rule = await toggle_rule(rule_id, toggle.is_active)
        await log_event("rule_toggled", {
            "rule_id": rule_id,
            "rule_name": updated_rule["name"],
            "is_active": updated_rule["is_active"]
        })
        return RuleResponse(**updated_rule)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log_event("rule_toggle_error", {"rule_id": rule_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to toggle rule: {str(e)}")

@app.post("/test_expr", response_model=TestExprResponse)
async def test_expr(req: TestExprRequest):
    """Test a rule expression with sample context data."""
    try:
        result = safe_eval(req.expr, req.context)
        return TestExprResponse(result=result)
    except Exception as e:
        return TestExprResponse(error=str(e)) 