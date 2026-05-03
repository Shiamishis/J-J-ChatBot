# src/RAG/utils/router.py

def route_intent(prompt: str, schema_context: str, orchestrator) -> str:
    """
    Analyzes the prompt and returns the intent name.
    """
    from src.RAG.handlers.registry import get_all_handlers, get_all_handler_names
    handlers = get_all_handlers()
    handler_names = get_all_handler_names()
    handler_names_options = ", ".join(handler_names)
    description_text = "\n".join([f"- {handler.__name__}: {handler.description}" for handler in handlers])
    system_prompt = (
        "You are the Intelligent Routing Core for a RAG Chatbot. Your sole purpose is to "
        "classify the user's intent into the correct processing bucket based on their prompt "
        "and the available database schema.\n\n"

        "### AVAILABLE HANDLERS AND THEIR ROLES:\n"
        f"{description_text}\n\n"
        "### INSTRUCTIONS:\n"
        f"Choose from the following options: {handler_names_options}.\n"
        "Your answer should be a single word corresponding to the handler name that best matches the user's intent. "
        "Do not provide any explanation or additional text."
    )

    # We call the LLM directly here
    intent = orchestrator.resources.small_llm.query(
        prompt=prompt,
        context=schema_context,
        system=system_prompt
    )

    return intent.strip().lower()
