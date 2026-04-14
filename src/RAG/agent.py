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
        self.schema_context = (
            self.database_service.load_schema_context_file()
            or self.database_service.build_and_save_schema_context_file(sample_rows_per_table=2)
        )

    async def initialize(self) -> None:
        # TODO potentially add init steps here
        pass

    async def close(self) -> None:
        # TODO potentially add cleanup steps here
        pass

    @staticmethod
    def query_llm(prompt, context, system):
        return query_llm(prompt=prompt, context=context, system=system)

    def get_relevant_tables(self, prompt: str, method: str = "steiner") -> set[str]:
        tables_response = self.query_llm(
            prompt=f"Given the user's prompt: '{prompt}', "
                   f"which tables in the database are relevant for answering the question? "
                   f"Return a list of relevant table names.",
            context=(
                f"These are all the tables to choose from: {self.graph.get_nodes()}\n\n"
                f"{self.schema_context}"
            ),
            system="You are a table-selection assistant. Use only the provided schema context. "
                   "Return only a Python-style list of relevant table names (e.g. ['FACT_Sales', 'DIM_Time']). "
                   "If the question asks about refresh times, data lineage, pipeline runs, or metadata that is not "
                   "represented in table columns, return an empty list []."
        )
        print(f"Tables response: {tables_response}")
        tables = extract_tables_from_response(tables_response, self.graph.get_nodes())
        if not tables:
            print("No tables identified by table selection step.")
            return set()
        if method == "steiner" and len(tables) > 1:
            return self.get_steiner_tree(set(tables))
        # TODO potentially add other methods, e.g. based on schema embeddings similarity or LLM ranking of join paths
        return set(tables)

    def get_steiner_tree(self, tables: set[str]) -> set[str]:
        if len(tables) <= 1:
            return tables
        try:
            return self.graph.find_steiner_tree(tables)
        except Exception as e:
            print(f"Steiner tree fallback triggered: {e}")
            return tables

    def get_sql_query(self, prompt: str, relevant_tables: set[str]) -> str:
        sql_query_response = self.query_llm(
            prompt=f"Given the user's prompt: '{prompt}', and the following relevant tables: {relevant_tables}, "
                   f"write an SQL query that retrieves the necessary information to answer the user's question."
                   f"Your response should be only the SQL query without any explanations.",
            context=(
                "You have access to the following single schema context file content:\n"
                f"{self.schema_context}"
            ),
            system="You are a SQL generator for SQLite. "
                   "Use only tables and columns shown in context. "
                   "If the user asks for refresh time, lineage, or operational metadata not present in context, "
                   "respond exactly with: I don't know. "
                   "Do not guess. Return only SQL or exactly: I don't know."
        )
        sql_query = extract_sql_query(sql_query_response)
        return sql_query

    def execute_sql_query(self, sql_query: str) -> list[dict[str, str]]:
        sql_results = self.database_service.execute_query(sql_query)
        return sql_results

    def prompt(self, prompt: str) -> str:
        # TODO extend this method to answer questions without SQL, for example when asked a question regarding
        #  definitions we would need to first determine the type of question and then go through with the

        #  LLM-pipeline get relevant tables
        relevant_tables = self.get_relevant_tables(prompt, method="steiner")
        print(f"Relevant tables identified: {relevant_tables}")
        if not relevant_tables:
            return "I don't know based on the available database tables. The question likely requires refresh/pipeline metadata that is not stored in this DB."
        # generate SQL query
        sql_query = self.get_sql_query(prompt, relevant_tables)
        print(f"SQL query generated: {sql_query}")
        if not sql_query or sql_query.strip().lower() == "i don't know":
            return "I don't know based on the available table schema and data."
        # execute SQL query
        sql_results = self.execute_sql_query(sql_query)
        print(f"SQL query executed, results obtained: {sql_results}")
        # final response
        final_response = self.query_llm(
            prompt=f"Given the user's original question: '{prompt}', and the following SQL query results: {sql_results}, "
                   f"provide a final answer to the user's question based on the SQL results.",
            context=(
                f"You have access to the following SQL query results: {sql_results}\n\n"
                f"Schema context:\n{self.schema_context}"
            ),
            system="You are a helpful assistant. Use the provided SQL query results to answer the user's original "
                   "question. If you don't know the answer, say you don't know."
        )
        return final_response
