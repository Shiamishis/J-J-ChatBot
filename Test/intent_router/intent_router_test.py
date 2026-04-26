import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.RAG.router.intent_router import route_intent


class DummyDataHandler:
    description = "Handles SQL/data retrieval prompts."


class DummyMetaDataHandler:
    description = "Handles schema and metadata prompts."


class DummyWebHandler:
    description = "Handles web-search and external information prompts."


class TestIntentRouter(unittest.TestCase):
    @patch("src.RAG.handlers.registry.get_all_handler_names")
    @patch("src.RAG.handlers.registry.get_all_handlers")
    def test_route_intent_builds_system_prompt_and_normalizes_output(
        self,
        mock_get_all_handlers,
        mock_get_all_handler_names,
    ):
        mock_get_all_handlers.return_value = [DummyDataHandler, DummyMetaDataHandler]
        mock_get_all_handler_names.return_value = ["data_handler", "metadata_handler"]

        orchestrator = SimpleNamespace()
        orchestrator.small_llm = SimpleNamespace()
        captured = {}

        def _mock_query(prompt, context, system):
            captured["prompt"] = prompt
            captured["context"] = context
            captured["system"] = system
            return "  DATA_HANDLER  "

        orchestrator.small_llm.query = _mock_query

        result = route_intent(
            prompt="How many records are in sales?",
            schema_context="schema context here",
            orchestrator=orchestrator,
        )

        self.assertEqual(result, "data_handler")
        self.assertEqual(captured["prompt"], "How many records are in sales?")
        self.assertEqual(captured["context"], "schema context here")
        self.assertIn("Choose from the following options: data_handler, metadata_handler", captured["system"])
        self.assertIn("- DummyDataHandler: Handles SQL/data retrieval prompts.", captured["system"])
        self.assertIn("- DummyMetaDataHandler: Handles schema and metadata prompts.", captured["system"])

    @patch("src.RAG.handlers.registry.get_all_handler_names")
    @patch("src.RAG.handlers.registry.get_all_handlers")
    def test_route_intent_routes_expected_prompts_to_expected_intents(
        self,
        mock_get_all_handlers,
        mock_get_all_handler_names,
    ):
        mock_get_all_handlers.return_value = [
            DummyDataHandler,
            DummyMetaDataHandler,
            DummyWebHandler,
        ]
        mock_get_all_handler_names.return_value = [
            "data_handler",
            "metadata_handler",
            "web_handler",
        ]

        orchestrator = SimpleNamespace()
        orchestrator.small_llm = SimpleNamespace()

        # Deterministic stub used to emulate intent classification from prompt text.
        def _mock_query(prompt, context, system):
            prompt_lower = prompt.lower()
            if "table" in prompt_lower or "schema" in prompt_lower or "column" in prompt_lower:
                return "  METADATA_HANDLER "
            if "latest" in prompt_lower or "news" in prompt_lower or "online" in prompt_lower:
                return "WEB_HANDLER"
            return "DATA_HANDLER"

        orchestrator.small_llm.query = _mock_query

        cases = [
            ("How many sales happened last month?", "data_handler"),
            ("What tables are available in this database?", "metadata_handler"),
            ("What are the columns in the customer table?", "metadata_handler"),
            ("What is the latest CHF to EUR exchange rate online?", "web_handler"),
        ]

        for prompt, expected_intent in cases:
            with self.subTest(prompt=prompt):
                intent = route_intent(
                    prompt=prompt,
                    schema_context="schema context here",
                    orchestrator=orchestrator,
                )
                self.assertEqual(intent, expected_intent)

