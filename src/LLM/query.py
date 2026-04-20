from src.LLM.llms import get_llm
import os

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Use the provided SQL result/context to answer the user's question. If you don't know the answer, say you don't know."

def query_llm(prompt: str, context: str, llm_name: str = "groq", system: str = DEFAULT_SYSTEM_PROMPT,  **kwargs) -> str:
    """
    Query a free-tier LLM via Groq's OpenAI-compatible endpoint.

    Required environment variable:
    - `GROQ_API_KEY`

    Optional environment variable:
    - `GROQ_MODEL` (default: `llama3-8b-8192`)
    """
    api_key = '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'
    if not api_key:
        return (
            "LLM not configured. Please set environment variable `GROQ_API_KEY` "
            "to a valid Groq API key."
        )
    try:
        llm_instance = get_llm(llm_name, api_key=api_key, **kwargs)
        return llm_instance.query(prompt, context, system)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error querying LLM: {e}"
