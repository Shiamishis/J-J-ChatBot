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
            prompt=f"Create a ticket based on the following user request: '{prompt}'. "
                   "The ticket should be concise and contain all necessary information for an expert to understand "
                   "the issue and take action. ",
            context="",
            system="You are a helpful assistant that creates clear and concise tickets for experts. Always respond in "
                   "plain text only. Never use markdown, code blocks, bullet points with symbols, or any formatting. "
                   "Just use clear plain sentences. Create a ticket based on the user request and conversation "
                   "history provided.",
            history=history
        )
        return ticket
