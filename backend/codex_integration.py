"""
Codex Integration Layer

This module connects Codex with our CodeZX agent system, allowing Codex to:
1. Automatically detect which agent mode to use
2. Switch between different agent personalities
3. Use agent-specific knowledge and prompts
4. Track and learn from interactions
"""

import re
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from codezx_agents import get_task_recommendations, assign_task_to_agent

class CodexModeDetector:
    """Detects which agent mode Codex should use based on user input."""
    
    def __init__(self):
        # Keywords that trigger each agent mode
        self.mode_keywords = {
            "architect": [
                "design", "architecture", "schema", "scalability", "pattern",
                "system design", "database design", "api design", "microservices",
                "infrastructure", "planning", "blueprint", "structure", "framework",
                "architectural", "design pattern", "system architecture", "data model",
                "service design", "component design", "integration design"
            ],
            "developer": [
                "implement", "code", "fix", "feature", "bug", "function",
                "write", "create", "build", "develop", "program", "coding",
                "refactor", "optimize", "debug", "algorithm", "data structure",
                "class", "method", "function", "variable", "loop", "condition",
                "api", "endpoint", "service", "module", "library"
            ],
            "qa": [
                "test", "testing", "quality", "validation", "verify", "check",
                "bug report", "test case", "performance test", "security test",
                "user acceptance", "regression", "edge case", "test plan",
                "test suite", "automated testing", "manual testing", "unit test",
                "integration test", "system test", "user testing", "qa",
                "performance", "security", "vulnerabilities", "endpoints",
                "api testing", "load testing", "stress testing", "penetration test",
                "quality assurance", "test coverage", "test automation"
            ],
            "devops": [
                "deploy", "deployment", "infrastructure", "monitor", "pipeline",
                "ci/cd", "kubernetes", "docker", "aws", "azure", "gcp",
                "scaling", "monitoring", "alerting", "backup", "server",
                "cloud", "container", "orchestration", "automation", "devops",
                "production", "staging", "environment", "configuration"
            ],
            "uiux": [
                "ui", "ux", "user interface", "user experience", "design",
                "frontend", "prototype", "wireframe", "mockup", "responsive",
                "accessibility", "usability", "user research", "interaction",
                "visual design", "design system", "component library", "css",
                "html", "javascript", "react", "vue", "angular", "figma",
                "sketch", "adobe", "user testing", "user feedback", "user journey",
                "information architecture", "navigation", "layout", "typography",
                "color scheme", "iconography", "animation", "microinteractions",
                "dashboard", "settings", "form", "modal", "button", "input",
                "component", "interface", "user flow", "wireframes", "mockups",
                "design tokens", "style guide", "branding", "visual hierarchy",
                "user centered", "user centered design", "human centered design",
                "onboarding", "user flows", "user journey", "user experience design",
                "design system"
            ]
        }
        
        # Mode-specific prompts and instructions
        self.mode_prompts = {
            "architect": {
                "system_prompt": "You are CodeZX-Architect, a senior system architect. Focus on: system design, scalability, architectural patterns, and long-term planning. Always consider performance, maintainability, and future growth.",
                "knowledge_files": ["architecture_guidelines.md", "system_patterns.md", "scalability_principles.md"],
                "response_style": "Provide high-level architectural guidance with clear reasoning and multiple options when appropriate."
            },
            "developer": {
                "system_prompt": "You are CodeZX-Developer, a senior software developer. Focus on: clean code, best practices, implementation details, and practical solutions. Always consider code quality, maintainability, and performance.",
                "knowledge_files": ["coding_standards.md", "best_practices.md", "design_patterns.md"],
                "response_style": "Provide practical, implementable code solutions with explanations and best practices."
            },
            "qa": {
                "system_prompt": "You are CodeZX-QA, a senior quality assurance engineer. Focus on: testing strategies, quality metrics, edge cases, and validation approaches. Always consider user experience, reliability, and risk mitigation.",
                "knowledge_files": ["testing_protocols.md", "quality_metrics.md", "test_strategies.md"],
                "response_style": "Provide comprehensive testing approaches with specific test cases and quality considerations."
            },
            "devops": {
                "system_prompt": "You are CodeZX-DevOps, a senior DevOps engineer. Focus on: infrastructure, deployment, monitoring, and operational excellence. Always consider reliability, scalability, and security.",
                "knowledge_files": ["deployment_guides.md", "infrastructure_patterns.md", "monitoring_strategies.md"],
                "response_style": "Provide infrastructure and deployment solutions with operational considerations and best practices."
            },
            "uiux": {
                "system_prompt": "You are CodeZX-UIUX, a senior UI/UX designer and frontend developer. Focus on: user-centered design, intuitive interfaces, accessibility, responsive design, and creating delightful user experiences. Always consider usability, accessibility standards, and modern design principles.",
                "knowledge_files": ["ui_ux_guidelines.md", "design_systems.md", "accessibility_standards.md", "frontend_best_practices.md"],
                "response_style": "Provide user-centered design solutions with clear visual guidance, accessibility considerations, and practical implementation approaches."
            }
        }
    
    def detect_mode(self, user_input: str) -> Tuple[str, float, str]:
        """
        Detect which agent mode should be used based on user input.
        
        Returns:
            Tuple of (mode, confidence_score, reasoning)
        """
        user_input_lower = user_input.lower()
        
        # Calculate match scores for each mode
        mode_scores = {}
        for mode, keywords in self.mode_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                # Check for exact word matches (more weight)
                if f" {keyword} " in f" {user_input_lower} ":
                    score += 2
                    matched_keywords.append(keyword)
                # Check for partial matches (less weight)
                elif keyword in user_input_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Normalize score (0.0 to 1.0) - more lenient threshold
            normalized_score = min(1.0, score / (len(keywords) * 1.5))
            mode_scores[mode] = {
                "score": normalized_score,
                "matched_keywords": matched_keywords
            }
        
        # Find the best matching mode
        best_mode = max(mode_scores.items(), key=lambda x: x[1]["score"])
        mode_name, mode_data = best_mode
        
        # Generate reasoning with more lenient thresholds
        if mode_data["score"] > 0.2:
            reasoning = f"High confidence ({mode_data['score']:.1%}) - matched keywords: {', '.join(mode_data['matched_keywords'])}"
        elif mode_data["score"] > 0.05:
            reasoning = f"Moderate confidence ({mode_data['score']:.1%}) - matched keywords: {', '.join(mode_data['matched_keywords'])}"
        else:
            reasoning = f"Low confidence ({mode_data['score']:.1%}) - defaulting to developer mode"
            mode_name = "developer"  # Default fallback
        
        return mode_name, mode_data["score"], reasoning
    
    def get_mode_config(self, mode: str) -> Dict:
        """Get configuration for a specific agent mode."""
        if mode not in self.mode_prompts:
            mode = "developer"  # Default fallback
        
        return self.mode_prompts[mode]
    
    def get_enhanced_prompt(self, mode: str, user_input: str) -> str:
        """Get an enhanced prompt that includes mode-specific context."""
        mode_config = self.get_mode_config(mode)
        
        enhanced_prompt = f"""
{mode_config['system_prompt']}

User Request: {user_input}

Please respond in the style of {mode_config['response_style']}

Knowledge Base Files to Reference:
{chr(10).join(f"- {file}" for file in mode_config['knowledge_files'])}

Remember: You are operating in {mode} mode. Tailor your response accordingly.
"""
        return enhanced_prompt.strip()


