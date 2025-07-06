import json
import ast
import operator as op
from database import get_db, log_event, log_strategy_trigger
from indicators import indicator_manager, gg_rule_generator
from atr_strategy import atr_strategy_generator
from vomy_strategy import VomyStrategyGenerator, VomyStrategyEvaluator
from four_h_po_dot_strategy import po_dot_strategy_generator
from conviction_arrow_strategy import conviction_arrow_strategy

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Name, ast.Load,
    ast.Compare, ast.BoolOp, ast.And, ast.Or, ast.Mod,
    ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Constant
)

_BIN_OPS = {
    ast.Add: op.add,   ast.Sub: op.sub,
    ast.Mult: op.mul,  ast.Div: op.truediv,
    ast.Mod: op.mod,
}

_CMP_OPS = {
    ast.Gt: op.gt,   ast.GtE: op.ge,
    ast.Lt: op.lt,   ast.LtE: op.le,
    ast.Eq: op.eq,   ast.NotEq: op.ne,
}

def _eval(node, ctx):
    if not isinstance(node, _ALLOWED_NODES):
        raise ValueError(f"Disallowed node {type(node).__name__}")
    if isinstance(node, ast.Num):          # Py <3.8
        return node.n
    if isinstance(node, ast.Constant):     # Py ≥3.8
        return node.value
    if isinstance(node, ast.Name):
        return ctx[node.id]
    if isinstance(node, ast.BinOp):
        return _BIN_OPS[type(node.op)](_eval(node.left, ctx), _eval(node.right, ctx))
    if isinstance(node, ast.UnaryOp):      # e.g., -value
        return -_eval(node.operand, ctx)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ctx)
        for op_, right_ in zip(node.ops, node.comparators):
            if not _CMP_OPS[type(op_)](left, _eval(right_, ctx)):
                return False
        return True
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, ctx) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    raise ValueError("Unhandled node")

def safe_eval(expr: str, ctx: dict):
    tree = ast.parse(expr, mode="eval")
    return _eval(tree.body, ctx)

async def load_strategies():
    """Load all active strategies from the database."""
    conn = await get_db()
    cursor = await conn.execute("SELECT id, name, strategy_expression, prompt_tpl, strategy_type, indicator_ref, indicator_params FROM strategies WHERE is_active=1")
    rows = await cursor.fetchall()
    return [dict(zip(("id", "name", "strategy_expression", "prompt_tpl", "strategy_type", "indicator_ref", "indicator_params"), r)) for r in rows]

