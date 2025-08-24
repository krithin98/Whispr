"""
CodeZX Agent System for Whispr Trading Platform

This module implements the intelligent development partners that work alongside
the development team to accelerate development while maintaining code quality
and architectural consistency.

Agents:
- CodeZX-Architect: Design and maintain system architecture
- CodeZX-Developer: Implement features and fix bugs
- CodeZX-QA: Ensure code quality and system reliability
- CodeZX-DevOps: Manage infrastructure and deployment

The system supports both flexible task assignment (any agent can do any task)
and role-based recommendations for optimal task distribution.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from database import log_event, get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeZXAgent:
    """Base class for all CodeZX agents."""
    
    def __init__(self, name: str, role: str, capabilities: List[str], specializations: List[str]):
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.specializations = specializations  # What this agent is particularly good at
        self.task_history: List[Dict] = []
        self.current_tasks: List[Dict] = []
        self.performance_metrics = {
            "tasks_completed": 0,
            "success_rate": 1.0,
            "avg_completion_time": 0.0,
            "specialization_score": 1.0
        }
        
    async def log_activity(self, activity_type: str, details: Dict) -> None:
        """Log agent activity for audit and tracking."""
        await log_event("codezx_activity", {
            "agent": self.name,
            "role": self.role,
            "activity_type": activity_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    async def accept_task(self, task: Dict, force_assignment: bool = False) -> Dict:
        """Accept a new task and add it to current tasks."""
        task_id = f"{self.name}_{len(self.task_history) + 1}"
        task["task_id"] = task_id
        task["status"] = "ACCEPTED"
        task["accepted_at"] = datetime.now().isoformat()
        task["agent"] = self.name
        task["force_assigned"] = force_assignment
        
        self.current_tasks.append(task)
        
        await self.log_activity("task_accepted", task)
        
        return {
            "status": "ACCEPTED",
            "task_id": task_id,
            "agent": self.name,
            "estimated_completion": task.get("estimated_completion", "TBD"),
            "role_match": self._calculate_role_match(task),
            "force_assigned": force_assignment
        }
        
    def _calculate_role_match(self, task: Dict) -> float:
        """Calculate how well this agent's role matches the task."""
        task_description = task.get("description", "").lower()
        task_keywords = set(task_description.split())
        
        # Check specialization keywords
        specialization_matches = 0
        for spec in self.specializations:
            if spec.lower() in task_description:
                specialization_matches += 1
        
        # Check capability keywords
        capability_matches = 0
        for capability in self.capabilities:
            if capability.lower() in task_description:
                capability_matches += 1
        
        # Calculate match score (0.0 to 1.0)
        total_keywords = len(task_keywords)
        if total_keywords == 0:
            return 0.5  # Default neutral score
            
        match_score = (specialization_matches * 2 + capability_matches) / (total_keywords * 3)
        return min(1.0, max(0.0, match_score))
        
    async def complete_task(self, task_id: str, results: Dict) -> None:
        """Mark a task as completed with results."""
        task = next((t for t in self.current_tasks if t["task_id"] == task_id), None)
        if not task:
            return {"status": "ERROR", "message": "Task not found"}
            
        task["status"] = "COMPLETED"
        task["completed_at"] = datetime.now().isoformat()
        task["results"] = results
        
        # Calculate completion time
        accepted_time = datetime.fromisoformat(task["accepted_at"])
        completed_time = datetime.fromisoformat(task["completed_at"])
        completion_time = (completed_time - accepted_time).total_seconds() / 3600  # hours
        
        # Update performance metrics
        self.performance_metrics["tasks_completed"] += 1
        self.performance_metrics["avg_completion_time"] = (
            (self.performance_metrics["avg_completion_time"] * (self.performance_metrics["tasks_completed"] - 1) + completion_time) /
            self.performance_metrics["tasks_completed"]
        )
        
        # Move to history
        self.current_tasks.remove(task)
        self.task_history.append(task)
        
        await self.log_activity("task_completed", {
            "task_id": task_id,
            "results": results,
            "completion_time": task["completed_at"],
            "role_match": task.get("role_match", 0.0)
        })
        
        return {"status": "COMPLETED", "task_id": task_id, "results": results}
        
    def get_status(self) -> Dict:
        """Get current agent status and task information."""
        return {
            "agent": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "specializations": self.specializations,
            "current_tasks": len(self.current_tasks),
            "completed_tasks": len(self.task_history),
            "active_tasks": [t["task_id"] for t in self.current_tasks],
            "performance_metrics": self.performance_metrics,
            "role_match_avg": self._get_average_role_match()
        }
        
    def _get_average_role_match(self) -> float:
        """Calculate average role match for completed tasks."""
        if not self.task_history:
            return 0.0
            
        total_match = sum(t.get("role_match", 0.0) for t in self.task_history)
        return total_match / len(self.task_history)


