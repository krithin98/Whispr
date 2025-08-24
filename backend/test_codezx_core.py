#!/usr/bin/env python3
"""
CodeZX Agent System - Core Functionality Test

This script tests the core agent functionality without external dependencies.
Run with: python test_codezx_core.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

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
        print(f"   Role Match: {assignment['role_match']:.2f}")
        
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

async def test_flexible_assignment():
    """Test flexible agent assignment."""
    print("\n🧪 Testing Flexible Assignment...")
    
    try:
        from codezx_agents import get_flexible_agent_assignment
        
        # Test flexible assignment
        task = "Implement WebSocket real-time data streaming for market data"
        flexible = await get_flexible_agent_assignment(task)
        
        print(f"✅ Task: {task[:50]}...")
        print(f"   Recommended Agent: {flexible['recommended_agent']}")
        print(f"   Reasoning: {flexible['reasoning']}")
        print(f"   Flexibility Note: {flexible['flexibility_note']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flexible assignment failed: {e}")
        return False

async def test_performance_metrics():
    """Test agent performance tracking."""
    print("\n🧪 Testing Performance Metrics...")
    
    try:
        from codezx_agents import get_agent_status
        
        # Get agent status
        status = await get_agent_status()
        
        print("✅ Agent Performance Metrics:")
        for agent_name, agent_data in status.items():
            metrics = agent_data['performance_metrics']
            print(f"   {agent_name}: {metrics['tasks_completed']} tasks, "
                  f"{metrics['success_rate']:.1%} success rate")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance metrics failed: {e}")
        return False

async def main():
    """Run all core tests."""
    print("🚀 CodeZX Agent System - Core Functionality Test")
    print("=" * 60)
    
    tests = [
        ("Agent Creation", test_agent_creation),
        ("Task Assignment", test_task_assignment),
        ("Workflow Execution", test_workflow_execution),
        ("Agent Recommendations", test_agent_recommendations),
        ("Flexible Assignment", test_flexible_assignment),
        ("Performance Metrics", test_performance_metrics)
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
    print("\n" + "=" * 60)
    print("📊 CORE TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 All core tests passed! CodeZX system is working correctly.")
        print("\n🚀 Next steps:")
        print("   1. Test with FastAPI integration")
        print("   2. Test database integration")
        print("   3. Deploy to production")
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
