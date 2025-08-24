#!/usr/bin/env python3
"""
CodeZX-Codex Integration Starter

This script sets up and starts the CodeZX agent system for Codex integration.
Run with: python start_codex_integration.py
"""

import asyncio
import subprocess
import sys
import time
import requests
from pathlib import Path

def print_header():
    print("🚀 CodeZX-Codex Integration Starter")
    print("=" * 50)

def check_dependencies():
    """Check if required modules are available."""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        import aiosqlite
        print("✅ All dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Install with: pip install fastapi uvicorn aiosqlite")
        return False

def setup_configuration():
    """Set up configuration files."""
    print("📁 Setting up configuration files...")
    
    try:
        from codex_integration import create_codex_configs
        config_files = create_codex_configs()
        print(f"✅ Created {len(config_files)} configuration files")
        return True
    except Exception as e:
        print(f"❌ Failed to create configuration: {e}")
        return False

def test_agent_system():
    """Test the agent system functionality."""
    print("🧪 Testing agent system...")
    
    try:
        from codezx_agents import get_agent_status
        status = asyncio.run(get_agent_status())
        print(f"✅ Agent system working - {len(status)} agents active")
        return True
    except Exception as e:
        print(f"❌ Agent system test failed: {e}")
        return False

def start_api_server():
    """Start the FastAPI server."""
    print("🌐 Starting API server...")
    
    try:
        # Start uvicorn in a subprocess
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ]
        
        print("🚀 Starting server with command:", " ".join(cmd))
        print("📍 Server will be available at: http://localhost:8000")
        print("🔗 API Documentation: http://localhost:8000/docs")
        print("🏥 Health Check: http://localhost:8000/codezx/health")
        print("\n💡 To stop the server, press Ctrl+C")
        print("-" * 50)
        
        # Start the server
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def test_api_endpoints():
    """Test API endpoints if server is running."""
    print("🔌 Testing API endpoints...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/codezx/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is responding")
            
            # Test mode detection
            test_request = {
                "task_description": "Design a database schema for user management"
            }
            
            response = requests.post(
                "http://localhost:8000/codezx/agents/flexible-assignment",
                json=test_request,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                mode = result["data"]["recommended_agent"]
                print(f"✅ Mode detection working - detected: {mode}")
                return True
            else:
                print(f"❌ Mode detection failed: {response.status_code}")
                return False
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API not accessible: {e}")
        return False

def show_integration_examples():
    """Show examples of how to use the integration."""
    print("\n🎯 Integration Examples:")
    print("-" * 30)
    
    examples = [
        {
            "request": "Design a database schema for user management",
            "expected_mode": "architect",
            "curl_command": '''curl -X POST "http://localhost:8000/codezx/agents/flexible-assignment" \\
  -H "Content-Type: application/json" \\
  -d '{"task_description": "Design a database schema for user management"}\''''
        },
        {
            "request": "Fix the login bug in authentication",
            "expected_mode": "developer", 
            "curl_command": '''curl -X POST "http://localhost:8000/codezx/agents/flexible-assignment" \\
  -H "Content-Type: application/json" \\
  -d '{"task_description": "Fix the login bug in authentication"}\''''
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['request']}")
        print(f"   Expected Mode: {example['expected_mode']}")
        print(f"   Test Command:")
        print(f"   {example['curl_command']}")

def main():
    """Main function to set up and start the integration."""
    print_header()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Set up configuration
    if not setup_configuration():
        sys.exit(1)
    
    # Test agent system
    if not test_agent_system():
        sys.exit(1)
    
    print("\n✅ Setup completed successfully!")
    print("\n🎯 Next Steps:")
    print("1. Start the API server (this script will do it)")
    print("2. Test the endpoints")
    print("3. Integrate with your Codex setup")
    
    # Ask user if they want to start the server
    try:
        choice = input("\n🚀 Start the API server now? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            start_api_server()
        else:
            print("\n💡 To start the server manually:")
            print("   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
            
            # Show integration examples
            show_integration_examples()
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup interrupted by user")

if __name__ == "__main__":
    main()