class CodeZXArchitect(CodeZXAgent):
    """Architecture Agent: Design and maintain system architecture."""
    
    def __init__(self):
        super().__init__(
            name="CodeZX-Architect",
            role="System Architecture Design",
            capabilities=[
                "Architectural design and documentation",
                "Code review for architectural compliance",
                "Infrastructure improvement suggestions",
                "Design pattern maintenance",
                "Performance optimization planning"
            ],
            specializations=[
                "architecture", "design", "patterns", "scalability", "performance",
                "database design", "API design", "system design", "microservices"
            ]
        )


class CodeZXDeveloper(CodeZXAgent):
    """Development Agent: Implement features and fix bugs."""
    
    def __init__(self):
        super().__init__(
            name="CodeZX-Developer",
            role="Feature Implementation",
            capabilities=[
                "Production-ready code writing",
                "Unit and integration test implementation",
                "Coding standards compliance",
                "Technical documentation creation",
                "Bug fixing and optimization"
            ],
            specializations=[
                "coding", "implementation", "features", "bug fixes", "refactoring",
                "testing", "documentation", "optimization", "debugging"
            ]
        )


class CodeZXQA(CodeZXAgent):
    """Quality Agent: Ensure code quality and system reliability."""
    
    def __init__(self):
        super().__init__(
            name="CodeZX-QA",
            role="Quality Assurance",
            capabilities=[
                "Code review and quality assessment",
                "Performance testing and optimization",
                "Security vulnerability scanning",
                "Automated testing implementation",
                "Quality metrics tracking"
            ],
            specializations=[
                "testing", "quality", "performance", "security", "validation",
                "code review", "metrics", "automation", "reliability"
            ]
        )


class CodeZXDevOps(CodeZXAgent):
    """DevOps Agent: Manage infrastructure and deployment."""
    
    def __init__(self):
        super().__init__(
            name="CodeZX-DevOps",
            role="Infrastructure Management",
            capabilities=[
                "CI/CD pipeline management",
                "Infrastructure as Code (IaC)",
                "Monitoring and alerting setup",
                "Deployment automation",
                "Infrastructure scaling"
            ],
            specializations=[
                "deployment", "infrastructure", "CI/CD", "monitoring", "scaling",
                "automation", "pipeline", "devops", "kubernetes", "docker"
            ]
        )


class CodeZXUIUX(CodeZXAgent):
    """UI/UX Agent: Design and optimize user interfaces and experiences."""
    
    def __init__(self):
        super().__init__(
            name="CodeZX-UIUX",
            role="User Interface & Experience Design",
            capabilities=[
                "User interface design and prototyping",
                "User experience optimization",
                "Frontend component development",
                "Responsive design implementation",
                "Accessibility compliance",
                "User research and usability testing",
                "Design system creation",
                "Interactive prototype development"
            ],
            specializations=[
                "ui", "ux", "design", "frontend", "user interface", "user experience",
                "prototyping", "wireframing", "responsive", "accessibility", "usability",
                "design systems", "interaction design", "visual design", "user research"
            ]
        )


