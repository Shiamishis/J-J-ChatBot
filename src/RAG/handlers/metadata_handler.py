from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources

@register_handler("metadata_handler")
class MetaDataHandler(Handler):
    description = (
        'The MetaDataHandler is responsible for processing user prompts that require database schema information. '
        'It can provide details about table structures, relationships as well as information about the schema and '
        'definitions.'
    )
    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str) -> str:
        """
        Handles prompts that ask for metadata information about the database schema.
        """
        response = self.resources.large_llm.query(
            prompt=f"Given the question: '{prompt}', provide relevant metadata information about the database schema.",
            context="Database Tables: {self.resources.graph.get_nodes()}\n{self.resources.schema_context}",
            system="Provide a clear and concise answer based on the database schema information provided."
        )
        return response
