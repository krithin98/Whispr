#!/usr/bin/env python3
"""
CodeZX Router - Command Line Interface

Usage:
    python codex_router.py --task "Design a responsive navigation component"
    python codex_router.py --task "Fix the login bug" --mode developer
    python codex_router.py --test  # Run mode detection tests
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from codex_integration import process_codex_request, CodexModeDetector

async def route_task(task_description: str, preferred_mode: str = None) -> dict:
    """Route a task and return compiled prompt for Codex."""
    
    # Get mode detection
    result = await process_codex_request(task_description)
    detected_mode = result["mode_detection"]["detected_mode"]
    confidence = result["mode_detection"]["confidence"]
    reasoning = result["mode_detection"]["reasoning"]
    
    # Use preferred mode if specified and valid
    if preferred_mode and preferred_mode in ["architect", "developer", "qa", "devops", "uiux"]:
        final_mode = preferred_mode
        mode_override = True
    else:
        final_mode = detected_mode
        mode_override = False
    
    # Get mode-specific configuration
    detector = CodexModeDetector()
    mode_config = detector.get_mode_config(final_mode)
    
    # Compile the prompt for Codex
    compiled_prompt = f"""You are CodeZX-{final_mode.title()}, a specialized AI agent.

{mode_config['system_prompt']}

**Current Task**: {task_description}

**Mode**: {final_mode.title()} (detected: {detected_mode}, confidence: {confidence:.1%})
**Reasoning**: {reasoning}
{f"**Note**: Mode overridden to {preferred_mode}" if mode_override else ""}

**Knowledge Base**: {', '.join(mode_config['knowledge_files'])}
**Response Style**: {mode_config['response_style']}

**Constraints**:
- Tests-first approach for Developer/QA tasks
- Keep code changes under 150-200 LOC
- Respect project architecture and constraints
- One chat = one task (don't mix modes)

**Deliverables**:
{f"- **UI/UX**: Assumptions, wireframes, component specs, copy matrix, Dev Checklist" if final_mode == "uiux" else ""}
{f"- **Developer**: Tests first, then minimal implementation" if final_mode == "developer" else ""}
{f"- **Architect**: High-level design, patterns, scalability considerations" if final_mode == "architect" else ""}
{f"- **QA**: Test strategy, edge cases, quality metrics" if final_mode == "qa" else ""}
{f"- **DevOps**: Infrastructure, deployment, monitoring approach" if final_mode == "devops" else ""}

Please proceed with this task as CodeZX-{final_mode.title()}."""
    
    return {
        "task_description": task_description,
        "detected_mode": detected_mode,
        "final_mode": final_mode,
        "confidence": confidence,
        "reasoning": reasoning,
        "mode_override": mode_override,
        "compiled_prompt": compiled_prompt,
        "mode_config": {
            "system_prompt": mode_config["system_prompt"],
            "knowledge_files": mode_config["knowledge_files"],
            "response_style": mode_config["response_style"]
        }
    }

async def run_tests():
    """Run mode detection tests."""
    print("🧪 Running CodeZX Router Mode Detection Tests...")
    
    test_cases = [
        ("Design a responsive navigation component", "uiux"),
        ("Create wireframes for account settings", "uiux"),
        ("Fix the login bug in authentication", "developer"),
        ("Design database schema for user management", "architect"),
        ("Test API endpoints for security vulnerabilities", "qa"),
        ("Deploy application to production with monitoring", "devops")
    ]
    
    all_passed = True
    
    for task, expected_mode in test_cases:
        try:
            result = await route_task(task)
            detected = result["detected_mode"]
            if detected == expected_mode:
                print(f"✅ {task} → {detected}")
            else:
                print(f"❌ {task} → {detected} (expected {expected_mode})")
                all_passed = False
        except Exception as e:
            print(f"💥 {task} → Error: {e}")
            all_passed = False
    
    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed!")
        return 1

def main():
    parser = argparse.ArgumentParser(description="CodeZX Router - Route tasks to appropriate agents")
    parser.add_argument("--task", help="Task description to route")
    parser.add_argument("--mode", help="Preferred agent mode (architect, developer, qa, devops, uiux)")
    parser.add_argument("--test", action="store_true", help="Run mode detection tests")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    if args.test:
        return asyncio.run(run_tests())
    
    if not args.task:
        parser.print_help()
        return 1
    
    try:
        result = asyncio.run(route_task(args.task, args.mode))
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("🚀 CodeZX Router Result")
            print("=" * 40)
            print(f"Task: {result['task_description']}")
            print(f"Detected Mode: {result['detected_mode']}")
            print(f"Final Mode: {result['final_mode']}")
            print(f"Confidence: {result['confidence']:.1%}")
            print(f"Reasoning: {result['reasoning']}")
            if result['mode_override']:
                print(f"Note: Mode overridden to {args.mode}")
            print("\n📝 Compiled Prompt for Codex:")
            print("-" * 40)
            print(result['compiled_prompt'])
        
        return 0
        
    except Exception as e:
        print(f"💥 Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
