"""
Test router accuracy against the evaluation set.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from codex_integration import process_codex_request

# Evaluation set from tests/evals/README.md
EVALUATION_SET = {
    "uiux": [
        "Design a responsive navigation component",
        "Create wireframes for account settings",
        "Design a user interface for the trading dashboard",
        "Create a design system for the application",
        "Design an accessible form component",
        "Create user flows for the onboarding process",
        "Design a modal component for confirmations",
        "Create a mobile-first design approach",
        "Design a data visualization component",
        "Create a user research plan",
        "Design a notification system",
        "Create a design token library",
        "Design a responsive grid layout"
    ],
    "developer": [
        "Fix the login bug in authentication",
        "Implement user registration endpoint",
        "Add input validation to the API",
        "Refactor the database connection code",
        "Optimize the database query performance",
        "Add error handling to the service layer",
        "Implement caching for expensive operations",
        "Fix the memory leak in the worker",
        "Add unit tests for the utility functions",
        "Refactor the legacy code structure",
        "Implement the new feature request"
    ],
    "architect": [
        "Design database schema for user management",
        "Plan the microservices architecture",
        "Design the API gateway structure",
        "Plan the data migration strategy",
        "Design the caching layer architecture",
        "Plan the scaling strategy for high load",
        "Design the security architecture",
        "Plan the monitoring and observability",
        "Design the deployment pipeline",
        "Plan the disaster recovery strategy",
        "Design the data backup strategy",
        "Plan the performance optimization approach"
    ],
    "qa": [
        "Test API endpoints for security vulnerabilities",
        "Create test plan for user registration",
        "Perform load testing on the API",
        "Test the error handling scenarios",
        "Validate the data integrity checks",
        "Test the authentication flow",
        "Perform accessibility testing",
        "Test the mobile responsiveness",
        "Validate the API response formats",
        "Test the database transaction rollback",
        "Perform cross-browser testing",
        "Test the performance under stress"
    ],
    "devops": [
        "Deploy application to production with monitoring",
        "Set up CI/CD pipeline for the project",
        "Configure monitoring and alerting",
        "Set up load balancing for high availability",
        "Configure backup and disaster recovery",
        "Set up container orchestration",
        "Configure security scanning in CI/CD",
        "Set up logging aggregation",
        "Configure auto-scaling policies",
        "Set up infrastructure as code",
        "Configure network security policies",
        "Set up performance monitoring"
    ]
}

async def test_router_accuracy():
    """Test router accuracy against the full evaluation set."""
    print("\n🧪 Testing Router Accuracy Against Evaluation Set")
    print("=" * 60)
    
    # Track results
    confusion_matrix = {mode: {predicted: 0 for predicted in EVALUATION_SET.keys()} for mode in EVALUATION_SET.keys()}
    total_correct = 0
    total_tests = 0
    
    # Test each mode
    for expected_mode, tasks in EVALUATION_SET.items():
        print(f"\n📋 Testing {expected_mode.upper()} tasks ({len(tasks)} items):")
        
        for i, task in enumerate(tasks, 1):
            try:
                result = await process_codex_request(task)
                predicted_mode = result["mode_detection"]["detected_mode"]
                confidence = result["mode_detection"]["confidence"]
                
                # Update confusion matrix
                confusion_matrix[expected_mode][predicted_mode] += 1
                
                # Check if correct
                is_correct = predicted_mode == expected_mode
                if is_correct:
                    total_correct += 1
                    status = "✅"
                else:
                    status = "❌"
                
                total_tests += 1
                
                print(f"  {status} {i:2d}. {task[:50]}{'...' if len(task) > 50 else ''}")
                print(f"       → {predicted_mode} ({confidence:.1%}) {'✓' if is_correct else '✗'}")
                
            except Exception as e:
                print(f"  ❌ {i:2d}. Error processing task: {e}")
                total_tests += 1
    
    # Calculate accuracy
    accuracy = (total_correct / total_tests) * 100 if total_tests > 0 else 0
    
    # Print confusion matrix
    print(f"\n📊 Confusion Matrix (Accuracy: {accuracy:.1f}%)")
    print("=" * 60)
    
    # Header
    header = "Actual\\Predicted"
    for mode in EVALUATION_SET.keys():
        header += f"  {mode:>6}"
    print(header)
    print("-" * len(header))
    
    # Matrix rows
    for actual_mode in EVALUATION_SET.keys():
        row = f"{actual_mode:>12}"
        for predicted_mode in EVALUATION_SET.keys():
            count = confusion_matrix[actual_mode][predicted_mode]
            row += f"  {count:>6}"
        print(row)
    
    # Per-class accuracy
    print(f"\n📈 Per-Class Accuracy:")
    for mode in EVALUATION_SET.keys():
        correct = confusion_matrix[mode][mode]
        total = sum(confusion_matrix[mode].values())
        class_accuracy = (correct / total) * 100 if total > 0 else 0
        print(f"  {mode:>8}: {class_accuracy:5.1f}% ({correct:2d}/{total:2d})")
    
    # Summary
    print(f"\n🎯 Summary:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Correct: {total_correct}")
    print(f"  Overall Accuracy: {accuracy:.1f}%")
    
    # Assert minimum accuracy threshold
    assert accuracy >= 90.0, f"Router accuracy {accuracy:.1f}% below threshold of 90%"
    
    print(f"\n✅ Router accuracy test passed! ({accuracy:.1f}%)")

if __name__ == "__main__":
    asyncio.run(test_router_accuracy())