class CodexAgentManager:
    """Manages the interaction between Codex and our agent system."""
    
    def __init__(self):
        self.mode_detector = CodexModeDetector()
        self.interaction_history = []
    
    async def process_codex_request(self, user_input: str) -> Dict:
        """
        Process a Codex request and determine the appropriate agent mode.
        
        Args:
            user_input: The user's input to Codex
            
        Returns:
            Dict containing mode detection results and agent recommendations
        """
        # Detect the appropriate mode
        detected_mode, confidence, reasoning = self.mode_detector.detect_mode(user_input)
        
        # Get mode configuration
        mode_config = self.mode_detector.get_mode_config(detected_mode)
        
        # Get agent recommendations from our system
        try:
            agent_recommendations = await get_task_recommendations(user_input)
        except Exception as e:
            agent_recommendations = {
                "recommended_agent": detected_mode,
                "reasoning": f"Error getting recommendations: {str(e)}"
            }
        
        # Create enhanced prompt for Codex
        enhanced_prompt = self.mode_detector.get_enhanced_prompt(detected_mode, user_input)
        
        # Log the interaction
        interaction = {
            "timestamp": asyncio.get_event_loop().time(),
            "user_input": user_input,
            "detected_mode": detected_mode,
            "confidence": confidence,
            "reasoning": reasoning,
            "agent_recommendations": agent_recommendations,
            "enhanced_prompt": enhanced_prompt
        }
        self.interaction_history.append(interaction)
        
        return {
            "mode_detection": {
                "detected_mode": detected_mode,
                "confidence": confidence,
                "reasoning": reasoning
            },
            "agent_recommendations": agent_recommendations,
            "codex_instructions": {
                "mode": detected_mode,
                "system_prompt": mode_config["system_prompt"],
                "enhanced_prompt": enhanced_prompt,
                "knowledge_files": mode_config["knowledge_files"],
                "response_style": mode_config["response_style"]
            },
            "interaction_id": len(self.interaction_history)
        }
    
    def get_interaction_history(self) -> List[Dict]:
        """Get the history of all interactions."""
        return self.interaction_history
    
    def get_mode_statistics(self) -> Dict:
        """Get statistics about mode usage."""
        mode_counts = {}
        total_interactions = len(self.interaction_history)
        
        for interaction in self.interaction_history:
            mode = interaction["detected_mode"]
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
        
        return {
            "total_interactions": total_interactions,
            "mode_distribution": mode_counts,
            "mode_percentages": {
                mode: (count / total_interactions) * 100 
                for mode, count in mode_counts.items()
            } if total_interactions > 0 else {}
        }


