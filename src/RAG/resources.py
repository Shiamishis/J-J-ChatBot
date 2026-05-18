from pathlib import Path

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
        self.training_contexts = self._load_training_contexts()
        print(
            "Resources initialized with small LLM, large LLM, database service, "
            "graph, schema context, and training contexts."
        )

    @staticmethod
    def _load_training_contexts() -> dict[str, str]:
        """
        Load per-dashboard training material text files produced by
        scripts/parse_training_materials.py. Returns a dict mapping
        slug -> text. Returns an empty dict if no files exist yet.
        """
        # this file is at <root>/src/RAG/resources.py
        root = Path(__file__).resolve().parent.parent.parent
        context_dir = root / "data" / "training_context"
        if not context_dir.exists():
            print(f"  (no training_context dir at {context_dir}, skipping)")
            return {}
        contexts: dict[str, str] = {}
        for path in sorted(context_dir.glob("*.txt")):
            try:
                contexts[path.stem] = path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  (failed to load {path.name}: {e})")
        if contexts:
            print(f"  Loaded {len(contexts)} dashboard training context(s): {list(contexts.keys())}")
        else:
            print("  (training_context dir is empty; run scripts/parse_training_materials.py)")
        return contexts


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