async def check_strategies(tick):
    """Check if any strategies match the current tick data. Returns a list of triggered strategies."""
    strategies = await load_strategies()
    await log_event("debug", {"message": f"Loaded {len(strategies)} strategies"})
    triggered = []
    
    for strategy in strategies:
        strategy_type = strategy.get("strategy_type", "standard")
        triggered_strategy = None
        
        if strategy_type == "golden_gate":
            # Handle Golden Gate strategies
            result = await gg_rule_generator.evaluate_gg_strategy(
                strategy["id"], 
                tick.get("price", tick.get("value", 0)), 
                tick.get("symbol", "SPY")
            )
            if result.get("triggered", False):
                triggered_strategy = {
                    **strategy,
                    "evaluation_result": result
                }
        elif strategy_type == "atr_based":
            # Handle ATR-based strategies
            result = await atr_strategy_generator.evaluate_atr_strategy(
                strategy["id"],
                tick.get("price", tick.get("value", 0)),
                tick.get("symbol", "SPY")
            )
            if result.get("triggered", False):
                triggered_strategy = {
                    **strategy,
                    "evaluation_result": result
                }
        elif strategy_type == "vomy_ivomy":
            # Handle Vomy & iVomy strategies
            timeframe = strategy.get("timeframe", "1d")
            ema_values = tick.get("ema_values", {}).get(timeframe, {})
            
            if ema_values:
                vomy_evaluator = VomyStrategyEvaluator()
                vomy_evaluator.update_ema_values(timeframe, ema_values)
                result = vomy_evaluator.evaluate_strategies([strategy])
                
                if result:
                    triggered_strategy = {
                        **strategy,
                        "evaluation_result": result[0]
                    }
        elif strategy_type == "po_dot":
            # Handle PO Dot strategies
            result = await po_dot_strategy_generator.evaluate_po_dot_strategy(
                strategy["id"],
                tick
            )
            if result.get("triggered", False):
                triggered_strategy = {
                    **strategy,
                    "evaluation_result": result
                }
        elif strategy_type == "conviction_arrow":
            # Handle Conviction Arrow strategies
            result = await conviction_arrow_strategy.evaluate_conviction_arrow(
                strategy["id"],
                tick
            )
            if result.get("triggered", False):
                triggered_strategy = {
                    **strategy,
                    "evaluation_result": result
                }
        else:
            # Handle standard strategies with direct expressions
            await log_event("debug", {"message": f"Checking strategy '{strategy['name']}' with expr '{strategy['strategy_expression']}' against tick {tick}"})
            result = safe_eval(strategy["strategy_expression"], tick)
            await log_event("debug", {"message": f"Strategy '{strategy['name']}' evaluation result: {result}"})
            if result:
                await log_event("debug", {"message": f"Strategy '{strategy['name']}' triggered!"})
                triggered_strategy = strategy
        
        # Log strategy trigger if strategy fired
        if triggered_strategy:
            try:
                # Extract trigger details
                evaluation_result = triggered_strategy.get("evaluation_result", {})
                symbol = tick.get("symbol", "SPY")
                timeframe = evaluation_result.get("timeframe", "1d")
                trigger_type = evaluation_result.get("trigger_type", "signal")
                side = evaluation_result.get("side", evaluation_result.get("direction"))
                price = tick.get("price", tick.get("value", 0))
                confidence = evaluation_result.get("confidence", 0.8)
                conditions_met = evaluation_result.get("conditions_met", [strategy.get("strategy_expression", "Unknown")])
                market_data = {
                    "tick": tick,
                    "strategy_expression": strategy.get("strategy_expression"),
                    "evaluation_result": evaluation_result
                }
                
                # Log the strategy trigger
                await log_strategy_trigger(
                    strategy_id=strategy["id"],
                    strategy_name=strategy["name"],
                    strategy_type=strategy_type,
                    symbol=symbol,
                    timeframe=timeframe,
                    trigger_type=trigger_type,
                    side=side,
                    price=price,
                    confidence=confidence,
                    conditions_met=conditions_met,
                    market_data=market_data
                )
                
                triggered.append(triggered_strategy)
                
            except Exception as e:
                await log_event("strategy_trigger_log_error", {
                    "error": str(e),
                    "strategy_id": strategy["id"],
                    "strategy_name": strategy["name"]
                })
    
    return triggered

async def add_strategy(name: str, trigger_expr: str, prompt_tpl: str):
    """Add a new strategy to the database."""
    conn = await get_db()
    await conn.execute(
        "INSERT INTO strategies (name, strategy_expression, prompt_tpl) VALUES (?, ?, ?)",
        (name, trigger_expr, prompt_tpl)
    )

async def seed_test_strategies():
    """Add some test strategies to get started."""
    test_strategies = [
        ("High price ping", "value >= 105", "Price crossed {{value}}. Any risk-reducing actions?"),
        ("Low price alert", "value <= 95", "Price dropped to {{value}}. Consider buying opportunity?"),
        ("Tick milestone", "tick % 10 == 0", "Reached tick {{tick}} with value {{value}}. Market pattern analysis?")
    ]
    
    conn = await get_db()
    for name, expr, tpl in test_strategies:
        # Check if strategy already exists
        cursor = await conn.execute("SELECT id FROM strategies WHERE name = ?", (name,))
        existing = await cursor.fetchall()
        if not existing:
            await conn.execute(
                "INSERT INTO strategies (name, strategy_expression, prompt_tpl) VALUES (?, ?, ?)",
                (name, expr, tpl)
            )

