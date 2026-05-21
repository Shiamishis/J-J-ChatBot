# src/RAG/utils/router.py

def extract_handler_from_response(response: str, handler_names: list) -> str:
    """
    Extracts the handler name from the LLM response. It checks if any of the handler names are present in the response.
    If a handler name is found, it returns that handler name. Otherwise, it returns "unknown_handler".
    """
    response_lower = response.lower()
    for handler_name in handler_names:
        if handler_name.lower() in response_lower:
            return handler_name
    # in case no handler is identified we do a more loose matching to see if we can find any handler name in the
    # response, even if it's not an exact match
    for handler_name in handler_names:
        # we strip the underscore and all the spaces from the response
        response_stripped = response_lower.replace("_", "").replace(" ", "")
        handler_name_stripped = handler_name.lower().replace("_", "").replace(" ", "")
        if handler_name_stripped in response_stripped:
            return handler_name
    return "unknown_handler"

def route_intent(prompt: str, schema_context: str, orchestrator) -> str:
    """
    Analyzes the prompt and returns the intent name.
    """
    if "create ticket" in prompt.lower():
        return "ticket_handler"
    from src.RAG.handlers.registry import get_all_handlers, get_all_handler_names
    handlers = get_all_handlers()
    handler_names = get_all_handler_names()
    handler_names_options = ", ".join(handler_names)
    description_text = "\n".join([f"- {handler.__name__}: {handler.description}" for handler in handlers])
    system_prompt = (
        "You are the Intelligent Routing Core for a RAG Chatbot. Your sole purpose is to "
        "classify the user's intent into the correct processing bucket based on their prompt "
        "and the available database schema.\n\n"
        "### DATABASE SCHEMA:\n"
        "{schema_context}\n\n"
        "### AVAILABLE HANDLERS AND THEIR ROLES:\n"
        f"{description_text}\n\n"
        "### INSTRUCTIONS:\n"
        f"Choose from the following options: {handler_names_options}.\n"
        "Your answer should be a single word corresponding to the handler name that best matches the user's intent. "
        "Do not provide any explanation or additional text. Use the database schema to inform your decision, "
        "and ensure that you select the handler that is most appropriate for processing the user's request."
    )

    # We call the LLM directly here
    intent = orchestrator.resources.large_llm.query(
        prompt=prompt,
        context="",
        system=system_prompt
    )

    handler = extract_handler_from_response(intent, handler_names)

    return intent.strip().lower()
