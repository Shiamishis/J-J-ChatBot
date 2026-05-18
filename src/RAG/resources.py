from src.LLM.llms import get_llm
from src.RAG.databaseservice import DatabaseService
from src.RAG.graph import Graph
from pathlib import Path
import json


class Resources:
    def __init__(self, api_key: str):
        # self.small_llm = get_llm("groq", api_key=api_key, model="llama-3.1-8b-instant")
        # self.large_llm = get_llm("groq", api_key=api_key, model="llama-3.3-70b-versatile")
        self.small_llm = get_llm("swissai", api_key=api_key, model="swiss-ai/Apertus-8B-Instruct-2509")
        self.large_llm = get_llm("swissai", api_key=api_key, model="meta-llama/Llama-3.3-70B-Instruct")
        self.database_service = DatabaseService()
        self.graph = self.build_graph()
        self.schema_context = self.database_service.load_schema_context_file()
        print("Resources initialized with small LLM, large LLM, database service, graph, and schema context.")


    def build_graph(self):
        ROOT_DIR = Path(__file__).parent.parent.parent
        graph_file = ROOT_DIR / "data" / "metadata_graph_manual.json"
        with open(graph_file, "r") as f:
            graph_data = json.load(f)
        nodes = graph_data["nodes"]
        edges = [(e["source_table"], e["target_table"]) for e in graph_data["edges"]]
        return Graph(nodes, edges)

    def get_small_llm(self):
        return self.small_llm

    def get_large_llm(self):
        return self.large_llm

    def get_database_service(self):
        return self.database_service

    def get_graph(self):
        return self.graph

    def get_schema_context(self):
        return self.schema_context

    def close(self):
        # If any of the resources require cleanup, do it here
        print("Closing resources...")
        self.small_llm.close()
        self.large_llm.close()
        print("Resources closed.")