from fastapi import FastAPI, WebSocket
import asyncio
import json
import httpx
import os
from database import log_event, get_db
from llm import get_cost_comparison
from data_feeds import get_data_feed
from trade_logger import trade_logger, TradeSide

app = FastAPI(title="Seer UI Service", version="0.4.0")

# Rules engine service URL
RULES_ENGINE_URL = "http://rules-engine:8001"

@app.get("/")
async def root():
    return {"status": "OK", "message": "Seer UI service running"}

@app.websocket("/ws/ticks")
async def websocket_ticks(ws: WebSocket):
    await ws.accept()
    
    # Get data feed configuration
    use_real_data = os.getenv("USE_REAL_DATA", "false").lower() == "true"
    symbol = os.getenv("TRADING_SYMBOL", "SPY")
    
    # Initialize data feed
    data_feed = get_data_feed(symbol=symbol, use_real_data=use_real_data)
    
    # Connect to data feed
    if not await data_feed.connect():
        await ws.send_json({"error": "Failed to connect to data feed"})
        return
    
    # HTTP client for calling rules engine
    async with httpx.AsyncClient() as client:
        try:
            async for tick_data in data_feed.stream():
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
                
        except Exception as e:
            await log_event("websocket_error", {"error": str(e)})
        finally:
            await data_feed.disconnect()

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

# Trade Management Endpoints
@app.post("/trades")
async def place_trade(symbol: str, side: str, quantity: int, price: float, order_type: str = "market"):
    """Place a simulated trade."""
    try:
        trade_side = TradeSide(side.lower())
        result = await trade_logger.place_order(symbol, trade_side, quantity, price, order_type)
        return result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        await log_event("trade_error", {"error": str(e)})
        return {"error": f"Failed to place trade: {str(e)}"}

@app.get("/trades/open")
async def get_open_trades():
    """Get all open trades."""
    return await trade_logger.get_open_trades()

@app.get("/trades/closed")
async def get_closed_trades(limit: int = 100):
    """Get recent closed trades."""
    return await trade_logger.get_closed_trades(limit)

@app.post("/trades/{trade_id}/close")
async def close_trade(trade_id: int, exit_price: float):
    """Close a simulated trade."""
    try:
        result = await trade_logger.close_trade(trade_id, exit_price)
        return result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        await log_event("trade_error", {"error": str(e)})
        return {"error": f"Failed to close trade: {str(e)}"}

@app.get("/trades/performance")
async def get_performance():
    """Get trading performance metrics."""
    return await trade_logger.get_performance_metrics() 