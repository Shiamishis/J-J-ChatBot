from __future__ import annotations

from src.RAG.databaseservice import DatabaseService
from src.LLM.query import query_llm
from src.RAG.graph import Graph
from src.LLM.utils import extract_tables_from_response, extract_sql_query


class RAGAgent:
    """

    """

    def __init__(self):
        self.database_service = DatabaseService()
        nodes, edges = self.database_service.get_schema_metadata()
        self.graph = Graph(nodes, edges)

    async def initialize(self) -> None:
        # TODO potentially add init steps here
        pass
    async def close(self) -> None:
        # TODO potentially add cleanup steps here
        pass
    def query(self, prompt: str, context: str) -> str:
        return query_llm(prompt, context)

    def get_context(self, prompt: str) -> str:
        tables_response = query_llm(
            prompt=f"Given the user's prompt: '{prompt}', "
                   f"which tables in the database are relevant for answering the question? "
                   f"Return a list of relevant table names.",
            context=f"These all the tables to choose from: {self.graph.get_nodes()}",
            system="You are a helpful assistant. Use the provided list of tables to determine which ones are relevant "
                   "to the user's question. Return only the names of the relevant tables in a list format. If no "
                   "tables are relevant, return an empty list."
        )
        tables = extract_tables_from_response(tables_response, self.graph.get_nodes())

        relevant_tables = self.graph.find_steiner_tree(tables)
        print(f"Identified relevant tables: {relevant_tables}")

        sql_query_response = query_llm(
            prompt=f"Given the user's prompt: '{prompt}', and the following relevant tables: {relevant_tables}, "
                   f"write an SQL query that retrieves the necessary information to answer the user's question."
                   f"Your response should be only the SQL query without any explanations.",
            context=f"You have access to the following tables with their respective columns: "
                    f"{self.database_service.retrieve_schema_for_prompt(relevant_tables)}",
            system="You are a helpful assistant. Use the provided list of relevant tables and their columns to write "
                   "an SQL query that answers the user's question. Only use the tables provided in the context. If "
                   "you don't know how to answer the question with SQL, say you don't know."
        )
        sql_query = extract_sql_query(sql_query_response)
        print(f"Generated SQL Query: {sql_query}")
        sql_results = self.database_service.execute_query(sql_query)

        final_response = query_llm(
            prompt=f"Given the user's original question: '{prompt}', and the following SQL query results: {sql_results}, "
                   f"provide a final answer to the user's question based on the SQL results.",
            context=f"You have access to the following SQL query results: {sql_results}",
            system="You are a helpful assistant. Use the provided SQL query results to answer the user's original "
                   "question. If you don't know the answer, say you don't know."
        )
        return final_response

    def prompt(self, prompt: str) -> str:
        context = self.get_context(prompt)
        response = self.query(prompt, context)
        return response
