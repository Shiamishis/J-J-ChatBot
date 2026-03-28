from src.LLM.query import query_llm
import unittest


class TestLLM(unittest.TestCase):
    def test_query_llm(self):
        prompt = "What is the capital of France?"
        context = "The capital of France is Paris."
        response = query_llm(prompt, context, llm_name="groq")
        assert "Paris" in response, f"Expected 'Paris' in response, got: {response}"

