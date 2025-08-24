"""
CodeZX Agent API Endpoints

This module provides REST API endpoints for the CodeZX agent system,
allowing external systems to interact with the intelligent development
partners programmatically.

The system supports both role-based recommendations and flexible task assignment,
allowing any agent to work on any task while providing intelligent suggestions.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import asyncio
import logging

from codezx_agents import (
    get_agent_status,
    assign_task_to_agent,
    get_task_recommendations,
    get_flexible_agent_assignment,
    run_agent_workflow
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/codezx", tags=["CodeZX Agents"])

# Pydantic models for request/response validation
class TaskRequest(BaseModel):
    """Request model for task assignment."""
    description: str = Field(..., description="Task description")
    priority: str = Field("MEDIUM", description="Task priority (LOW/MEDIUM/HIGH)")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time")
    requirements: Optional[Dict[str, Any]] = Field(None, description="Task requirements")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class WorkflowStep(BaseModel):
    """Model for workflow step definition."""
    agent_type: str = Field(..., description="Type of agent (architect/developer/qa/devops)")
    task: TaskRequest = Field(..., description="Task to be executed")

class WorkflowRequest(BaseModel):
    """Request model for workflow execution."""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    steps: List[WorkflowStep] = Field(..., description="Workflow steps")
    priority: str = Field("MEDIUM", description="Workflow priority")

class AgentRecommendationRequest(BaseModel):
    """Request model for agent recommendations."""
    task_description: str = Field(..., description="Description of the task")

class FlexibleAssignmentRequest(BaseModel):
    """Request model for flexible agent assignment."""
    task_description: str = Field(..., description="Description of the task")
    preferred_agent: Optional[str] = Field(None, description="Preferred agent (optional)")
    force_assignment: bool = Field(False, description="Force assignment to specific agent")

# API Endpoints

@router.get("/agents/status")
async def get_all_agent_status() -> Dict[str, Any]:
    """
    Get status of all CodeZX agents.
    
    Returns:
        Dict containing status information for all agents
    """
    try:
        status = await get_agent_status()
        return {
            "status": "success",
            "data": status,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")

@router.get("/agents/{agent_type}/status")
async def get_agent_status_by_type(agent_type: str) -> Dict[str, Any]:
    """
    Get status of a specific agent type.
    
    Args:
        agent_type: Type of agent (architect/developer/qa/devops)
    
    Returns:
        Dict containing status information for the specified agent
    """
    try:
        all_status = await get_agent_status()
        if agent_type not in all_status:
            raise HTTPException(status_code=404, detail=f"Agent type '{agent_type}' not found")
        
        return {
            "status": "success",
            "data": all_status[agent_type],
            "timestamp": asyncio.get_event_loop().time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent status for {agent_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")

@router.post("/agents/{agent_type}/tasks")
async def assign_task(
    agent_type: str,
    task_request: TaskRequest,
    force_assignment: bool = Query(False, description="Force assignment even if not optimal"),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Assign a task to a specific agent type.
    
    Args:
        agent_type: Type of agent (architect/developer/qa/devops)
        task_request: Task details
        force_assignment: Force assignment even if not optimal
        background_tasks: FastAPI background tasks
    
    Returns:
        Dict containing task assignment information
    """
    try:
        # Validate agent type
        valid_agents = ["architect", "developer", "qa", "devops"]
        if agent_type not in valid_agents:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid agent type. Must be one of: {valid_agents}"
            )
        
        # Convert Pydantic model to dict
        task_dict = task_request.dict()
        
        # Assign task to agent
        assignment = await assign_task_to_agent(agent_type, task_dict, force_assignment)
        
        # Log the assignment
        logger.info(f"Task assigned to {agent_type}: {assignment}")
        
        return {
            "status": "success",
            "data": assignment,
            "message": f"Task successfully assigned to {agent_type}",
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning task to {agent_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")

@router.post("/agents/recommendations")
async def get_agent_recommendation(
    request: AgentRecommendationRequest
) -> Dict[str, Any]:
    """
    Get recommendations for which agent should handle a task.
    
    Args:
        request: Task description for recommendation
    
    Returns:
        Dict containing agent recommendation and reasoning
    """
    try:
        recommendation = await get_task_recommendations(request.task_description)
        
        return {
            "status": "success",
            "data": recommendation,
            "message": "Agent recommendation generated successfully",
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error(f"Error getting agent recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendation: {str(e)}")

@router.post("/agents/flexible-assignment")
async def get_flexible_agent_assignment_endpoint(
    request: FlexibleAssignmentRequest
) -> Dict[str, Any]:
    """
    Get flexible agent assignment with recommendations.
    
    This endpoint provides recommendations while emphasizing that any agent
    can work on any task. It's designed for teams that want suggestions
    but maintain flexibility in task assignment.
    
    Args:
        request: Task description and assignment preferences
    
    Returns:
        Dict containing flexible assignment recommendations
    """
    try:
        # Get flexible assignment recommendations
        flexible_assignment = await get_flexible_agent_assignment(request.task_description)
        
        # If a preferred agent is specified, add that information
        if request.preferred_agent:
            flexible_assignment["user_preference"] = {
                "preferred_agent": request.preferred_agent,
                "note": "User has specified a preferred agent. You can still assign to any agent."
            }
        
        return {
            "status": "success",
            "data": flexible_assignment,
            "message": "Flexible agent assignment recommendations generated",
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error(f"Error getting flexible agent assignment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get flexible assignment: {str(e)}")

@router.post("/agents/smart-assignment")
async def smart_agent_assignment(
    task_request: TaskRequest,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Smart agent assignment that automatically selects the best agent.
    
    This endpoint automatically assigns the task to the most suitable agent
    based on role match, performance, and current workload.
    
    Args:
        task_request: Task details
        background_tasks: FastAPI background tasks
    
    Returns:
        Dict containing automatic task assignment
    """
    try:
        # Get recommendations
        recommendations = await get_task_recommendations(task_request.description)
        recommended_agent = recommendations["recommended_agent"]
        
        # Automatically assign to recommended agent
        task_dict = task_request.dict()
        assignment = await assign_task_to_agent(recommended_agent, task_dict, force_assignment=False)
        
        return {
            "status": "success",
            "data": {
                "assignment": assignment,
                "recommendation": recommendations,
                "auto_assigned": True
            },
            "message": f"Task automatically assigned to {recommended_agent}",
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error(f"Error in smart agent assignment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")

@router.post("/workflows")
async def execute_workflow(
    workflow_request: WorkflowRequest,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Execute a complete workflow involving multiple agents.
    
    Args:
        workflow_request: Workflow definition
        background_tasks: FastAPI background tasks
    
    Returns:
        Dict containing workflow execution results
    """
    try:
        # Convert Pydantic models to dicts
        workflow_steps = []
        for step in workflow_request.steps:
            workflow_steps.append({
                "agent_type": step.agent_type,
                "task": step.task.dict()
            })
        
        # Execute workflow
        workflow_result = await run_agent_workflow(workflow_steps)
        
        # Log workflow execution
        logger.info(f"Workflow '{workflow_request.name}' executed: {workflow_result}")
        
        return {
            "status": "success",
            "data": {
                "workflow_name": workflow_request.name,
                "workflow_description": workflow_request.description,
                "execution_result": workflow_result
            },
            "message": f"Workflow '{workflow_request.name}' executed successfully",
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")

@router.get("/workflows/examples")
async def get_workflow_examples() -> Dict[str, Any]:
    """
    Get example workflows for common development tasks.
    
    Returns:
        Dict containing example workflow definitions
    """
    examples = {
        "feature_development": {
            "name": "Feature Development Workflow",
            "description": "Complete workflow for developing a new feature",
            "steps": [
                {
                    "agent_type": "architect",
                    "task": {
                        "description": "Design feature architecture",
                        "priority": "HIGH",
                        "estimated_completion": "2 hours"
                    }
                },
                {
                    "agent_type": "developer",
                    "task": {
                        "description": "Implement feature code",
                        "priority": "HIGH",
                        "estimated_completion": "4 hours"
                    }
                },
                {
                    "agent_type": "qa",
                    "task": {
                        "description": "Test feature functionality",
                        "priority": "MEDIUM",
                        "estimated_completion": "2 hours"
                    }
                },
                {
                    "agent_type": "devops",
                    "task": {
                        "description": "Deploy feature to staging",
                        "priority": "MEDIUM",
                        "estimated_completion": "1 hour"
                    }
                }
            ]
        },
        "bug_fix": {
            "name": "Bug Fix Workflow",
            "description": "Workflow for fixing reported bugs",
            "steps": [
                {
                    "agent_type": "qa",
                    "task": {
                        "description": "Reproduce and analyze bug",
                        "priority": "HIGH",
                        "estimated_completion": "1 hour"
                    }
                },
                {
                    "agent_type": "developer",
                    "task": {
                        "description": "Implement bug fix",
                        "priority": "HIGH",
                        "estimated_completion": "2 hours"
                    }
                },
                {
                    "agent_type": "qa",
                    "task": {
                        "description": "Verify bug fix",
                        "priority": "MEDIUM",
                        "estimated_completion": "1 hour"
                    }
                }
            ]
        },
        "performance_optimization": {
            "name": "Performance Optimization Workflow",
            "description": "Workflow for optimizing system performance",
            "steps": [
                {
                    "agent_type": "qa",
                    "task": {
                        "description": "Run performance tests",
                        "priority": "HIGH",
                        "estimated_completion": "2 hours"
                    }
                },
                {
                    "agent_type": "architect",
                    "task": {
                        "description": "Analyze performance bottlenecks",
                        "priority": "HIGH",
                        "estimated_completion": "3 hours"
                    }
                },
                {
                    "agent_type": "developer",
                    "task": {
                        "description": "Implement optimizations",
                        "priority": "HIGH",
                        "estimated_completion": "4 hours"
                    }
                },
                {
                    "agent_type": "qa",
                    "task": {
                        "description": "Validate performance improvements",
                        "priority": "MEDIUM",
                        "estimated_completion": "2 hours"
                    }
                }
            ]
        }
    }
    
    return {
        "status": "success",
        "data": examples,
        "message": "Example workflows retrieved successfully",
        "timestamp": asyncio.get_event_loop().time()
    }

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the CodeZX agent system.
    
    Returns:
        Dict containing system health information
    """
    try:
        # Get agent status to verify system is working
        agent_status = await get_agent_status()
        
        return {
            "status": "healthy",
            "service": "CodeZX Agent System",
            "agents_active": len(agent_status),
            "timestamp": asyncio.get_event_loop().time(),
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "CodeZX Agent System",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
            "version": "1.0.0"
        }

# Note: Exception handlers should be registered on the main FastAPI app, not the router
# This will be handled by the main application