async def create_strategy(name: str, trigger_expr: str, prompt_tpl: str):
    """Create a new strategy. Returns the created strategy."""
    conn = await get_db()
    
    # Check if strategy name already exists
    cursor = await conn.execute("SELECT id FROM strategies WHERE name = ?", (name,))
    existing = await cursor.fetchall()
    if existing:
        raise ValueError(f"Strategy with name '{name}' already exists")
    
    # Insert the new strategy
    cursor = await conn.execute(
        "INSERT INTO strategies (name, strategy_expression, prompt_tpl, is_active) VALUES (?, ?, ?, ?)",
        (name, trigger_expr, prompt_tpl, True)
    )
    
    # Get the created strategy
    strategy_id = cursor.lastrowid
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression, prompt_tpl, is_active FROM strategies WHERE id = ?",
        (strategy_id,)
    )
    strategy = await cursor.fetchone()
    
    return dict(zip(("id", "name", "strategy_expression", "prompt_tpl", "is_active"), strategy))

async def get_strategy_by_id(strategy_id: int):
    """Get a strategy by ID. Returns None if not found."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression, prompt_tpl, is_active FROM strategies WHERE id = ?",
        (strategy_id,)
    )
    strategy = await cursor.fetchone()
    
    if strategy:
        return dict(zip(("id", "name", "strategy_expression", "prompt_tpl", "is_active"), strategy))
    return None

async def update_strategy(strategy_id: int, name: str = None, trigger_expr: str = None, prompt_tpl: str = None):
    """Update a strategy. Returns the updated strategy."""
    conn = await get_db()
    
    # Check if strategy exists
    existing = await get_strategy_by_id(strategy_id)
    if not existing:
        raise ValueError(f"Strategy with id {strategy_id} not found")
    
    # Build update query dynamically
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
        
        # Check if new name conflicts with existing strategy
        cursor = await conn.execute(
            "SELECT id FROM strategies WHERE name = ? AND id != ?", (name, strategy_id)
        )
        name_conflict = await cursor.fetchall()
        if name_conflict:
            raise ValueError(f"Strategy with name '{name}' already exists")
    
    if trigger_expr is not None:
        updates.append("strategy_expression = ?")
        params.append(trigger_expr)
    
    if prompt_tpl is not None:
        updates.append("prompt_tpl = ?")
        params.append(prompt_tpl)
    
    if not updates:
        return existing  # No changes requested
    
    params.append(strategy_id)
    
    # Execute update
    query = f"UPDATE strategies SET {', '.join(updates)} WHERE id = ?"
    await conn.execute(query, params)
    
    # Return updated strategy
    return await get_strategy_by_id(strategy_id)

async def delete_strategy(strategy_id: int):
    """Delete a strategy. Returns True if successful."""
    conn = await get_db()
    
    # Check if strategy exists
    existing = await get_strategy_by_id(strategy_id)
    if not existing:
        raise ValueError(f"Strategy with id {strategy_id} not found")
    
    # Delete the strategy
    await conn.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
    return True

async def toggle_strategy(strategy_id: int, is_active: bool):
    """Toggle a strategy's active status. Returns the updated strategy."""
    conn = await get_db()
    
    # Check if strategy exists
    existing = await get_strategy_by_id(strategy_id)
    if not existing:
        raise ValueError(f"Strategy with id {strategy_id} not found")
    
    # Update active status
    await conn.execute(
        "UPDATE strategies SET is_active = ? WHERE id = ?",
        (is_active, strategy_id)
    )
    
    # Return updated strategy
    return await get_strategy_by_id(strategy_id) 