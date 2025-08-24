import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codex_integration import process_codex_request
import asyncio

def test_uiux_detection_examples():
    """Test UI/UX mode detection for various design requests."""
    async def run_tests():
        # Test UI/UX detection
        result1 = await process_codex_request("Design a responsive navigation component")
        assert result1["mode_detection"]["detected_mode"] == "uiux", f"Expected uiux, got {result1['mode_detection']['detected_mode']}"
        
        result2 = await process_codex_request("Create wireframes for account settings")
        assert result2["mode_detection"]["detected_mode"] == "uiux", f"Expected uiux, got {result2['mode_detection']['detected_mode']}"
        
        print("✅ UI/UX detection tests passed")
    
    asyncio.run(run_tests())

def test_dev_detection_examples():
    """Test Developer mode detection for various coding requests."""
    async def run_tests():
        result = await process_codex_request("Fix login bug on /auth when token invalid")
        assert result["mode_detection"]["detected_mode"] == "developer", f"Expected developer, got {result['mode_detection']['detected_mode']}"
        
        print("✅ Developer detection tests passed")
    
    asyncio.run(run_tests())

def test_architect_detection_examples():
    """Test Architect mode detection for various design requests."""
    async def run_tests():
        result = await process_codex_request("Design database schema for user management")
        assert result["mode_detection"]["detected_mode"] == "architect", f"Expected architect, got {result['mode_detection']['detected_mode']}"
        
        print("✅ Architect detection tests passed")
    
    asyncio.run(run_tests())

def test_qa_detection_examples():
    """Test QA mode detection for various testing requests."""
    async def run_tests():
        result = await process_codex_request("Test API endpoints for security vulnerabilities")
        assert result["mode_detection"]["detected_mode"] == "qa", f"Expected qa, got {result['mode_detection']['detected_mode']}"
        
        print("✅ QA detection tests passed")
    
    asyncio.run(run_tests())

def test_devops_detection_examples():
    """Test DevOps mode detection for various deployment requests."""
    async def run_tests():
        result = await process_codex_request("Deploy application to production with monitoring")
        assert result["mode_detection"]["detected_mode"] == "devops", f"Expected devops, got {result['mode_detection']['detected_mode']}"
        
        print("✅ DevOps detection tests passed")
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    print("🧪 Running CodeZX Router Mode Detection Tests...")
    
    test_uiux_detection_examples()
    test_dev_detection_examples()
    test_architect_detection_examples()
    test_qa_detection_examples()
    test_devops_detection_examples()
    
    print("🎉 All router mode detection tests passed!")
