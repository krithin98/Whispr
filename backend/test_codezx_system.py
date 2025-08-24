#!/usr/bin/env python3
"""
CodeZX Agent System Test Suite

This script tests the complete CodeZX agent system including:
- Agent creation and initialization
- Task assignment and execution
- Workflow management
- API endpoint functionality
- Database integration
- Error handling

Run with: python test_codezx_system.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def test_agent_creation():
    """Test agent creation and basic functionality."""
    print("🧪 Testing Agent Creation...")
    
    try:
        from codezx_agents import (
            CodeZXArchitect, CodeZXDeveloper, CodeZXQA, CodeZXDevOps,
            CodeZXAgentManager
        )
        
        # Test individual agents
        architect = CodeZXArchitect()
        developer = CodeZXDeveloper()
        qa = CodeZXQA()
        devops = CodeZXDevOps()
        
        print(f"✅ Created {architect.name} - {architect.role}")
        print(f"✅ Created {developer.name} - {developer.role}")
        print(f"✅ Created {qa.name} - {qa.role}")
        print(f"✅ Created {devops.name} - {devops.role}")
        
        # Test agent manager
        manager = CodeZXAgentManager()
        status = await manager.get_agent_status()
        
        print(f"✅ Agent Manager created with {len(status)} agents")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False

async def test_task_assignment():
    """Test task assignment to agents."""
    print("\n🧪 Testing Task Assignment...")
    
    try:
        from codezx_agents import assign_task_to_agent
        
        # Test task assignment
        task = {
            "description": "Review database architecture for scalability",
            "priority": "HIGH",
            "estimated_completion": "2 hours",
            "requirements": {"database": "SQLite", "focus": "scalability"}
        }
        
        assignment = await assign_task_to_agent("architect", task)
        
        print(f"✅ Task assigned: {assignment['task_id']}")
        print(f"   Agent: {assignment['agent']}")
        print(f"   Status: {assignment['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Task assignment failed: {e}")
        return False

async def test_workflow_execution():
    """Test complete workflow execution."""
    print("\n🧪 Testing Workflow Execution...")
    
    try:
        from codezx_agents import run_agent_workflow
        
        # Test workflow
        workflow = [
            {
                "agent_type": "architect",
                "task": {
                    "description": "Design API architecture",
                    "priority": "HIGH",
                    "estimated_completion": "2 hours"
                }
            },
            {
                "agent_type": "developer",
                "task": {
                    "description": "Implement API endpoints",
                    "priority": "HIGH",
                    "estimated_completion": "4 hours"
                }
            },
            {
                "agent_type": "qa",
                "task": {
                    "description": "Test API functionality",
                    "priority": "MEDIUM",
                    "estimated_completion": "2 hours"
                }
            }
        ]
        
        workflow_result = await run_agent_workflow(workflow)
        
        print(f"✅ Workflow completed: {workflow_result['workflow_status']}")
        print(f"   Steps completed: {workflow_result['steps_completed']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        return False

async def test_agent_recommendations():
    """Test agent recommendation system."""
    print("\n🧪 Testing Agent Recommendations...")
    
    try:
        from codezx_agents import get_task_recommendations
        
        # Test different task types
        test_tasks = [
            "Design a new database schema for user management",
            "Fix a bug in the authentication system",
            "Run performance tests on the API endpoints",
            "Deploy the application to production"
        ]
        
        for task in test_tasks:
            recommendation = await get_task_recommendations(task)
            print(f"✅ Task: {task[:50]}...")
            print(f"   Recommended Agent: {recommendation['recommended_agent']}")
            print(f"   Reasoning: {recommendation['reasoning']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent recommendations failed: {e}")
        return False

async def test_database_integration():
    """Test database integration and logging."""
    print("\n🧪 Testing Database Integration...")
    
    try:
        from codezx_agents import get_agent_status
        from database import get_db
        
        # Test database connection
        conn = await get_db()
        print("✅ Database connection established")
        
        # Test agent activity logging
        status = await get_agent_status()
        print(f"✅ Agent status retrieved: {len(status)} agents")
        
        # Check if events table exists and has data
        rows = await conn.execute_fetchall(
            "SELECT COUNT(*) FROM events WHERE event_type = 'codezx_activity'"
        )
        event_count = rows[0][0] if rows else 0
        print(f"✅ CodeZX events logged: {event_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database integration failed: {e}")
        return False

async def test_api_endpoints():
    """Test API endpoint functionality."""
    print("\n🧪 Testing API Endpoints...")
    
    try:
        from codezx_api import (
            get_all_agent_status,
            get_agent_status_by_type,
            get_agent_recommendation,
            get_workflow_examples,
            health_check
        )
        
        # Test health check
        health = await health_check()
        print(f"✅ Health check: {health['status']}")
        
        # Test agent status
        status = await get_all_agent_status()
        print(f"✅ Agent status API: {status['status']}")
        
        # Test workflow examples
        examples = await get_workflow_examples()
        print(f"✅ Workflow examples: {len(examples['data'])} examples")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint testing failed: {e}")
        return False

async def test_error_handling():
    """Test error handling and edge cases."""
    print("\n🧪 Testing Error Handling...")
    
    try:
        from codezx_agents import assign_task_to_agent, get_agent_status
        
        # Test invalid agent type
        try:
            await assign_task_to_agent("invalid_agent", {"description": "test"})
            print("❌ Should have failed with invalid agent type")
            return False
        except Exception as e:
            print(f"✅ Correctly handled invalid agent type: {type(e).__name__}")
        
        # Test empty task
        try:
            await assign_task_to_agent("developer", {})
            print("✅ Handled empty task gracefully")
        except Exception as e:
            print(f"✅ Correctly handled empty task: {type(e).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def run_performance_test():
    """Run basic performance tests."""
    print("\n🧪 Running Performance Tests...")
    
    try:
        from codezx_agents import get_agent_status, assign_task_to_agent
        
        # Test response time for agent status
        start_time = time.time()
        await get_agent_status()
        status_time = time.time() - start_time
        
        print(f"✅ Agent status response time: {status_time:.3f}s")
        
        # Test task assignment performance
        start_time = time.time()
        task = {"description": "Performance test task", "priority": "LOW"}
        await assign_task_to_agent("developer", task)
        assignment_time = time.time() - start_time
        
        print(f"✅ Task assignment response time: {assignment_time:.3f}s")
        
        # Performance thresholds
        if status_time < 0.1 and assignment_time < 0.1:
            print("✅ Performance within acceptable limits")
            return True
        else:
            print("⚠️  Performance below expected thresholds")
            return False
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 CodeZX Agent System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Agent Creation", test_agent_creation),
        ("Task Assignment", test_task_assignment),
        ("Workflow Execution", test_workflow_execution),
        ("Agent Recommendations", test_agent_recommendations),
        ("Database Integration", test_database_integration),
        ("API Endpoints", test_api_endpoints),
        ("Error Handling", test_error_handling),
        ("Performance", run_performance_test)
    ]
    
    results = {}
    total_tests = len(tests)
    passed_tests = 0
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
            if result:
                passed_tests += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! CodeZX system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)
