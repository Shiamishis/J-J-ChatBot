from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler

@register_handler("metadata_handler")
class MetaDataHandler(Handler):
    description = (
        'The MetaDataHandler is responsible for processing user prompts that require database schema information. '
        'It can provide details about table structures, relationships as well as information about the schema and '
        'definitions.'
    )
    def __init__(self, orchestrator):
        super().__init__(orchestrator)

    def handle(self, prompt: str) -> str:
        """
        Handles prompts that ask for metadata information about the database schema.
        """
        response = self.orchestrator.large_llm.query(
            prompt=f"Given the question: '{prompt}', provide relevant metadata information about the database schema.",
            context="Database Tables: {self.orchestrator.graph.get_nodes()}\n{self.orchestrator.schema_context}",
            system="Provide a clear and concise answer based on the database schema information provided."
        )
        return response
