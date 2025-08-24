#!/usr/bin/env python3
"""
Codex Integration Test

This script demonstrates how Codex integrates with our agent system.
Run with: python test_codex_integration.py
"""

import asyncio
import json
from codex_integration import process_codex_request, create_codex_configs, get_codex_stats

async def test_codex_workflow():
    """Test the complete Codex workflow."""
    print("🚀 Testing Codex Integration Workflow")
    print("=" * 60)
    
    # Test different types of requests
    test_requests = [
        {
            "input": "Design a new database schema for user management with role-based access control",
            "expected_mode": "architect",
            "description": "Architecture/Design Request"
        },
        {
            "input": "Fix the bug where users can't log in after password reset",
            "expected_mode": "developer", 
            "description": "Bug Fix Request"
        },
        {
            "input": "Test the API endpoints for performance and security vulnerabilities",
            "expected_mode": "qa",
            "description": "Testing Request"
        },
        {
            "input": "Deploy the new trading strategy to production with zero downtime",
            "expected_mode": "devops",
            "description": "Deployment Request"
        },
        {
            "input": "Write a function to calculate Fibonacci numbers",
            "expected_mode": "developer",
            "description": "General Coding Request"
        }
    ]
    
    print("🧪 Testing Mode Detection:")
    print("-" * 40)
    
    for i, test in enumerate(test_requests, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Input: {test['input']}")
        print(f"   Expected Mode: {test['expected_mode']}")
        
        # Process the request
        result = await process_codex_request(test['input'])
        
        # Show results
        detected_mode = result['mode_detection']['detected_mode']
        confidence = result['mode_detection']['confidence']
        reasoning = result['mode_detection']['reasoning']
        
        print(f"   Detected Mode: {detected_mode}")
        print(f"   Confidence: {confidence:.1%}")
        print(f"   Reasoning: {reasoning}")
        
        # Check if detection was correct
        if detected_mode == test['expected_mode']:
            print(f"   ✅ CORRECT - Mode detected successfully!")
        else:
            print(f"   ❌ INCORRECT - Expected {test['expected_mode']}, got {detected_mode}")
        
        # Show Codex instructions
        codex_instructions = result['codex_instructions']
        print(f"   Codex Mode: {codex_instructions['mode']}")
        print(f"   Knowledge Files: {', '.join(codex_instructions['knowledge_files'])}")
    
    # Create configuration files
    print(f"\n📁 Creating Codex Configuration Files:")
    print("-" * 40)
    config_files = create_codex_configs()
    
    for config_file in config_files:
        print(f"   ✅ {config_file}")
    
    # Show statistics
    print(f"\n📊 Codex Integration Statistics:")
    print("-" * 40)
    stats = get_codex_stats()
    
    print(f"   Total Interactions: {stats['total_interactions']}")
    print(f"   Mode Distribution:")
    for mode, count in stats['mode_distribution'].items():
        percentage = stats['mode_percentages'].get(mode, 0)
        print(f"     {mode}: {count} ({percentage:.1f}%)")
    
    print(f"\n🎯 Key Benefits of This Integration:")
    print("-" * 40)
    print("1. **Automatic Mode Detection**: Codex automatically switches to the right mode")
    print("2. **Specialized Knowledge**: Each mode has access to relevant knowledge files")
    print("3. **Consistent Responses**: Responses are tailored to the specific mode")
    print("4. **Learning & Improvement**: System tracks interactions and improves over time")
    print("5. **Flexible Override**: You can still manually choose any mode")
    
    print(f"\n🔧 How to Use This in Codex:")
    print("-" * 40)
    print("1. **Type your request** in Codex (e.g., 'Design a database schema')")
    print("2. **System automatically detects** the appropriate mode")
    print("3. **Codex switches to that mode** with specialized knowledge")
    print("4. **Get tailored responses** based on the detected mode")
    print("5. **Override if needed** by specifying a different mode")
    
    print(f"\n✅ Codex integration test completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(test_codex_workflow())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
