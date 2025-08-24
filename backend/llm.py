import os
from openai import OpenAI
from database import log_event

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3-8b-8192")
LLM_API_KEY = (
    os.getenv("GROQ_API_KEY") if LLM_PROVIDER == "groq" else os.getenv("OPENAI_API_KEY")
)

COSTS = {
    "groq": {
        "llama3-8b-8192": {"input": 0.05, "output": 0.08},
        "llama3-70b-8192": {"input": 0.59, "output": 0.79},
    },
    "openai": {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
    },
}

def get_client() -> OpenAI:
    """Return configured OpenAI client for either Groq or OpenAI."""
    base_url = GROQ_BASE_URL if LLM_PROVIDER == "groq" else OPENAI_BASE_URL
    return OpenAI(api_key=LLM_API_KEY, base_url=base_url)

async def call_llm(messages: list, max_tokens: int = 150) -> dict:
    """Call LLM and return response with cost tracking."""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )

        usage = response.usage
        model_costs = COSTS[LLM_PROVIDER].get(
            LLM_MODEL, COSTS[LLM_PROVIDER]["llama3-8b-8192"]
        )
        cost_estimate = (
            (usage.prompt_tokens / 1_000_000) * model_costs["input"]
            + (usage.completion_tokens / 1_000_000) * model_costs["output"]
        )

        result = {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
            "cost_estimate": cost_estimate,
            "model": LLM_MODEL,
            "provider": LLM_PROVIDER,
        }

        await log_event("llm_call", result)
        return result

    except Exception as e:
        error_result = {
            "content": None,
            "error": str(e),
            "usage": None,
            "cost_estimate": 0.0,
            "model": LLM_MODEL,
            "provider": LLM_PROVIDER,
        }
        
        await log_event("llm_error", error_result)
        return error_result

def get_cost_comparison():
<<<<<<< Updated upstream
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
=======
    """Return cost comparison for different providers."""
    return COSTS 
>>>>>>> Stashed changes
