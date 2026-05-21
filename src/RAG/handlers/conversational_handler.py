from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources


@register_handler("conversational_handler")
class ConversationalHandler(Handler):
    description = (
        "Handles social interactions, meta-commentary about the conversation, and general conceptual "
        "definitions that do not require specific data access. "
        "Use this for (Positive): Greetings ('Hello'), small talk ('How are you?'), references to "
        "previous messages ('What did I just ask?'), requests for simpler explanations ('Explain that "
        "like I'm five'), and general knowledge definitions ('What is a SQL join?' or 'What does CAGR stand for?'). "
        "Do NOT use this for (Negative): Questions about specific internal data values ('What was our revenue?'), "
        "questions about how to use a specific internal report ('How do I filter this dashboard?'), "
        "or requests for schema details ('What columns are in the users table?')."
    )

    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str, history: list | None = None) -> str:
        response = self.resources.large_llm.query(
            prompt=prompt,
            context="",
            system=(
                "You are a helpful data assistant. Always respond in plain text only. Never use markdown, "
                "code blocks, bullet points with symbols, or any formatting. Just use clear plain sentences. "
                "Answer the user's question using the conversation history provided. Do not reference any database or schema."
            ),
            history=history
        )
        return response
