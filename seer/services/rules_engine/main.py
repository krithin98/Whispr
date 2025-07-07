from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional, Union
import json
import asyncio

# Import our existing modules
import sys
import os
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.append(backend_path)

# Change working directory to backend so relative paths work
os.chdir(backend_path)

from database import log_event, get_db
from strategies import check_strategies, load_strategies, seed_test_strategies, safe_eval, create_strategy, get_strategy_by_id, update_strategy, delete_strategy, toggle_strategy
from llm import call_llm

app = FastAPI(title="Seer Strategies Engine", version="0.4.0")

@app.on_event("startup")
async def startup_event():
    """Seed test strategies on startup."""
    try:
        await seed_test_strategies()
        await log_event("startup", {"message": "Strategies engine started, test strategies seeded"})
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

class StrategySuggestion(BaseModel):
    strategy_id: int
    strategy_name: str

class EvaluationResponse(BaseModel):
    triggered_strategies: List[StrategySuggestion]
    evaluation_time_ms: float

# New CRUD models
class StrategyCreate(BaseModel):
    name: str
    strategy_expression: str
    prompt_tpl: str
    
    @validator('strategy_expression')
    def validate_strategy_expression(cls, v):
        """Validate that the strategy expression is safe and syntactically correct."""
        try:
            # Test with sample data to ensure it works
            sample_data = {"value": 100, "tick": 50, "volume": 1000}
            result = safe_eval(v, sample_data)
            # If we get here, the expression is valid
            return v
        except Exception as e:
            raise ValueError(f"Invalid strategy expression: {str(e)}")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate strategy name is not empty."""
        if not v.strip():
            raise ValueError("Strategy name cannot be empty")
        return v.strip()

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    strategy_expression: Optional[str] = None
    prompt_tpl: Optional[str] = None
    
    @validator('strategy_expression')
    def validate_strategy_expression(cls, v):
        """Validate strategy expression if provided."""
        if v is not None:
            try:
                sample_data = {"value": 100, "tick": 50, "volume": 1000}
                result = safe_eval(v, sample_data)
                return v
            except Exception as e:
                raise ValueError(f"Invalid strategy expression: {str(e)}")
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate strategy name if provided."""
        if v is not None and not v.strip():
            raise ValueError("Strategy name cannot be empty")
        return v.strip() if v else v

class StrategyToggle(BaseModel):
    is_active: bool