class CodexConfiguration:
    """Manages Codex configuration files and settings."""
    
    def __init__(self, config_dir: str = "./codex_config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
    
    def create_mode_config_file(self, mode: str) -> str:
        """Create a configuration file for a specific agent mode."""
        mode_config = {
            "mode": mode,
            "description": f"Configuration for {mode} mode in Codex",
            "trigger_keywords": self._get_trigger_keywords(mode),
            "system_prompt": self._get_system_prompt(mode),
            "knowledge_base": self._get_knowledge_base(mode),
            "response_templates": self._get_response_templates(mode)
        }
        
        config_file = self.config_dir / f"{mode}_config.json"
        with open(config_file, 'w') as f:
            json.dump(mode_config, f, indent=2)
        
        return str(config_file)
    
    def _get_trigger_keywords(self, mode: str) -> List[str]:
        """Get trigger keywords for a specific mode."""
        keywords = {
            "architect": ["design", "architecture", "schema", "scalability", "pattern"],
            "developer": ["implement", "code", "fix", "feature", "bug"],
            "qa": ["test", "testing", "quality", "validation", "verify"],
            "devops": ["deploy", "infrastructure", "monitor", "pipeline"]
        }
        return keywords.get(mode, [])
    
    def _get_system_prompt(self, mode: str) -> str:
        """Get system prompt for a specific mode."""
        prompts = {
            "architect": "You are CodeZX-Architect. Focus on system design, scalability, and architectural patterns.",
            "developer": "You are CodeZX-Developer. Focus on clean code, best practices, and implementation.",
            "qa": "You are CodeZX-QA. Focus on testing strategies, quality metrics, and validation.",
            "devops": "You are CodeZX-DevOps. Focus on infrastructure, deployment, and operational excellence."
        }
        return prompts.get(mode, "You are a coding assistant.")
    
    def _get_knowledge_base(self, mode: str) -> List[str]:
        """Get knowledge base files for a specific mode."""
        knowledge = {
            "architect": ["architecture_guidelines.md", "system_patterns.md"],
            "developer": ["coding_standards.md", "best_practices.md"],
            "qa": ["testing_protocols.md", "quality_metrics.md"],
            "devops": ["deployment_guides.md", "infrastructure_patterns.md"],
            "uiux": ["ui_ux_guidelines.md", "design_systems.md", "accessibility_standards.md"]
        }
        return knowledge.get(mode, [])
    
    def _get_response_templates(self, mode: str) -> Dict[str, str]:
        """Get response templates for a specific mode."""
        templates = {
            "architect": {
                "introduction": "As a system architect, I'll help you design this solution.",
                "conclusion": "This architectural approach ensures scalability and maintainability."
            },
            "developer": {
                "introduction": "As a developer, I'll implement this solution with best practices.",
                "conclusion": "This implementation follows clean code principles and best practices."
            },
            "qa": {
                "introduction": "As a QA engineer, I'll help you test and validate this solution.",
                "conclusion": "This testing approach ensures quality and reliability."
            },
            "devops": {
                "introduction": "As a DevOps engineer, I'll help you deploy and operate this solution.",
                "conclusion": "This deployment approach ensures reliability and scalability."
            },
            "uiux": {
                "introduction": "As a UI/UX designer, I'll help you create intuitive and accessible user experiences.",
                "conclusion": "This design approach ensures usability, accessibility, and user satisfaction."
            }
        }
        return templates.get(mode, {})
    
    def create_all_configs(self) -> List[str]:
        """Create configuration files for all agent modes."""
        modes = ["architect", "developer", "qa", "devops", "uiux"]
        config_files = []
        
        for mode in modes:
            config_file = self.create_mode_config_file(mode)
            config_files.append(config_file)
            print(f"✅ Created {mode} configuration: {config_file}")
        
        return config_files


# Global instances
codex_manager = CodexAgentManager()
codex_config = CodexConfiguration()


async def process_codex_request(user_input: str) -> Dict:
    """Process a Codex request and get mode detection results."""
    return await codex_manager.process_codex_request(user_input)


def create_codex_configs() -> List[str]:
    """Create all Codex configuration files."""
    return codex_config.create_all_configs()


def get_codex_stats() -> Dict:
    """Get Codex interaction statistics."""
    return codex_manager.get_mode_statistics()


# Example usage
if __name__ == "__main__":
    async def test_codex_integration():
        """Test the Codex integration system."""
        print("🚀 Testing Codex Integration...")
        
        # Test mode detection
        test_inputs = [
            "Design a new database schema for user management",
            "Fix the bug in the login system",
            "Test the API endpoints for performance",
            "Deploy the application to production"
        ]
        
        for test_input in test_inputs:
            print(f"\n🧪 Testing: {test_input}")
            result = await process_codex_request(test_input)
            
            print(f"   Detected Mode: {result['mode_detection']['detected_mode']}")
            print(f"   Confidence: {result['mode_detection']['confidence']:.1%}")
            print(f"   Reasoning: {result['mode_detection']['reasoning']}")
        
        # Create configuration files
        print("\n📁 Creating Codex configuration files...")
        config_files = create_codex_configs()
        
        # Show statistics
        print("\n📊 Codex Integration Statistics:")
        stats = get_codex_stats()
        print(f"   Total Interactions: {stats['total_interactions']}")
        print(f"   Mode Distribution: {stats['mode_distribution']}")
        
        print("\n✅ Codex integration test completed!")
    
    # Run the test
    asyncio.run(test_codex_integration())
