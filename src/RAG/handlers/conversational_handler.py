from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources


@register_handler("conversational_handler")
class ConversationalHandler(Handler):
    description = (
        "The ConversationalHandler handles general conversational questions, follow-up questions, "
        "and any prompt that refers to the conversation itself — such as asking what was said before, "
        "clarifying a previous answer, or casual greetings. It does NOT access the database."
    )

    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str, history: list | None = None) -> str:
        response = self.resources.large_llm.query(
            prompt=prompt,
            context="",
            system=(
                "You are a helpful assistant. Answer the user's question using the conversation "
                "history provided. Do not reference any database or schema."
            ),
            history=history
        )
        return response
