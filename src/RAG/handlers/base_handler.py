from abc import ABC

from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources


@register_handler("base_handler")
class Handler(ABC):
    description = "Base handler - should not be used directly."
    def __init__(self, resources: Resources):
        # Handlers get access to the agent's shared resources
        self.resources = resources

    def handle(self, prompt: str) -> str:
        pass
