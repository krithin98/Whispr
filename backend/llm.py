import os
import json
from openai import OpenAI
from database import log_event

# Configuration
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"

# Default to Groq for cost efficiency
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3-8b-8192")
LLM_API_KEY = os.getenv("GROQ_API_KEY") if LLM_PROVIDER == "groq" else os.getenv("OPENAI_API_KEY")

# Cost tracking (per 1M tokens)
COSTS = {
    "groq": {
        "llama3-8b-8192": {"input": 0.05, "output": 0.08},
        "llama3-70b-8192": {"input": 0.59, "output": 0.79},
    },
    "openai": {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
    }
}

def get_client():
    """Return configured OpenAI client for either Groq or OpenAI."""
    base_url = GROQ_BASE_URL if LLM_PROVIDER == "groq" else OPENAI_BASE_URL
    return OpenAI(
        api_key=LLM_API_KEY,
        base_url=base_url
    )

async def call_llm(messages: list, max_tokens: int = 150) -> dict:
    """
    Call LLM and return response with cost tracking.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens for response
    
    Returns:
        dict with 'content', 'usage', 'cost_estimate', 'model'
    """
    try:
        client = get_client()
        
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        # Calculate cost estimate
        usage = response.usage
        model_costs = COSTS[LLM_PROVIDER].get(LLM_MODEL, COSTS[LLM_PROVIDER]["llama3-8b-8192"])
        cost_estimate = (
            (usage.prompt_tokens / 1_000_000) * model_costs["input"] +
            (usage.completion_tokens / 1_000_000) * model_costs["output"]
        )
        
        result = {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            },
            "cost_estimate": round(cost_estimate, 6),
            "model": f"{LLM_PROVIDER}/{LLM_MODEL}"
        }
        
        # Log the LLM call for analytics
        await log_event("llm_call", {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "cost_estimate": result["cost_estimate"],
            "response_length": len(result["content"])
        })
        
        return result
        
    except Exception as e:
        # Log error for debugging
        await log_event("llm_error", {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "error": str(e)
        })
        raise e

def get_cost_comparison():
    """Return cost comparison for different models."""
    return {
        "current": {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "costs": COSTS[LLM_PROVIDER].get(LLM_MODEL, COSTS[LLM_PROVIDER]["llama3-8b-8192"])
        },
        "alternatives": {
            "groq_llama3_70b": COSTS["groq"]["llama3-70b-8192"],
            "openai_gpt4o_mini": COSTS["openai"]["gpt-4o-mini"],
            "openai_gpt4o": COSTS["openai"]["gpt-4o"]
        }
    } 
