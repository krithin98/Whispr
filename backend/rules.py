import json
import ast
import operator
from database import get_db

SAFE_OPS = {
    ast.Gt: operator.gt,
    ast.Lt: operator.lt,
    ast.GtE: operator.ge,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
}

def _safe_eval(expr, context):
    """
    A very small and safe evaluator: supports comparisons like value > 105.
    """
    try:
        tree = ast.parse(expr, mode="eval").body  # type: ast.AST
        if isinstance(tree, ast.Compare):
            left = _safe_eval(ast.unparse(tree.left), context)
            right = _safe_eval(ast.unparse(tree.comparators[0]), context)
            op = SAFE_OPS[type(tree.ops[0])]
            return op(left, right)
        if isinstance(tree, ast.Name):
            return context.get(tree.id)
        if isinstance(tree, ast.Constant):
            return tree.value
        if isinstance(tree, ast.BinOp) and isinstance(tree.op, ast.Mod):
            left = _safe_eval(ast.unparse(tree.left), context)
            right = _safe_eval(ast.unparse(tree.right), context)
            return left % right
        return False
    except Exception:
        return False

async def load_rules():
    """Load all active rules from the database."""
    conn = await get_db()
    rows = await conn.execute_fetchall("SELECT id, name, trigger_expr, prompt_tpl FROM rules WHERE is_active=1")
    return [dict(zip(("id", "name", "expr", "tpl"), r)) for r in rows]

async def check_rules(tick):
    """Check if any rules match the current tick data."""
    for rule in await load_rules():
        if _safe_eval(rule["expr"], tick):
            yield rule

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
        existing = await conn.execute_fetchall(
            "SELECT id FROM rules WHERE name = ?", (name,)
        )
        if not existing:
            await conn.execute(
                "INSERT INTO rules (name, trigger_expr, prompt_tpl) VALUES (?, ?, ?)",
                (name, expr, tpl)
            ) 