class CodeZXAgentManager:
    """Manages all CodeZX agents and coordinates their activities."""
    
    def __init__(self):
        self.agents = {
            "architect": CodeZXArchitect(),
            "developer": CodeZXDeveloper(),
            "qa": CodeZXQA(),
            "devops": CodeZXDevOps(),
            "uiux": CodeZXUIUX()
        }
        
    async def get_agent_status(self) -> Dict:
        """Get status of all agents."""
        return {
            agent_name: agent.get_status()
            for agent_name, agent in self.agents.items()
        }
        
    async def assign_task(self, agent_type: str, task: Dict, force_assignment: bool = False) -> Dict:
        """Assign a task to a specific agent type."""
        if agent_type not in self.agents:
            return {"status": "ERROR", "message": f"Unknown agent type: {agent_type}"}
            
        agent = self.agents[agent_type]
        return await agent.accept_task(task, force_assignment)
        
    async def get_agent_recommendations(self, task_description: str, include_scores: bool = True) -> Dict:
        """Get recommendations for which agent should handle a task."""
        task_lower = task_description.lower()
        
        # Calculate match scores for all agents
        agent_scores = {}
        for agent_name, agent in self.agents.items():
            # Calculate role match
            role_match = agent._calculate_role_match({"description": task_description})
            
            # Consider performance metrics
            performance_boost = agent.performance_metrics["success_rate"] * 0.2
            
            # Consider current workload (prefer less busy agents)
            workload_factor = 1.0 / (1.0 + len(agent.current_tasks) * 0.1)
            
            # Final score
            final_score = role_match * 0.6 + performance_boost + workload_factor * 0.2
            agent_scores[agent_name] = {
                "score": final_score,
                "role_match": role_match,
                "performance": agent.performance_metrics["success_rate"],
                "current_workload": len(agent.current_tasks),
                "reasoning": self._generate_recommendation_reasoning(agent, role_match, final_score)
            }
        
        # Sort by score
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        # Get top recommendation
        top_agent = sorted_agents[0][0]
        
        result = {
            "task_description": task_description,
            "recommended_agent": top_agent,
            "reasoning": agent_scores[top_agent]["reasoning"],
            "all_agent_scores": agent_scores if include_scores else None
        }
        
        return result
        
    def _generate_recommendation_reasoning(self, agent: CodeZXAgent, role_match: float, final_score: float) -> str:
        """Generate human-readable reasoning for agent recommendation."""
        reasons = []
        
        if role_match > 0.8:
            reasons.append(f"Excellent role match ({role_match:.1%})")
        elif role_match > 0.6:
            reasons.append(f"Good role match ({role_match:.1%})")
        elif role_match > 0.4:
            reasons.append(f"Moderate role match ({role_match:.1%})")
        else:
            reasons.append(f"Low role match ({role_match:.1%})")
            
        if agent.performance_metrics["success_rate"] > 0.9:
            reasons.append("High success rate")
        elif agent.performance_metrics["success_rate"] < 0.7:
            reasons.append("Lower success rate")
            
        if len(agent.current_tasks) == 0:
            reasons.append("Available (no current tasks)")
        elif len(agent.current_tasks) < 3:
            reasons.append("Light workload")
        else:
            reasons.append("Heavy workload")
            
        return "; ".join(reasons)
        
    async def run_workflow(self, workflow_steps: List[Dict]) -> Dict:
        """Run a complete workflow involving multiple agents."""
        workflow_results = []
        
        for step in workflow_steps:
            agent_type = step.get("agent_type")
            task = step.get("task")
            
            if not agent_type or not task:
                continue
                
            # Assign task to agent
            assignment = await self.assign_task(agent_type, task)
            
            # Simulate task execution
            await asyncio.sleep(1)  # Simulate work time
            
            # Complete task
            agent = self.agents[agent_type]
            completion = await agent.complete_task(
                assignment["task_id"], 
                {"output": f"Completed {task.get('description', 'task')}"}
            )
            
            workflow_results.append({
                "step": step,
                "assignment": assignment,
                "completion": completion
            })
            
        return {
            "workflow_status": "COMPLETED",
            "steps_completed": len(workflow_results),
            "results": workflow_results
        }
        
    async def get_flexible_agent_assignment(self, task_description: str) -> Dict:
        """Get flexible agent assignment allowing any agent to work on any task."""
        # Get recommendations
        recommendations = await self.get_agent_recommendations(task_description, include_scores=True)
        
        # Add flexibility note
        recommendations["flexibility_note"] = (
            "Any agent can work on any task. This is a recommendation based on "
            "role match and current workload. You can override and assign to any agent."
        )
        
        return recommendations


# Global agent manager instance
agent_manager = CodeZXAgentManager()


async def get_agent_status() -> Dict:
    """Get status of all CodeZX agents."""
    return await agent_manager.get_agent_status()


async def assign_task_to_agent(agent_type: str, task: Dict, force_assignment: bool = False) -> Dict:
    """Assign a task to a specific agent type."""
    return await agent_manager.assign_task(agent_type, task, force_assignment)


async def get_task_recommendations(task_description: str) -> Dict:
    """Get recommendations for which agent should handle a task."""
    return await agent_manager.get_agent_recommendations(task_description)


async def get_flexible_agent_assignment(task_description: str) -> Dict:
    """Get flexible agent assignment with recommendations."""
    return await agent_manager.get_flexible_agent_assignment(task_description)


async def run_agent_workflow(workflow_steps: List[Dict]) -> Dict:
    """Run a complete workflow involving multiple agents."""
    return await agent_manager.run_workflow(workflow_steps)


# Example usage and testing
if __name__ == "__main__":
    async def test_agents():
        """Test the CodeZX agent system."""
        print("🚀 Testing CodeZX Agent System...")
        
        # Test agent status
        status = await get_agent_status()
        print(f"Agent Status: {json.dumps(status, indent=2)}")
        
        # Test task assignment
        task = {
            "description": "Review database architecture for scalability",
            "priority": "HIGH",
            "estimated_completion": "2 hours"
        }
        
        assignment = await assign_task_to_agent("architect", task)
        print(f"Task Assignment: {json.dumps(assignment, indent=2)}")
        
        # Test flexible assignment
        flexible = await get_flexible_agent_assignment("Fix a bug in the authentication system")
        print(f"Flexible Assignment: {json.dumps(flexible, indent=2)}")
        
        # Test workflow
        workflow = [
            {
                "agent_type": "architect",
                "task": {"description": "Design API architecture", "priority": "HIGH"}
            },
            {
                "agent_type": "developer", 
                "task": {"description": "Implement API endpoints", "priority": "HIGH"}
            },
            {
                "agent_type": "qa",
                "task": {"description": "Test API functionality", "priority": "MEDIUM"}
            }
        ]
        
        workflow_result = await run_agent_workflow(workflow)
        print(f"Workflow Result: {json.dumps(workflow_result, indent=2)}")
        
    # Run the test
    asyncio.run(test_agents())
