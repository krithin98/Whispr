from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
import asyncio
import json
import httpx
import os
from datetime import datetime, timedelta
from database import log_event, get_db, log_strategy_trigger, get_strategy_triggers, update_trigger_outcome
from llm import get_cost_comparison
from data_feeds import get_data_feed, YFinanceFeed
from trade_logger import trade_logger, TradeSide
from indicators import gg_rule_generator
from atr_strategy import atr_strategy_generator
from vomy_strategy import VomyStrategyGenerator, VomyStrategyEvaluator
from four_h_po_dot_strategy import po_dot_strategy_generator
from conviction_arrow_strategy import conviction_arrow_strategy
from strategies import check_strategies, seed_test_strategies
from backtesting import backtesting_engine, BacktestResult
from indicator_service import get_indicator_service
from data_providers import get_provider

app = FastAPI(title="Seer UI Service", version="0.4.0")

# --- CORS Middleware ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:3001"] for more security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rules engine service URL
RULES_ENGINE_URL = "http://localhost:8001"

@app.on_event("startup")
async def startup_event():
    """Seed test strategies on startup."""
    await seed_test_strategies()

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
                
                # NEW: evaluate strategies
                async for strategy in check_strategies(tick_data):
                    try:
                        # Format the prompt template with tick data
                        prompt = strategy["prompt_tpl"].format(**tick_data)
                        
                        # Get LLM suggestion
                        suggestion_result = await get_llm_suggestion(prompt)
                        
                        # Send suggestion to client
                        suggestion_payload = {
                            "type": "suggestion",
                            "strategy_id": strategy["id"],
                            "strategy_name": strategy["name"],
                            "prompt": prompt,
                            "response": suggestion_result["response"],
                            "cost": suggestion_result["cost"],
                            "model": suggestion_result["model"],
                            "tick_data": tick_data
                        }
                        
                        await ws.send_json(suggestion_payload)
                        
                        # Log the strategy trigger
                        await log_event("strategy_trigger", {
                            "strategy_id": strategy["id"],
                            "strategy_name": strategy["name"],
                            "tick_data": tick_data,
                            "suggestion": suggestion_result
                        })
                        
                    except Exception as e:
                        await log_event("strategy_error", {
                            "strategy_id": strategy["id"],
                            "error": str(e),
                            "tick_data": tick_data
                        })
                
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
                        
                        # Send any triggered strategies as suggestions
                        for strategy_suggestion in evaluation_result["triggered_strategies"]:
                            suggestion_payload = {
                                "type": "suggestion",
                                "strategy_id": strategy_suggestion["strategy_id"],
                                "strategy_name": strategy_suggestion["strategy_name"],
                                "prompt": strategy_suggestion["prompt"],
                                "response": strategy_suggestion["suggestion"],
                                "cost": strategy_suggestion["cost"],
                                "model": strategy_suggestion["model"],
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

@app.get("/strategies")
async def get_strategies():
    """Proxy to rules engine strategies endpoint."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{RULES_ENGINE_URL}/strategies")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Failed to fetch strategies from rules engine"}
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

@app.post("/strategies/generate-golden-gate")
async def generate_golden_gate_strategies():
    """Generate Golden Gate strategies for all timeframes."""
    try:
        await gg_rule_generator.generate_golden_gate_rules()
        return {"status": "success", "message": "Golden Gate rules generated successfully"}
    except Exception as e:
        await log_event("error", {"message": f"Failed to generate Golden Gate rules: {str(e)}"})
        return {"status": "error", "message": f"Failed to generate rules: {str(e)}"}

@app.get("/strategies/golden-gate")
async def get_golden_gate_strategies():
    """Get all Golden Gate strategies."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, prompt_tpl, tags, priority, is_active FROM rules WHERE rule_type = 'golden_gate' ORDER BY priority DESC, name"
    )
    rules = await cursor.fetchall()
    return [dict(zip(("id", "name", "rule_expression", "prompt_tpl", "tags", "priority", "is_active"), rule)) for rule in rules]

@app.get("/indicators")
async def get_indicators():
    """Get all registered indicators."""
    conn = await get_db()
    cursor = await conn.execute("SELECT id, name, indicator_type, config, is_active FROM indicators")
    indicators = await cursor.fetchall()
    return [dict(zip(("id", "name", "indicator_type", "config", "is_active"), indicator)) for indicator in indicators]

