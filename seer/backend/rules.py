import json
import ast
import operator as op
from database import get_db, log_event

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

async def load_rules():
    """Load all active rules from the database."""
    conn = await get_db()
    cursor = await conn.execute("SELECT id, name, trigger_expr, prompt_tpl FROM rules WHERE is_active=1")
    rows = await cursor.fetchall()
    return [dict(zip(("id", "name", "expr", "tpl"), r)) for r in rows]

async def check_rules(tick):
    """Check if any rules match the current tick data. Returns a list of triggered rules."""
    rules = await load_rules()
    await log_event("debug", {"message": f"Loaded {len(rules)} rules"})
    triggered = []
    for rule in rules:
        await log_event("debug", {"message": f"Checking rule '{rule['name']}' with expr '{rule['expr']}' against tick {tick}"})
        result = safe_eval(rule["expr"], tick)
        await log_event("debug", {"message": f"Rule '{rule['name']}' evaluation result: {result}"})
        if result:
            await log_event("debug", {"message": f"Rule '{rule['name']}' triggered!"})
            triggered.append(rule)
    return triggered

async def add_rule(name: str, trigger_expr: str, prompt_tpl: str):
    """Add a new rule to the database."""
    conn = await get_db()
    await conn.execute(
        "INSERT INTO rules (name, trigger_expr, prompt_tpl) VALUES (?, ?, ?)",
        (name, trigger_expr, prompt_tpl)
    )

async def seed_test_rules():
    """Add some test rules to get started."""
    test_rules = [
        ("High price ping", "value >= 105", "Price crossed {{value}}. Any risk-reducing actions?"),
        ("Low price alert", "value <= 95", "Price dropped to {{value}}. Consider buying opportunity?"),
        ("Tick milestone", "tick % 10 == 0", "Reached tick {{tick}} with value {{value}}. Market pattern analysis?")
    ]
    
    conn = await get_db()
    for name, expr, tpl in test_rules:
        # Check if rule already exists
        cursor = await conn.execute("SELECT id FROM rules WHERE name = ?", (name,))
        existing = await cursor.fetchall()
        if not existing:
            await conn.execute(
                "INSERT INTO rules (name, trigger_expr, prompt_tpl) VALUES (?, ?, ?)",
                (name, expr, tpl)
            )

async def create_rule(name: str, trigger_expr: str, prompt_tpl: str):
    """Create a new rule. Returns the created rule."""
    conn = await get_db()
    
    # Check if rule name already exists
    cursor = await conn.execute("SELECT id FROM rules WHERE name = ?", (name,))
    existing = await cursor.fetchall()
    if existing:
        raise ValueError(f"Rule with name '{name}' already exists")
    
    # Insert the new rule
    cursor = await conn.execute(
        "INSERT INTO rules (name, trigger_expr, prompt_tpl, is_active) VALUES (?, ?, ?, ?)",
        (name, trigger_expr, prompt_tpl, True)
    )
    
    # Get the created rule
    rule_id = cursor.lastrowid
    cursor = await conn.execute(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules WHERE id = ?",
        (rule_id,)
    )
    rule = await cursor.fetchone()
    
    return dict(zip(("id", "name", "trigger_expr", "prompt_tpl", "is_active"), rule))

async def get_rule_by_id(rule_id: int):
    """Get a rule by ID. Returns None if not found."""
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules WHERE id = ?",
        (rule_id,)
    )
    rule = await cursor.fetchone()
    
    if rule:
        return dict(zip(("id", "name", "trigger_expr", "prompt_tpl", "is_active"), rule))
    return None

async def update_rule(rule_id: int, name: str = None, trigger_expr: str = None, prompt_tpl: str = None):
    """Update a rule. Returns the updated rule."""
    conn = await get_db()
    
    # Check if rule exists
    existing = await get_rule_by_id(rule_id)
    if not existing:
        raise ValueError(f"Rule with id {rule_id} not found")
    
    # Build update query dynamically
    updates = []
    params = []
    
    if name is not None:
        # Check if new name conflicts with existing rule
        cursor = await conn.execute(
            "SELECT id FROM rules WHERE name = ? AND id != ?", (name, rule_id)
        )
        name_conflict = await cursor.fetchall()
        if name_conflict:
            raise ValueError(f"Rule with name '{name}' already exists")
        updates.append("name = ?")
        params.append(name)
    
    if trigger_expr is not None:
        updates.append("trigger_expr = ?")
        params.append(trigger_expr)
    
    if prompt_tpl is not None:
        updates.append("prompt_tpl = ?")
        params.append(prompt_tpl)
    
    if not updates:
        return existing  # No changes
    
    # Execute update
    params.append(rule_id)
    await conn.execute(
        f"UPDATE rules SET {', '.join(updates)} WHERE id = ?",
        params
    )
    
    # Return updated rule
    return await get_rule_by_id(rule_id)

async def delete_rule(rule_id: int):
    """Delete a rule. Returns the deleted rule."""
    conn = await get_db()
    
    # Get the rule before deleting
    rule = await get_rule_by_id(rule_id)
    if not rule:
        raise ValueError(f"Rule with id {rule_id} not found")
    
    # Delete the rule
    await conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
    
    return rule

async def toggle_rule(rule_id: int, is_active: bool):
    """Toggle a rule's active status. Returns the updated rule."""
    conn = await get_db()
    
    # Check if rule exists
    existing = await get_rule_by_id(rule_id)
    if not existing:
        raise ValueError(f"Rule with id {rule_id} not found")
    
    # Update the status
    await conn.execute(
        "UPDATE rules SET is_active = ? WHERE id = ?",
        (is_active, rule_id)
    )
    
    # Return updated rule
    return await get_rule_by_id(rule_id) 