class StrategyResponse(BaseModel):
    id: int
    name: str
    strategy_expression: str
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
    return {"status": "healthy", "service": "strategies-engine", "version": "0.4.0"}

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_tick(request: EvaluationRequest):
    """
    Evaluate a tick against all active strategies.
    Returns triggered strategies and their suggestions.
    """
    import time
    start_time = time.time()
    
    try:
        # Convert tick data to dict for strategy evaluation
        tick_dict = request.tick_data.dict()
        
        # Log the incoming tick
        await log_event("tick", tick_dict)
        
        triggered_strategies = []
        
        # Get triggered strategies as a list
        triggered = await check_strategies(tick_dict)
        for strategy in triggered:
            try:
                # Format prompt template with tick data
                prompt = strategy["tpl"].format(**tick_dict)
                # For now, skip LLM call if no API key (we'll add this later)
                # llm_response = await call_llm([{"role": "user", "content": prompt}])
                # Create suggestion (placeholder for now)
                suggestion = f"Strategy '{strategy['name']}' triggered with prompt: {prompt}"
                strategy_suggestion = StrategySuggestion(
                    strategy_id=strategy["id"],
                    strategy_name=strategy["name"],
                )
                triggered_strategies.append(strategy_suggestion)
                # Log the strategy trigger
                await log_event("strategy_trigger", {
                    "strategy_id": strategy["id"],
                    "strategy_name": strategy["name"],
                })
            except Exception as e:
                # Log strategy evaluation errors
                await log_event("strategy_error", {
                    "strategy_id": strategy["id"],
                    "error": str(e)
                })
        evaluation_time = (time.time() - start_time) * 1000  # Convert to ms
        return EvaluationResponse(
            triggered_strategies=triggered_strategies,
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

@app.get("/strategies")
async def get_strategies():
    """Get all active strategies."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression, prompt_tpl, is_active FROM strategies ORDER BY id"
    )
    rows = await cursor.fetchall()
    return [{"id": r[0], "name": r[1], "strategy_expression": r[2], "prompt_tpl": r[3], "is_active": bool(r[4])} for r in rows]

@app.post("/strategies", response_model=StrategyResponse)
async def create_new_strategy(strategy: StrategyCreate):
    """Create a new strategy."""
    try:
        created_strategy = await create_strategy(strategy.name, strategy.strategy_expression, strategy.prompt_tpl)
        await log_event("strategy_created", {
            "strategy_id": created_strategy["id"],
            "strategy_name": created_strategy["name"],
            "strategy_expression": created_strategy["strategy_expression"]
        })
        return StrategyResponse(**created_strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await log_event("strategy_creation_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to create strategy: {str(e)}")

@app.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int):
    """Get a specific strategy by ID."""
    strategy = await get_strategy_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy with id {strategy_id} not found")
    return StrategyResponse(**strategy)

@app.put("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_existing_strategy(strategy_id: int, strategy_update: StrategyUpdate):
    """Update an existing strategy."""
    try:
        # Only pass non-None values to update_strategy
        update_data = {}
        if strategy_update.name is not None:
            update_data["name"] = strategy_update.name
        if strategy_update.strategy_expression is not None:
            update_data["strategy_expression"] = strategy_update.strategy_expression
        if strategy_update.prompt_tpl is not None:
            update_data["prompt_tpl"] = strategy_update.prompt_tpl
        
        if not update_data:
            # No changes requested
            strategy = await get_strategy_by_id(strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail=f"Strategy with id {strategy_id} not found")
            return StrategyResponse(**strategy)
        
        updated_strategy = await update_strategy(
            strategy_id,
            name=update_data.get("name"),
            strategy_expression=update_data.get("strategy_expression"),
            prompt_tpl=update_data.get("prompt_tpl")
        )
        
        await log_event("strategy_updated", {
            "strategy_id": strategy_id,
            "updated_fields": list(update_data.keys())
        })
        
        return StrategyResponse(**updated_strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await log_event("strategy_update_error", {"strategy_id": strategy_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to update strategy: {str(e)}")

@app.delete("/strategies/{strategy_id}")
async def delete_existing_strategy(strategy_id: int):
    """Delete a strategy."""
    try:
        deleted_strategy = await delete_strategy(strategy_id)
        await log_event("strategy_deleted", {
            "strategy_id": strategy_id,
            "strategy_name": deleted_strategy["name"]
        })
        return {
            "message": "Strategy deleted successfully",
            "deleted_strategy": StrategyResponse(**deleted_strategy)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log_event("strategy_deletion_error", {"strategy_id": strategy_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to delete strategy: {str(e)}")

@app.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
async def toggle_strategy_status(strategy_id: int, toggle: StrategyToggle):
    """Toggle a strategy's active status."""
    try:
        updated_strategy = await toggle_strategy(strategy_id, toggle.is_active)
        await log_event("strategy_toggled", {
            "strategy_id": strategy_id,
            "strategy_name": updated_strategy["name"],
            "is_active": updated_strategy["is_active"]
        })
        return StrategyResponse(**updated_strategy)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log_event("strategy_toggle_error", {"strategy_id": strategy_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to toggle strategy: {str(e)}")

@app.post("/test_expr", response_model=TestExprResponse)
async def test_expr(req: TestExprRequest):
    """Test a strategy expression with sample context data."""
    try:
        result = safe_eval(req.expr, req.context)
        return TestExprResponse(result=result)
    except Exception as e:
        return TestExprResponse(error=str(e)) 