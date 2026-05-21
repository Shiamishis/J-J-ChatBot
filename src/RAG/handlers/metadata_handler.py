from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources

import os


@register_handler("metadata_handler")
class MetaDataHandler(Handler):
    description = (
        "Provides technical information about the database structure, architecture, and data organization. "
        "Use this for: Table and column discovery ('What tables are available?'), "
        "relationship questions ('How is the orders table connected to the customers table?'), "
        "and data types ('Is the price column an integer or a float?'). "
        "Do NOT use this for: Retrieving actual row data ('What is the price of item #101?'), "
        "social greetings ('Hi there'), or external web searches ('What is the latest SQL version?')."
    )
    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str, history: list | None = None, method: str = "") -> str:
        """
        Handles prompts that ask for metadata information about the database schema.
        """
        response = self.resources.large_llm.query(
            prompt=f"Given the question: '{prompt}', provide relevant metadata information about the database schema.",
            context=f"Database Tables: {self.resources.graph.get_nodes()}\n{self.resources.schema_context}",
            system="You are a helpful data assistant. Always respond in plain text only. Never use markdown, "
                   "code blocks, bullet points with symbols, or any formatting. Just use clear plain sentences. "
                   "Answer based on the database schema information provided.",
            history=history
        )
        return response