@app.get("/analytics/golden-gate")
async def get_golden_gate_analytics():
    """Get Golden Gate analytics and completion statistics."""
    conn = await get_db()
    
    # Get recent GG events
    cursor = await conn.execute(
        """
        SELECT event_type, payload, ts FROM events 
        WHERE event_type IN ('golden_gate_trigger', 'golden_gate_complete', 'golden_gate_pending')
        ORDER BY ts DESC LIMIT 50
        """
    )
    events = await cursor.fetchall()
    
    # Parse events
    triggers = []
    completions = []
    pending = []
    
    for event_type, payload, timestamp in events:
        data = json.loads(payload)
        data['timestamp'] = timestamp
        
        if event_type == 'golden_gate_trigger':
            triggers.append(data)
        elif event_type == 'golden_gate_complete':
            completions.append(data)
        elif event_type == 'golden_gate_pending':
            pending.append(data)
    
    # Calculate completion rates
    completion_stats = {}
    if triggers:
        for trigger in triggers:
            timeframe = trigger.get('timeframe')
            side = trigger.get('side')
            time_slot = trigger.get('time_slot')
            
            if timeframe == 'day' and time_slot:
                key = f"{timeframe}_{side}_{time_slot}"
                if key not in completion_stats:
                    completion_stats[key] = {
                        'triggers': 0,
                        'completions': 0,
                        'pending': 0
                    }
                completion_stats[key]['triggers'] += 1
    
    # Count completions and pending
    for completion in completions:
        timeframe = completion.get('timeframe')
        side = completion.get('side')
        time_slot = completion.get('time_slot')
        
        if timeframe == 'day' and time_slot:
            key = f"{timeframe}_{side}_{time_slot}"
            if key in completion_stats:
                completion_stats[key]['completions'] += 1
    
    for pending_event in pending:
        timeframe = pending_event.get('timeframe')
        side = pending_event.get('side')
        time_slot = pending_event.get('time_slot')
        
        if timeframe == 'day' and time_slot:
            key = f"{timeframe}_{side}_{time_slot}"
            if key in completion_stats:
                completion_stats[key]['pending'] += 1
    
    return {
        "recent_triggers": triggers[:10],
        "recent_completions": completions[:10],
        "pending_triggers": pending[:10],
        "completion_statistics": completion_stats,
        "total_triggers": len(triggers),
        "total_completions": len(completions),
        "total_pending": len(pending)
    }

@app.get("/analytics/golden-gate/probabilities")
async def get_golden_gate_probabilities():
    """Get the Day GG completion probabilities."""
    try:
        with open("data/day_gg_probabilities.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Day GG probabilities not found"}

@app.post("/strategies/generate-atr")
async def generate_atr_strategies():
    """Generate ATR-based strategies for all timeframes."""
    try:
        total_rules = await atr_strategy_generator.generate_atr_rules()
        return {"status": "success", "message": f"Generated {total_rules} ATR rules successfully"}
    except Exception as e:
        await log_event("error", {"message": f"Failed to generate ATR rules: {str(e)}"})
        return {"status": "error", "message": f"Failed to generate rules: {str(e)}"}

@app.get("/strategies/atr")
async def get_atr_strategies():
    """Get all ATR-based strategies."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, prompt_tpl, tags, priority, is_active FROM rules WHERE rule_type = 'atr_based' ORDER BY priority DESC, name"
    )
    rules = await cursor.fetchall()
    return [dict(zip(("id", "name", "rule_expression", "prompt_tpl", "tags", "priority", "is_active"), rule)) for rule in rules]

@app.get("/strategies/atr/adjacent")
async def get_adjacent_atr_strategies():
    """Get adjacent (one-step) ATR strategies."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, prompt_tpl, tags, priority, is_active FROM rules WHERE rule_type = 'atr_based' AND tags LIKE '%atr_level%' ORDER BY priority DESC, name"
    )
    rules = await cursor.fetchall()
    return [dict(zip(("id", "name", "rule_expression", "prompt_tpl", "tags", "priority", "is_active"), rule)) for rule in rules]

