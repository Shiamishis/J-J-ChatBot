from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources


@register_handler("ticket_handler")
class TicketHandler(Handler):
    description = ("The TicketHandler is responsible for creating tickets based on user prompts."
                   "The tickets should be ready to be sent to an expert on the respective field, "
                   "e.g. a database expert, a web search expert, etc.")

    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str, history: list | None = None) -> str:
        ticket = self.resources.large_llm.query(
            prompt=f"Write a support ticket email body for the following user request: '{prompt}'. ",
            context="",
            system=(
                "You are a support ticket writer. Your job is to write the body of a support email "
                "that a user can copy and paste directly to send to an expert. "
                "Write in first person as the user. "
                "Do not describe the ticket or explain what it should contain. "
                "Do not include greetings, sign-offs, or subject lines. "
                "Do not use markdown, bullet points, or formatting symbols. "
                "Just write the plain text email body, ready to send. "
                "Be specific, concise, and include all relevant context from the conversation history."
            ),
            history=history
        )
        return ticket
