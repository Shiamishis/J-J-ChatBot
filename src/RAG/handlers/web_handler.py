from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources
import requests
import os


@register_handler("web_handler")
class WebHandler(Handler):
    description = (
        "Fetches real-time, external, or world knowledge that is not contained within the internal "
        "company database or documentation. "
        "Use this for (Positive): External market data ('What is the current stock price of Nvidia?'), "
        "industry benchmarks ('What is the average churn rate for SaaS?'), and current events "
        "('Who won the Super Bowl?'). "
        "Do NOT use this for (Negative): Internal company data ('What was our revenue?'), "
        "internal documentation ('How do I use our internal dashboard?'), or simple conversation."
    )

    def __init__(self, resources: Resources):
        super().__init__(resources)

    def _search(self, query):
        api_key = os.environ.get("SERPER_API_KEY")
        print("API_KEY: ", api_key)
        response = requests.post("https://google.serper.dev/search",
                                 json={"q": query},
                                 headers={"X-API-KEY": api_key})
        print(response)
        results = response.json()["organic"]
        return "\n".join([f"{r['title']}: {r['snippet']}" for r in results[:3]])

    def handle(self, prompt: str, history: list | None = None) -> str:
        """
        Handles prompts that require web search or external API calls.
        """
        web_response = self._search(prompt)
        llm_response = self.resources.large_llm.query(
            prompt=f"Given the question: '{prompt}, provide a comprehensive answer based on the following web search results.",
            context=f"Use the following web search results: {web_response}",
            system="You are a helpful data assistant. Always respond in plain text only. Never use markdown, code blocks, bullet points with symbols, or any formatting. Just use clear plain sentences. Answer based on the web search results provided.",
            history=history
        )
        return llm_response
