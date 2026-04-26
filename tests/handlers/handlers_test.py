import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

# Import registry first so handler autodiscovery runs before class imports.
from src.RAG.handlers import registry as _registry  # noqa: F401
from src.RAG.handlers.data_handler import DataHandler
from src.RAG.handlers.metadata_handler import MetaDataHandler
from src.RAG.handlers.registry import get_handler


class TestDataHandler(unittest.TestCase):
    def _build_orchestrator(self) -> SimpleNamespace:
        orchestrator = SimpleNamespace()
        orchestrator.large_llm = MagicMock()
        orchestrator.small_llm = MagicMock()
        orchestrator.database_service = MagicMock()
        orchestrator.graph = MagicMock()
        orchestrator.schema_context = "mock schema context"
        orchestrator.graph.get_nodes.return_value = ["sales", "customers"]
        return orchestrator

    def test_handle_returns_final_answer_for_valid_pipeline(self):
        orchestrator = self._build_orchestrator()
        orchestrator.large_llm.query.side_effect = [
            "Relevant tables: sales and customers",
            "```sql\nSELECT COUNT(*) AS total FROM sales;\n```",
        ]
        orchestrator.graph.find_steiner_tree.return_value = {"sales", "customers"}
        orchestrator.database_service.execute_query.return_value = [{"total": 42}]
        orchestrator.small_llm.query.return_value = "The total number of sales is 42."

        handler = DataHandler(orchestrator)
        response = handler.handle("How many sales are in the database?")

        self.assertEqual(response, "The total number of sales is 42.")
        orchestrator.database_service.execute_query.assert_called_once_with(
            "SELECT COUNT(*) AS total FROM sales;"
        )
        orchestrator.small_llm.query.assert_called_once()

    def test_handle_returns_i_dont_know_when_no_relevant_tables(self):
        orchestrator = self._build_orchestrator()
        orchestrator.large_llm.query.return_value = "No relevant table found."

        handler = DataHandler(orchestrator)
        response = handler.handle("Tell me about weather forecasts.")

        self.assertIn("I don't know", response)
        orchestrator.database_service.execute_query.assert_not_called()

    def test_get_relevant_tables_falls_back_if_steiner_tree_fails(self):
        orchestrator = self._build_orchestrator()
        orchestrator.large_llm.query.return_value = "Relevant tables: sales, customers"
        orchestrator.graph.find_steiner_tree.side_effect = RuntimeError("graph error")

        handler = DataHandler(orchestrator)
        tables = handler._get_relevant_tables("Need joined sales/customer data")

        self.assertEqual(tables, {"sales", "customers"})

    def test_handle_returns_error_message_if_query_execution_fails(self):
        orchestrator = self._build_orchestrator()
        orchestrator.large_llm.query.side_effect = [
            "Relevant tables: sales",
            "SELECT COUNT(*) FROM sales;",
        ]
        orchestrator.database_service.execute_query.side_effect = RuntimeError(
            "database unavailable"
        )

        handler = DataHandler(orchestrator)
        response = handler.handle("How many sales are there?")

        self.assertIn("Error executing database query", response)
        self.assertIn("database unavailable", response)


class TestMetaDataHandler(unittest.TestCase):
    def test_handle_delegates_to_large_llm_and_returns_response(self):
        orchestrator = SimpleNamespace()
        orchestrator.large_llm = MagicMock()
        orchestrator.large_llm.query.return_value = "Table sales contains order metrics."
        orchestrator.graph = MagicMock()
        orchestrator.graph.get_nodes.return_value = ["sales"]
        orchestrator.schema_context = "schema context"

        handler = MetaDataHandler(orchestrator)
        response = handler.handle("What columns exist in sales?")

        self.assertEqual(response, "Table sales contains order metrics.")
        orchestrator.large_llm.query.assert_called_once()


class TestHandlerRegistry(unittest.TestCase):
    def test_get_handler_falls_back_to_base_handler_for_unknown_intent(self):
        handler = get_handler("unknown_intent", agent=SimpleNamespace())
        self.assertEqual(handler.__class__.__name__, "Handler")

