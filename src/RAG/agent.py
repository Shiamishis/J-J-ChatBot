from __future__ import annotations

from src.RAG.databaseservice import DatabaseService
from src.RAG.graph import Graph
from src.LLM.llms import LLM, get_llm
from src.RAG.router.intent_router import route_intent
from src.LLM.history import ConversationHistory


class RAGOrchestrator:

    def __init__(self, small_llm: LLM, large_llm: LLM):
        self.small_llm = small_llm
        self.large_llm = large_llm
        self.history = ConversationHistory()

        self.database_service = DatabaseService()
        nodes, edges = self.database_service.get_schema_metadata()
        self.graph = Graph(nodes, edges)
        self.schema_context = (
            self.database_service.load_schema_context_file()
            or self.database_service.build_and_save_schema_context_file(sample_rows_per_table=2)
        )

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    def prompt(self, prompt: str) -> str:
        intent = route_intent(prompt, self.schema_context, self)
        print(f"Determined intent: {intent}")

        from src.RAG.handlers.registry import get_handler
        handler = get_handler(intent, self)
        print("Instantiated handler:", handler.__class__.__name__)
        response = handler.handle(prompt)
        print(f"Handler response: {response}")

        self.history.add_message("user", prompt)
        self.history.add_message("assistant", response)

        return response