@app.get("/strategies/atr/multi-level")
async def get_multi_level_atr_strategies():
    """Get multi-level (skip-a-step) ATR strategies."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, prompt_tpl, tags, priority, is_active FROM rules WHERE rule_type = 'atr_based' AND tags LIKE '%atr_multi%' ORDER BY priority DESC, name"
    )
    rules = await cursor.fetchall()
    return [dict(zip(("id", "name", "rule_expression", "prompt_tpl", "tags", "priority", "is_active"), rule)) for rule in rules]

@app.get("/analytics/atr")
async def get_atr_analytics():
    """Get ATR rule analytics and trigger statistics."""
    conn = await get_db()
    
    # Get recent ATR rule events
    cursor = await conn.execute(
        """
        SELECT event_type, payload, ts FROM events 
        WHERE event_type = 'atr_rule_trigger'
        ORDER BY ts DESC LIMIT 50
        """
    )
    events = await cursor.fetchall()
    
    # Parse events
    triggers = []
    for event_type, payload, timestamp in events:
        data = json.loads(payload)
        data['timestamp'] = timestamp
        triggers.append(data)
    
    # Calculate statistics by rule type and timeframe
    stats = {}
    for trigger in triggers:
        rule_type = trigger.get('rule_type', 'unknown')
        timeframe = trigger.get('timeframe', 'unknown')
        tag = trigger.get('tag', 'unknown')
        
        key = f"{timeframe}_{rule_type}_{tag}"
        if key not in stats:
            stats[key] = {
                'triggers': 0,
                'total_probability': 0,
                'timeframe': timeframe,
                'rule_type': rule_type,
                'tag': tag
            }
        
        stats[key]['triggers'] += 1
        stats[key]['total_probability'] += trigger.get('probability', 0)
    
    # Calculate average probabilities
    for key, data in stats.items():
        if data['triggers'] > 0:
            data['avg_probability'] = data['total_probability'] / data['triggers']
        else:
            data['avg_probability'] = 0
    
    return {
        "recent_triggers": triggers[:10],
        "statistics": stats,
        "total_triggers": len(triggers)
    }

# Vomy & iVomy Rule Endpoints
@app.post("/strategies/generate-vomy")
async def generate_vomy_strategies():
    """Generate Vomy and iVomy strategies for all supported candle timeframes."""
    try:
        generator = VomyStrategyGenerator()
        strategies = generator.generate_all_strategies()
        
        # Save strategies to database
        conn = await get_db()
        saved_count = 0
        
        for strategy in strategies:
            # Check if strategy already exists
            cursor = await conn.execute(
                "SELECT id FROM rules WHERE name = ? AND rule_type = 'vomy_ivomy'", 
                (strategy["name"],)
            )
            existing = await cursor.fetchall()
            
            if not existing:
                await conn.execute(
                    """
                    INSERT INTO rules (name, rule_expression, prompt_tpl, rule_type, tags, priority, is_active, indicator_ref, indicator_params)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        strategy["name"],
                        strategy["expression"],
                        f"Vomy/iVomy signal triggered: {{strategy_name}} on {{timeframe}} timeframe. EMA values: {{ema_values}}. Direction: {{direction}}",
                        "vomy_ivomy",
                        json.dumps(strategy["tags"]),
                        strategy["priority"],
                        strategy["enabled"],
                        "ema_crossover",
                        json.dumps({
                            "timeframe": strategy["timeframe"],
                            "ema_periods": strategy["ema_periods"],
                            "signal_type": strategy["signal_type"],
                            "direction": strategy["direction"]
                        })
                    )
                )
                saved_count += 1
        
        await log_event("info", {
            "message": f"Generated {len(strategies)} Vomy/iVomy strategies, saved {saved_count} new strategies"
        })
        
        return {
            "status": "success", 
            "message": f"Generated {len(strategies)} Vomy/iVomy strategies, saved {saved_count} new strategies",
            "total_strategies": len(strategies),
            "saved_strategies": saved_count
        }
        
    except Exception as e:
        await log_event("error", {"message": f"Failed to generate Vomy/iVomy strategies: {str(e)}"})
        return {"status": "error", "message": f"Failed to generate strategies: {str(e)}"}

