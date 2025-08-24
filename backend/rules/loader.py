"""
Rules loader with JSON Schema validation.
"""
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
from jsonschema import validate, ValidationError

# Load the schema
SCHEMA_PATH = Path(__file__).parent / "schema" / "rules_v1.schema.json"

def load_schema() -> Dict[str, Any]:
    """Load the JSON schema for rule validation."""
    try:
        with open(SCHEMA_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON schema: {e}")

def validate_rule(rule_data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Validate a rule against the schema.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    try:
        validate(instance=rule_data, schema=schema)
    except ValidationError as e:
        errors.append(f"Validation error: {e.message}")
        if e.path:
            errors.append(f"  at path: {' -> '.join(str(p) for p in e.path)}")
    except Exception as e:
        errors.append(f"Unexpected error during validation: {e}")
    
    return errors

def load_rule_file(rule_path: Path) -> Dict[str, Any]:
    """Load and validate a single rule file."""
    try:
        with open(rule_path, 'r') as f:
            rule_data = yaml.safe_load(f)
        
        if not isinstance(rule_data, dict):
            raise ValueError("Rule file must contain a YAML object")
        
        # Validate against schema
        schema = load_schema()
        errors = validate_rule(rule_data, schema)
        
        if errors:
            raise ValueError(f"Rule validation failed:\n" + "\n".join(errors))
        
        return rule_data
        
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {rule_path}: {e}")
    except Exception as e:
        raise ValueError(f"Error loading rule from {rule_path}: {e}")

def load_rules_from_directory(rules_dir: Path) -> List[Dict[str, Any]]:
    """Load and validate all rule files from a directory."""
    rules = []
    
    if not rules_dir.exists():
        return rules
    
    for rule_file in rules_dir.glob("*.yaml"):
        try:
            rule_data = load_rule_file(rule_file)
            rule_data['_source_file'] = str(rule_file)
            rules.append(rule_data)
        except Exception as e:
            print(f"Warning: Could not load rule from {rule_file}: {e}")
    
    return rules

def get_rule_by_name(rules: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    """Get a specific rule by name."""
    for rule in rules:
        if rule.get('name') == name:
            return rule
    raise ValueError(f"Rule '{name}' not found")

# Example usage and testing
if __name__ == "__main__":
    # Test loading the example rule
    example_path = Path(__file__).parent / "examples" / "golden_gate_intraday.yaml"
    
    try:
        rule = load_rule_file(example_path)
        print(f"✅ Successfully loaded and validated rule: {rule['name']}")
        print(f"   Timeframe: {rule['inputs']['timeframe']}")
        print(f"   Indicators: {', '.join(rule['inputs']['indicators'])}")
        print(f"   Logic rules: {len(rule['logic'])}")
        
    except Exception as e:
        print(f"❌ Error loading example rule: {e}")

