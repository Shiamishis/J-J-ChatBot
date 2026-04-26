from src.LLM.llms import get_llm
import os


def query_llm(prompt: str, context: str, llm_name: str, system: str,  **kwargs) -> str:
    """
    Query a free-tier LLM via Groq's OpenAI-compatible endpoint.

    Required environment variable:
    - `GROQ_API_KEY`

    Optional environment variable:
    - `GROQ_MODEL` (default: `llama3-8b-8192`)
    """
    api_key = os.environ.get("GROQ_API_KEY")
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