@app.get("/strategies/vomy")
async def get_vomy_strategies():
    """Get all Vomy and iVomy strategies."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, prompt_tpl, tags, priority, is_active, indicator_params FROM rules WHERE rule_type = 'vomy_ivomy' ORDER BY priority DESC, name"
    )
    strategies = await cursor.fetchall()
    
    result = []
    for strategy in strategies:
        strategy_dict = dict(zip(("id", "name", "rule_expression", "prompt_tpl", "tags", "priority", "is_active", "indicator_params"), strategy))
        
        # Parse tags and indicator_params
        try:
            strategy_dict["tags"] = json.loads(strategy_dict["tags"]) if strategy_dict["tags"] else []
            strategy_dict["indicator_params"] = json.loads(strategy_dict["indicator_params"]) if strategy_dict["indicator_params"] else {}
        except:
            strategy_dict["tags"] = []
            strategy_dict["indicator_params"] = {}
        
        result.append(strategy_dict)
    
    return result

@app.get("/strategies/vomy/{timeframe}")
async def get_vomy_strategies_by_timeframe(timeframe: str):
    """Get Vomy and iVomy strategies for a specific timeframe."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, prompt_tpl, tags, priority, is_active, indicator_params FROM rules WHERE rule_type = 'vomy_ivomy' AND indicator_params LIKE ? ORDER BY priority DESC, name",
        (f'%"timeframe": "{timeframe}"%',)
    )
    strategies = await cursor.fetchall()
    
    result = []
    for strategy in strategies:
        strategy_dict = dict(zip(("id", "name", "rule_expression", "prompt_tpl", "tags", "priority", "is_active", "indicator_params"), strategy))
        
        # Parse tags and indicator_params
        try:
            strategy_dict["tags"] = json.loads(strategy_dict["tags"]) if strategy_dict["tags"] else []
            strategy_dict["indicator_params"] = json.loads(strategy_dict["indicator_params"]) if strategy_dict["indicator_params"] else {}
        except:
            strategy_dict["tags"] = []
            strategy_dict["indicator_params"] = {}
        
        result.append(strategy_dict)
    
    return result

