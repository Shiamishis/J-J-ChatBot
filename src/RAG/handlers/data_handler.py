from src.LLM.utils import extract_tables_from_response, extract_sql_query
from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources

@register_handler("data_handler")
class DataHandler(Handler):
    description = (
        "The primary engine for retrieving specific values, aggregates, and records from the internal "
        "database via SQL execution. "
        "Use this for: Questions requiring hard numbers ('How many new signups did we have yesterday?'), "
        "list-based requests ('Show me the top 5 products by profit'), and trend analysis ('Did our sales "
        "grow between January and March?'). "
        "Do NOT use this for: High-level schema questions ('What tables do we have?'), "
        "UI help ('Where is the sign-up report?'), or general definitions ('What is a signup?')."
    )
    def __init__(self, resources: Resources):
        super().__init__(resources)

    def handle(self, prompt: str, history: list | None = None) -> str:
        """
        Executes the Text-to-SQL pipeline by calling LLMs directly
        from the Resources.
        """

        relevant_tables = self._get_relevant_tables(prompt)
        print(f"[DataHandler] Tables identified: {relevant_tables}")

        if not relevant_tables:
            return "I don't know based on the available tables. The information might not be in the database."

        full_prompt = f"Write a SQLite query for: '{prompt}'. Use tables: {relevant_tables}"
        sql_query = self._get_sql_query(full_prompt)
        print(f"[DataHandler] SQL Generated: {sql_query}")

        if not sql_query or sql_query.strip().lower() == "i don't know":
            return "I don't know based on the available table schema."

        # sql_query = self._get_sql_query(prompt)
        # print(f"[DataHandler] SQL Generated: {sql_query}")
        # if not sql_query or sql_query.strip().lower() == "i don't know":
        #     return "I don't know based on the available table schema."

        try:
            sql_results = self.resources.database_service.execute_query(sql_query)
        except Exception as e:
            return f"Error executing database query: {e}"

        final_answer = self.resources.large_llm.query(
            prompt=f"Question: {prompt}\nData: {sql_results}",
            system=(
                "Translate the provided data into a clear, natural language answer. "
                "Rules: 1. Use the names provided in the data, not IDs. "
                "2. If the data contains multiple rows, list them all. "
                "3. Do not mention SQL, tables, or technical terms. "
                "4. If the data is empty, say 'No data found'."
            ),
            context=f"Schema Context: {self.resources.schema_context}"
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

    def _get_sql_query(self, prompt: str) -> str:
        """Directly uses the Large LLM to generate SQL."""
        # Directly calling agent.large_llm.query
        system_instruction = (
            """
            SYSTEM: 
            You are an expert SQLite Generator. You will be provided with a Database Schema. 
            Your goal is to return ONLY the SQL code, with no explanation or markdown.
            Never return raw IDs (like brand_id or account_id) to the user. 
            Always JOIN the corresponding DIMENSION table to retrieve the human-readable 'brand_name', 'account_name', or 'geo_name'.
            
            ### CRITICAL SQL RULES:
            1. SQLITE LIMITATIONS: SQLite does not support CORR(), MEDIAN(), or PERCENTILE(). 
               - For correlation, you must select the raw values or use the manual Pearson formula.
            
            ### EXECUTION:
            Based on the Schema provided in the Context, write the SQLite query for the user's prompt."""
        )
        response = self.resources.large_llm.query(
            prompt=prompt,
            context=f"Detailed Schema: {self.resources.schema_context}",
            system=system_instruction
        )
        return extract_sql_query(response)
