from __future__ import annotations

from src.RAG.resources import Resources
from src.RAG.router.intent_router import route_intent


class RAGOrchestrator:

    def __init__(self, resources: Resources):
        self.resources = resources

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    def prompt(self, prompt: str, history: list | None = None) -> str:
        intent = route_intent(prompt, self.resources.schema_context, self)
        print(f"Determined intent: {intent}")

        from src.RAG.handlers.registry import get_handler
        handler = get_handler(intent, self.resources)
        print("Instantiated handler:", handler.__class__.__name__)
        response = handler.handle(prompt, history or [])
        print(f"Handler response: {response}")

        return response
