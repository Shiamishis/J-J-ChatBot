from src.LLM.utils import extract_tables_from_response, extract_sql_query
from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources

@register_handler("data_handler")
class DataHandler(Handler):
    description = (
        "The DataHandler processes user prompts that require database access. It identifies relevant tables, "
        "generates SQL queries, executes them, and formats the results into a natural language answer."
    )
    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str, history: list | None = None) -> str:
        """
        Executes the Text-to-SQL pipeline by calling LLMs directly
        from the Resources.
        """

        # 1. Identify relevant tables (Reasoning task -> Large LLM)
        relevant_tables = self._get_relevant_tables(prompt)
        print(f"[DataHandler] Tables identified: {relevant_tables}")

        if not relevant_tables:
            return "I don't know based on the available tables. The information might not be in the database."

        # 2. Generate the SQL query (High precision task -> Large LLM)
        sql_query = self._get_sql_query(prompt, relevant_tables)
        print(f"[DataHandler] SQL Generated: {sql_query}")

        if not sql_query or sql_query.strip().lower() == "i don't know":
            return "I don't know based on the available table schema."

        # 3. Execute the query via the Resources's database service
        try:
            sql_results = self.resources.database_service.execute_query(sql_query)
        except Exception as e:
            return f"Error executing database query: {e}"

        # 4. Generate final answer (Formatting task -> Small LLM)
        final_answer = self.resources.small_llm.query(
            prompt=f"Original question: {prompt}\nSQL Results: {sql_results}",
            context=f"Schema context: {self.resources.schema_context}",
            system="Provide a clear, natural language answer based on the SQL results provided.",
            history=history
        )

        return final_answer

    def _get_relevant_tables(self, prompt: str) -> set[str]:
        """Directly uses the Large LLM to select tables."""
        # Directly calling agent.large_llm.query
        response = self.resources.large_llm.query(
            prompt=f"Given the question: '{prompt}', which tables are relevant?",
            context=f"Database Tables: {self.resources.graph.get_nodes()}\n{self.resources.schema_context}",
            system="Return only a Python-style list of relevant table names."
        )

        tables = extract_tables_from_response(response, self.resources.graph.get_nodes())

        if not tables:
            return set()

        # Use Resources's graph for join path finding
        if len(tables) > 1:
            try:
                return self.resources.graph.find_steiner_tree(set(tables))
            except Exception as e:
                print(f"Steiner tree fallback: {e}")
                return set(tables)

        return set(tables)

    def _get_sql_query(self, prompt: str, relevant_tables: set[str]) -> str:
        """Directly uses the Large LLM to generate SQL."""
        # Directly calling agent.large_llm.query
        response = self.resources.large_llm.query(
            prompt=f"Write a SQLite query for: '{prompt}'. Use tables: {relevant_tables}",
            context=f"Detailed Schema: {self.resources.schema_context}",
            system="You are an expert SQL generator. Return only the SQL query code."
        )
        return extract_sql_query(response)
