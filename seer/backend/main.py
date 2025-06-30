from fastapi import FastAPI, WebSocket
import asyncio
import json
import httpx
from database import log_event, get_db
from llm import get_cost_comparison

app = FastAPI(title="Seer UI Service", version="0.4.0")

# Rules engine service URL
RULES_ENGINE_URL = "http://rules-engine:8001"

@app.get("/")
async def root():
    return {"status": "OK", "message": "Seer UI service running"}

@app.websocket("/ws/ticks")
async def websocket_ticks(ws: WebSocket):
    await ws.accept()
    tick = 0
    
    # HTTP client for calling rules engine
    async with httpx.AsyncClient() as client:
        while True:
            tick_data = {"tick": tick, "value": 100 + tick}
            
            # Send tick to WebSocket client
            await ws.send_json(tick_data)
            
            # Call rules engine to evaluate the tick
            try:
                evaluation_request = {
                    "tick_data": tick_data,
                    "strategy_id": None
                }
                
                response = await client.post(
                    f"{RULES_ENGINE_URL}/evaluate",
                    json=evaluation_request,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    evaluation_result = response.json()
                    
                    # Send any triggered rules as suggestions
                    for rule_suggestion in evaluation_result["triggered_rules"]:
                        suggestion_payload = {
                            "type": "suggestion",
                            "rule_id": rule_suggestion["rule_id"],
                            "rule_name": rule_suggestion["rule_name"],
                            "prompt": rule_suggestion["prompt"],
                            "response": rule_suggestion["suggestion"],
                            "cost": rule_suggestion["cost"],
                            "model": rule_suggestion["model"],
                            "tick_data": tick_data,
                            "evaluation_time_ms": evaluation_result["evaluation_time_ms"]
                        }
                        
                        await ws.send_json(suggestion_payload)
                
            except Exception as e:
                # Log errors but don't break the tick stream
                await log_event("ui_error", {
                    "error": f"Rules engine call failed: {str(e)}",
                    "tick_data": tick_data
                })
            
            await asyncio.sleep(1)  # 1-Hz simulated stream
            tick += 1

@app.get("/last_events")
async def last_events(limit: int = 5):
    """Proxy to rules engine events endpoint."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{RULES_ENGINE_URL}/events?limit={limit}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Failed to fetch events from rules engine"}
        except Exception as e:
            return {"error": f"Rules engine connection failed: {str(e)}"}

@app.get("/costs")
async def get_costs():
    """Get cost comparison for different LLM providers and models."""
    return get_cost_comparison()

@app.get("/rules")
async def get_rules():
    """Proxy to rules engine rules endpoint."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{RULES_ENGINE_URL}/rules")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Failed to fetch rules from rules engine"}
        except Exception as e:
            return {"error": f"Rules engine connection failed: {str(e)}"} 