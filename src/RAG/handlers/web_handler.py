from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources
@register_handler("web_handler")
class WebHandler(Handler):
    def __init__(self, resources: Resources):
        super().__init__(resources)
        self.description = (
            'The WebHandler is responsible for processing user prompts that require web search or external API calls. '
            'It can fetch real-time information, perform searches, and integrate data from the web to provide '
            'up-to-date responses.'
        )
    def handle(self, prompt: str, history: list | None = None) -> str:
        """
        Handles prompts that require web search or external API calls.
        """
        # TODO: Implement web search or external API call
        return "I don't know based on the available web search or external API call results."