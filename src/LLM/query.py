# This file is not used in the current implementation
from src.LLM.llms import get_llm
import os

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Use the provided SQL result/context to answer the user's question. If you don't know the answer, say you don't know."


def query_llm(prompt: str, context: str, llm_name: str = "swissai", system: str = DEFAULT_SYSTEM_PROMPT,
              **kwargs) -> str:
    """
    Query an LLM via the Swiss AI Research Platform.

    Required environment variable:
    - `SWISSAI_API_KEY`
    """
    # It's best practice to grab this from os.getenv rather than hardcoding!
    api_key = os.getenv("SWISSAI_API_KEY", "your_actual_swiss_ai_key_here")

    if not api_key or api_key == "your_actual_swiss_ai_key_here":
        return (
            "LLM not configured. Please set the `SWISSAI_API_KEY` variable."
        )

    try:
        # Note: You can pass a different model in kwargs if you don't want the default Llama-3.3-70B
        llm_instance = get_llm(llm_name, api_key=api_key, **kwargs)
        return llm_instance.query(prompt, context, system)

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error querying LLM: {e}"