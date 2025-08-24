#!/usr/bin/env python3
"""
Live Integration Test

This script tests the CodeZX-Codex integration while the API server is running.
Run with: python test_integration_live.py
"""

import requests
import json
import time

def test_live_integration():
    """Test the live integration with the running API server."""
    print("🔗 Testing Live CodeZX-Codex Integration")
    print("=" * 50)
    
    base_url = "http://localhost:8000/codezx"
    
    # Test health check first
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API is healthy - {health_data['agents_active']} agents active")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("💡 Make sure the server is running: python start_codex_integration.py")
        return False
    
    # Test mode detection with various requests
    test_requests = [
        {
            "description": "Architecture Request",
            "input": "Design a scalable database schema for a trading system with real-time data",
            "expected_mode": "architect"
        },
        {
            "description": "Development Request", 
            "input": "Write a Python function to calculate ATR levels for SPX trading",
            "expected_mode": "developer"
        },
        {
            "description": "Testing Request",
            "input": "Create test cases for API security vulnerabilities and performance testing",
            "expected_mode": "qa"
        },
        {
            "description": "DevOps Request",
            "input": "Deploy the trading system to production with monitoring and auto-scaling",
            "expected_mode": "devops"
        }
    ]
    
    print("\n🧪 Testing Mode Detection:")
    print("-" * 40)
    
    correct_detections = 0
    total_tests = len(test_requests)
    
    for i, test in enumerate(test_requests, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Input: {test['input']}")
        print(f"   Expected: {test['expected_mode']}")
        
        try:
            # Test flexible assignment endpoint
            response = requests.post(
                f"{base_url}/agents/flexible-assignment",
                json={"task_description": test['input']},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                detected_mode = result["data"]["recommended_agent"]
                confidence = result["data"]["reasoning"]
                
                print(f"   Detected: {detected_mode}")
                print(f"   Reasoning: {confidence}")
                
                if detected_mode == test['expected_mode']:
                    print(f"   ✅ CORRECT")
                    correct_detections += 1
                else:
                    print(f"   ❌ INCORRECT")
                    
            else:
                print(f"   ❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    # Test direct task assignment
    print(f"\n🎯 Testing Direct Task Assignment:")
    print("-" * 40)
    
    try:
        task_data = {
            "description": "Review the database architecture for scalability issues",
            "priority": "HIGH",
            "estimated_completion": "2 hours"
        }
        
        response = requests.post(
            f"{base_url}/agents/architect/tasks",
            json=task_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result["data"]["task_id"]
            agent = result["data"]["agent"]
            print(f"✅ Task assigned successfully")
            print(f"   Task ID: {task_id}")
            print(f"   Assigned to: {agent}")
        else:
            print(f"❌ Task assignment failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Task assignment error: {e}")
    
    # Test agent status
    print(f"\n📊 Testing Agent Status:")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/agents/status", timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            agents = status_data["data"]
            
            print(f"✅ Retrieved status for {len(agents)} agents:")
            for agent_name, agent_data in agents.items():
                tasks_completed = agent_data["performance_metrics"]["tasks_completed"]
                success_rate = agent_data["performance_metrics"]["success_rate"]
                current_tasks = agent_data["current_tasks"]
                
                print(f"   {agent_name}: {tasks_completed} completed, "
                      f"{success_rate:.1%} success, {current_tasks} active")
        else:
            print(f"❌ Status check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Status check error: {e}")
    
    # Summary
    print(f"\n📈 Test Results Summary:")
    print("-" * 40)
    accuracy = (correct_detections / total_tests) * 100
    print(f"Mode Detection Accuracy: {correct_detections}/{total_tests} ({accuracy:.1f}%)")
    
    if accuracy >= 80:
        print("✅ Integration is working well!")
    elif accuracy >= 60:
        print("⚠️  Integration is working but could be improved")
    else:
        print("❌ Integration needs improvement")
    
    print(f"\n🔗 Integration Endpoints Available:")
    print(f"   Health Check: {base_url}/health")
    print(f"   Mode Detection: {base_url}/agents/flexible-assignment")
    print(f"   Task Assignment: {base_url}/agents/{{type}}/tasks")
    print(f"   Agent Status: {base_url}/agents/status")
    print(f"   API Docs: http://localhost:8000/docs")
    
    return accuracy >= 60

def show_integration_instructions():
    """Show instructions for integrating with Codex."""
    print(f"\n🔧 How to Integrate with Codex:")
    print("-" * 40)
    print("1. **Use the API endpoints** in your Codex configuration")
    print("2. **Configure mode detection** using the flexible-assignment endpoint")
    print("3. **Set up automatic prompts** based on detected modes")
    print("4. **Reference knowledge base files** for each mode")
    
    print(f"\n📝 Example Codex Integration Code:")
    print("-" * 40)
    print("""
// JavaScript example for Codex plugin
async function enhancePrompt(userInput) {
    const response = await fetch('http://localhost:8000/codezx/agents/flexible-assignment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: userInput })
    });
    
    const result = await response.json();
    const mode = result.data.recommended_agent;
    
    // Load mode-specific configuration
    const config = await loadModeConfig(mode);
    
    // Return enhanced prompt for Codex
    return {
        systemPrompt: config.system_prompt,
        mode: mode,
        knowledgeFiles: config.knowledge_base
    };
}
""")

if __name__ == "__main__":
    try:
        success = test_live_integration()
        if success:
            show_integration_instructions()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
