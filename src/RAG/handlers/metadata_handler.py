from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENTATION_PATH = os.path.join(PROJECT_ROOT, "data", "documentation.txt")

@register_handler("metadata_handler")
class MetaDataHandler(Handler):
    description = (
        'The MetaDataHandler is responsible for processing user prompts that require database schema information. '
        'It can provide details about table structures, relationships as well as information about the schema and '
        'definitions.'
    )
    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str, history: list | None = None) -> str:
        """
        Handles prompts that ask for metadata information about the database schema.
        """
        response = self.resources.large_llm.query(
            prompt=f"Given the question: '{prompt}', provide relevant metadata information about the database schema.",
            context=f"Database Tables: {self.resources.graph.get_nodes()}\n{self.resources.schema_context}",
            system="You are a helpful data assistant. Always respond in plain text only. Never use markdown, code blocks, bullet points with symbols, or any formatting. Just use clear plain sentences. Answer based on the database schema information provided.",
            history=history
        )
        return response
