from abc import ABC, abstractmethod
from src.RAG.agent import RAGOrchestrator
from src.RAG.handlers.registry import register_handler
from src.LLM.query import query_llm

@register_handler("base_handler")
class Handler(ABC):
    description = "Base handler - should not be used directly."
    def __init__(self, orchestrator: RAGOrchestrator):
        # Handlers get access to the agent's shared resources
        self.orchestrator = orchestrator

    def handle(self, prompt: str) -> str:
        pass
