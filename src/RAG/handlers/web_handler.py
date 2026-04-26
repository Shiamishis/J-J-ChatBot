from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler

@register_handler("web_handler")
class WebHandler(Handler):
    def __init__(self, data_source):
        self.description = (
            'The WebHandler is responsible for processing user prompts that require web search or external API calls. '
            'It can fetch real-time information, perform searches, and integrate data from the web to provide '
            'up-to-date responses.'
        )

    def handle(self, prompt: str) -> str:
        pass