@app.get("/strategies/vomy/type/{strategy_type}")
async def get_vomy_strategies_by_type(strategy_type: str):
    """Get Vomy or iVomy strategies by type (vomy or ivomy)."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, prompt_tpl, tags, priority, is_active, indicator_params FROM rules WHERE rule_type = 'vomy_ivomy' AND name LIKE ? ORDER BY priority DESC, name",
        (f"{strategy_type.capitalize()}%",)
    )
    strategies = await cursor.fetchall()
    
    result = []
    for strategy in strategies:
        strategy_dict = dict(zip(("id", "name", "rule_expression", "prompt_tpl", "tags", "priority", "is_active", "indicator_params"), strategy))
        
        # Parse tags and indicator_params
        try:
            strategy_dict["tags"] = json.loads(strategy_dict["tags"]) if strategy_dict["tags"] else []
            strategy_dict["indicator_params"] = json.loads(strategy_dict["indicator_params"]) if strategy_dict["indicator_params"] else {}
        except:
            strategy_dict["tags"] = []
            strategy_dict["indicator_params"] = {}
        
        result.append(strategy_dict)
    
    return result

@app.get("/analytics/vomy")
async def get_vomy_analytics():
    """Get Vomy and iVomy strategy analytics and trigger statistics."""
    conn = await get_db()
    
    # Get recent Vomy/iVomy strategy events
    cursor = await conn.execute(
        """
        SELECT event_type, payload, ts FROM events 
        WHERE event_type = 'vomy_strategy_trigger'
        ORDER BY ts DESC LIMIT 50
        """
    )
    events = await cursor.fetchall()
    
    # Parse events
    triggers = []
    for event_type, payload, timestamp in events:
        data = json.loads(payload)
        data['timestamp'] = timestamp
        triggers.append(data)
    
    # Calculate statistics by strategy type and timeframe
    stats = {}
    for trigger in triggers:
        strategy_type = trigger.get('strategy_type', 'unknown')
        timeframe = trigger.get('timeframe', 'unknown')
        direction = trigger.get('direction', 'unknown')
        
        key = f"{timeframe}_{strategy_type}_{direction}"
        if key not in stats:
            stats[key] = {
                'triggers': 0,
                'timeframe': timeframe,
                'strategy_type': strategy_type,
                'direction': direction,
                'last_trigger': None
            }
        
        stats[key]['triggers'] += 1
        stats[key]['last_trigger'] = trigger.get('triggered_at')
    
    return {
        "recent_triggers": triggers[:10],
        "statistics": stats,
        "total_triggers": len(triggers)
    }

@app.get("/vomy/specification")
async def get_vomy_specification():
    """Get the Vomy & iVomy strategy specification and configuration."""
    try:
        generator = VomyStrategyGenerator()
        return {
            "specification": generator.config,
            "supported_timeframes": generator.get_supported_timeframes(),
            "ema_periods": generator.get_ema_periods(),
            "statistics": generator.get_strategy_statistics()
        }
    except Exception as e:
        return {"error": f"Failed to load specification: {str(e)}"}

@app.get("/vomy/timeframes")
async def get_vomy_timeframes():
    """Get all supported candle timeframes for Vomy strategies."""
    try:
        generator = VomyStrategyGenerator()
        timeframes = generator.get_supported_timeframes()
        
        result = {}
        for tf in timeframes:
            metadata = generator.get_timeframe_metadata(tf)
            result[tf] = metadata
        
        return result
    except Exception as e:
        return {"error": f"Failed to load timeframes: {str(e)}"}

@app.post("/generate-po-dot-strategies")
async def generate_po_dot_strategies():
    """Generate 4H PO Dot strategies for SPX."""
    try:
        total_strategies = await po_dot_strategy_generator.generate_po_dot_strategies()
        return {"status": "success", "message": f"Generated {total_strategies} PO Dot strategies successfully"}
    except Exception as e:
        await log_event("po_dot_generation_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to generate PO Dot strategies: {str(e)}")

@app.get("/po-dot-statistics")
async def get_po_dot_statistics():
    """Get PO Dot strategy statistics and recent triggers."""
    try:
        stats = await po_dot_strategy_generator.get_po_dot_statistics()
        return stats
    except Exception as e:
        await log_event("po_dot_stats_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get PO Dot statistics: {str(e)}")

@app.post("/generate-conviction-arrow-strategies")
async def generate_conviction_arrow_strategies():
    """Generate Hourly Conviction Arrow strategies."""
    try:
        total_strategies = await conviction_arrow_strategy.generate_conviction_arrow_strategy()
        return {"status": "success", "message": f"Generated {total_strategies} Conviction Arrow strategies successfully"}
    except Exception as e:
        await log_event("conviction_arrow_generation_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to generate Conviction Arrow strategies: {str(e)}")

@app.get("/conviction-arrow-statistics")
async def get_conviction_arrow_statistics():
    """Get Conviction Arrow strategy statistics and recent triggers."""
    try:
        stats = await conviction_arrow_strategy.get_arrow_statistics()
        return stats
    except Exception as e:
        await log_event("conviction_arrow_stats_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get Conviction Arrow statistics: {str(e)}")

@app.get("/conviction-arrow-pending-evaluations")
async def get_pending_conviction_arrow_evaluations():
    """Get conviction arrows that need evaluation."""
    try:
        pending = await conviction_arrow_strategy.check_pending_evaluations()
        return {"pending_evaluations": pending}
    except Exception as e:
        await log_event("conviction_arrow_pending_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get pending evaluations: {str(e)}")

@app.post("/conviction-arrow-evaluate/{outcome_id}")
async def evaluate_conviction_arrow(outcome_id: int, success: bool, notes: str = None):
    """Record the outcome of a conviction arrow signal."""
    try:
        await conviction_arrow_strategy.record_arrow_outcome(outcome_id, success, notes)
        return {"status": "success", "message": f"Recorded {outcome_id} as {'success' if success else 'failure'}"}
    except Exception as e:
        await log_event("conviction_arrow_evaluation_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to record evaluation: {str(e)}")

# Strategy Triggers Endpoints
@app.get("/strategy-triggers")
async def get_strategy_triggers_endpoint(
    strategy_id: int = None,
    strategy_name: str = None,
    symbol: str = None,
    timeframe: str = None,
    trigger_type: str = None,
    side: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100
):
    """Get strategy triggers with optional filters."""
    try:
        triggers = await get_strategy_triggers(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            trigger_type=trigger_type,
            side=side,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return {
            "triggers": triggers,
            "count": len(triggers),
            "filters": {
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "symbol": symbol,
                "timeframe": timeframe,
                "trigger_type": trigger_type,
                "side": side,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        }
    except Exception as e:
        await log_event("strategy_triggers_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get strategy triggers: {str(e)}")

@app.get("/strategy-triggers/{trigger_id}")
async def get_strategy_trigger_by_id(trigger_id: int):
    """Get a specific strategy trigger by ID."""
    try:
        conn = await get_db()
        cursor = await conn.execute(
            "SELECT * FROM strategy_triggers WHERE id = ?",
            (trigger_id,)
        )
        trigger = await cursor.fetchone()
        
        if not trigger:
            raise HTTPException(status_code=404, detail="Strategy trigger not found")
        
        # Convert to dict
        columns = [description[0] for description in cursor.description]
        trigger_dict = dict(zip(columns, trigger))
        
        # Parse JSON fields
        try:
            trigger_dict["conditions_met"] = json.loads(trigger_dict["conditions_met"]) if trigger_dict["conditions_met"] else []
            trigger_dict["market_data"] = json.loads(trigger_dict["market_data"]) if trigger_dict["market_data"] else {}
        except:
            trigger_dict["conditions_met"] = []
            trigger_dict["market_data"] = {}
        
        return trigger_dict
    except HTTPException:
        raise
    except Exception as e:
        await log_event("strategy_trigger_error", {"error": str(e), "trigger_id": trigger_id})
        raise HTTPException(status_code=500, detail=f"Failed to get strategy trigger: {str(e)}")

@app.put("/strategy-triggers/{trigger_id}/outcome")
async def update_strategy_trigger_outcome(
    trigger_id: int,
    outcome: str,
    outcome_price: float = None,
    outcome_time: str = None
):
    """Update the outcome of a strategy trigger."""
    try:
        await update_trigger_outcome(trigger_id, outcome, outcome_price, outcome_time)
        return {"status": "success", "message": f"Updated trigger {trigger_id} outcome to {outcome}"}
    except Exception as e:
        await log_event("strategy_trigger_outcome_error", {"error": str(e), "trigger_id": trigger_id})
        raise HTTPException(status_code=500, detail=f"Failed to update trigger outcome: {str(e)}")

@app.get("/strategy-triggers/analytics/summary")
async def get_strategy_triggers_summary():
    """Get summary analytics for strategy triggers."""
    try:
        conn = await get_db()
        
        # Get total triggers
        cursor = await conn.execute("SELECT COUNT(*) FROM strategy_triggers")
        total_triggers = (await cursor.fetchone())[0]
        
        # Get triggers by strategy type
        cursor = await conn.execute("""
            SELECT strategy_type, COUNT(*) as count 
            FROM strategy_triggers 
            GROUP BY strategy_type
        """)
        by_strategy_type = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Get triggers by outcome
        cursor = await conn.execute("""
            SELECT outcome, COUNT(*) as count 
            FROM strategy_triggers 
            WHERE outcome IS NOT NULL
            GROUP BY outcome
        """)
        by_outcome = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Get recent triggers (last 24 hours)
        cursor = await conn.execute("""
            SELECT COUNT(*) FROM strategy_triggers 
            WHERE timestamp >= datetime('now', '-1 day')
        """)
        recent_triggers = (await cursor.fetchone())[0]
        
        return {
            "total_triggers": total_triggers,
            "recent_triggers_24h": recent_triggers,
            "by_strategy_type": by_strategy_type,
            "by_outcome": by_outcome
        }
    except Exception as e:
        await log_event("strategy_triggers_analytics_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

# Backtesting Endpoints
@app.post("/backtest/strategy")
async def backtest_single_strategy(
    strategy_id: int,
    symbol: str = "SPY",
    start_date: str = None,
    end_date: str = None
):
    """Run backtest for a single strategy."""
    try:
        # Set default dates if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Run backtest
        result = await backtesting_engine.backtest_strategy(strategy_id, symbol, start_date, end_date)
        
        # Convert to dict for JSON serialization
        result_dict = {
            "strategy_id": result.strategy_id,
            "strategy_name": result.strategy_name,
            "symbol": result.symbol,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "total_return": result.total_return,
            "total_pnl": result.total_pnl,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "avg_trade_duration": result.avg_trade_duration,
            "profit_factor": result.profit_factor,
            "trades": result.trades,
            "equity_curve": result.equity_curve
        }
        
        await log_event("backtest_completed", {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "total_return": result.total_return,
            "win_rate": result.win_rate
        })
        
        return result_dict
        
    except Exception as e:
        await log_event("backtest_error", {"error": str(e), "strategy_id": strategy_id})
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@app.post("/backtest/multiple")
async def backtest_multiple_strategies(
    strategy_ids: list[int],
    symbol: str = "SPY",
    start_date: str = None,
    end_date: str = None
):
    """Run backtests for multiple strategies."""
    try:
        # Set default dates if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Run backtests
        results = await backtesting_engine.backtest_multiple_strategies(strategy_ids, symbol, start_date, end_date)
        
        # Convert to dicts for JSON serialization
        results_dict = []
        for result in results:
            result_dict = {
                "strategy_id": result.strategy_id,
                "strategy_name": result.strategy_name,
                "symbol": result.symbol,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "win_rate": result.win_rate,
                "total_return": result.total_return,
                "total_pnl": result.total_pnl,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "avg_trade_duration": result.avg_trade_duration,
                "profit_factor": result.profit_factor,
                "trades": result.trades,
                "equity_curve": result.equity_curve
            }
            results_dict.append(result_dict)
        
        await log_event("backtest_multiple_completed", {
            "strategy_count": len(results),
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        })
        
        return {
            "results": results_dict,
            "summary": {
                "total_strategies": len(results),
                "avg_return": sum(r["total_return"] for r in results_dict) / len(results_dict) if results_dict else 0,
                "avg_win_rate": sum(r["win_rate"] for r in results_dict) / len(results_dict) if results_dict else 0,
                "best_strategy": max(results_dict, key=lambda x: x["total_return"]) if results_dict else None,
                "worst_strategy": min(results_dict, key=lambda x: x["total_return"]) if results_dict else None
            }
        }
        
    except Exception as e:
        await log_event("backtest_multiple_error", {"error": str(e), "strategy_ids": strategy_ids})
        raise HTTPException(status_code=500, detail=f"Multiple backtest failed: {str(e)}")

@app.get("/backtest/strategies")
async def get_backtestable_strategies():
    """Get list of strategies available for backtesting."""
    try:
        conn = await get_db()
        cursor = await conn.execute(
            "SELECT id, name, strategy_type, prompt_tpl FROM strategies WHERE is_active = 1"
        )
        strategies = await cursor.fetchall()
        
        return {
            "strategies": [
                {
                    "id": strategy[0],
                    "name": strategy[1],
                    "type": strategy[2],
                    "description": strategy[3] or "No description"
                }
                for strategy in strategies
            ]
        }
    except Exception as e:
        await log_event("backtest_strategies_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get strategies: {str(e)}")

@app.get("/market-data/spy")
async def get_spy_data():
    """Get real-time SPY data from yfinance."""
    try:
        # Create YFinanceFeed instance
        spy_feed = YFinanceFeed("SPY")
        
        # Get latest data
        tick_data = await spy_feed.get_latest_data()
        
        if tick_data:
            return {
                "success": True,
                "data": tick_data,
                "source": "yfinance",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Fallback to simulated data
            base_price = 450.0
            change = (datetime.utcnow().timestamp() % 100 - 50) * 0.1
            price = base_price + change
            
            fallback_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": "SPY",
                "price": round(price, 2),
                "volume": int(1000 + (datetime.utcnow().timestamp() % 1000) * 50),
                "bid": round(price - 0.01, 2),
                "ask": round(price + 0.01, 2),
                "change": round(change, 2),
                "change_percent": round((change / base_price) * 100, 3),
                "open": round(price - 0.05, 2),
                "high": round(price + 0.05, 2),
                "low": round(price - 0.05, 2),
                "tick_id": int(datetime.utcnow().timestamp() * 1000),
                "source": "simulated_fallback"
            }
            
            return {
                "success": False,
                "data": fallback_data,
                "source": "simulated_fallback",
                "message": "yfinance data unavailable, using simulated data",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        await log_event("market_data_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to fetch SPY data: {str(e)}")

@app.get("/market-data/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    start_date: str,
    end_date: str,
    interval: str = "1d"
):
    """Get historical data for a symbol using yfinance."""
    try:
        spy_feed = YFinanceFeed(symbol)
        data = await spy_feed.get_historical_data(start_date, end_date, interval)
        
        if data.empty:
            return {
                "success": False,
                "message": f"No historical data found for {symbol}",
                "data": []
            }
        
        return {
            "success": True,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "interval": interval,
            "data_points": len(data),
            "data": data.to_dict('records')
        }
        
    except Exception as e:
        await log_event("historical_data_error", {
            "symbol": symbol,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to fetch historical data: {str(e)}")

# New Indicator Endpoints
@app.get("/indicators/{symbol}")
async def get_symbol_indicators(symbol: str, timeframe: str = None):
    """Get all indicators for a symbol across all timeframes or a specific timeframe."""
    try:
        indicator_service = get_indicator_service()
        
        if timeframe:
            # Get indicators for specific timeframe
            data = await indicator_service.get_latest_indicators(symbol, timeframe)
            if data:
                return {"symbol": symbol, "timeframe": timeframe, "data": data}
            else:
                return {"error": f"No indicator data found for {symbol} on {timeframe}"}
        else:
            # Get indicators for all timeframes
            all_timeframes = indicator_service.timeframes + indicator_service.trading_timeframes
            results = {}
            
            for tf in all_timeframes:
                data = await indicator_service.get_latest_indicators(symbol, tf)
                if data:
                    results[tf] = data
            
            return {"symbol": symbol, "timeframes": results}
            
    except Exception as e:
        await log_event("get_indicators_error", {"error": str(e), "symbol": symbol})
        return {"error": f"Failed to get indicators: {str(e)}"}

@app.get("/indicators/{symbol}/atr")
async def get_atr_indicators(symbol: str, timeframe: str = "1d"):
    """Get ATR indicators for a symbol and timeframe."""
    try:
        indicator_service = get_indicator_service()
        data = await indicator_service.get_latest_indicators(symbol, timeframe)
        
        if data and "indicators" in data and "atr" in data["indicators"]:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "atr_data": data["indicators"]["atr"],
                "current_price": data.get("current_price")
            }
        else:
            return {"error": f"No ATR data found for {symbol} on {timeframe}"}
            
    except Exception as e:
        await log_event("get_atr_error", {"error": str(e), "symbol": symbol})
        return {"error": f"Failed to get ATR indicators: {str(e)}"}

@app.get("/indicators/{symbol}/pivot-ribbon")
async def get_pivot_ribbon(symbol: str, timeframe: str = "1d"):
    """Get pivot ribbon data for a symbol and timeframe."""
    try:
        indicator_service = get_indicator_service()
        data = await indicator_service.get_latest_indicators(symbol, timeframe)
        
        if data and "indicators" in data and "pivot_ribbon" in data["indicators"]:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "pivot_data": data["indicators"]["pivot_ribbon"],
                "current_price": data.get("current_price")
            }
        else:
            return {"error": f"No pivot ribbon data found for {symbol} on {timeframe}"}
            
    except Exception as e:
        await log_event("get_pivot_ribbon_error", {"error": str(e), "symbol": symbol})
        return {"error": f"Failed to get pivot ribbon: {str(e)}"}

@app.get("/indicators/{symbol}/support-resistance")
async def get_support_resistance(symbol: str, timeframe: str = "1d"):
    """Get support and resistance levels for a symbol and timeframe."""
    try:
        indicator_service = get_indicator_service()
        data = await indicator_service.get_latest_indicators(symbol, timeframe)
        
        if data and "indicators" in data and "support_resistance" in data["indicators"]:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "support_resistance": data["indicators"]["support_resistance"],
                "current_price": data.get("current_price")
            }
        else:
            return {"error": f"No support/resistance data found for {symbol} on {timeframe}"}
            
    except Exception as e:
        await log_event("get_support_resistance_error", {"error": str(e), "symbol": symbol})
        return {"error": f"Failed to get support/resistance: {str(e)}"}

@app.post("/indicators/calculate")
async def calculate_indicators(symbol: str = "SPY", background_tasks: BackgroundTasks = None):
    """Calculate indicators for a symbol (can run in background)."""
    try:
        indicator_service = get_indicator_service()
        
        if background_tasks:
            # Run in background
            background_tasks.add_task(indicator_service.calculate_all_indicators, symbol)
            return {"message": f"Started calculating indicators for {symbol} in background"}
        else:
            # Run immediately
            results = await indicator_service.calculate_all_indicators(symbol)
            return {"symbol": symbol, "results": results}
            
    except Exception as e:
        await log_event("calculate_indicators_error", {"error": str(e), "symbol": symbol})
        return {"error": f"Failed to calculate indicators: {str(e)}"}

@app.get("/indicators/status")
async def get_indicator_status():
    """Get status of indicator calculations."""
    try:
        indicator_service = get_indicator_service()
        cache_info = {
            "cached_indicators": len(indicator_service.indicator_cache),
            "cache_ttl_seconds": indicator_service.cache_ttl,
            "supported_timeframes": indicator_service.timeframes + indicator_service.trading_timeframes,
            "supported_symbols": indicator_service.symbols
        }
        return cache_info
        
    except Exception as e:
        await log_event("indicator_status_error", {"error": str(e)})
        return {"error": f"Failed to get indicator status: {str(e)}"} 