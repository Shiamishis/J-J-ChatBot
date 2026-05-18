from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources


@register_handler("dashboard_handler")
class DashboardHandler(Handler):
    description = (
        "The DashboardHandler answers questions about how to use the dashboards, "
        "what their KPIs mean, how to navigate them, what features they have, "
        "and how metrics are calculated. It uses dashboard-specific training "
        "documentation (PDFs, DOCXs, XLSXs, and video transcripts) as context. "
        "Use this for any 'how do I...', 'what does X mean', or 'explain the dashboard' "
        "questions that are NOT about querying live data from the database."
    )

    def __init__(self, resources: Resources):
        super().__init__(resources)

    def _pick_context(self, prompt: str) -> str:
        """
        Pick the most relevant dashboard's training context by keyword overlap.
        Falls back to concatenating all contexts if no dashboard name matches.
        """
        contexts = getattr(self.resources, "training_contexts", None) or {}
        if not contexts:
            return ""

        prompt_lower = prompt.lower()
        scored = []
        for name, text in contexts.items():
            slug_words = [w.lower() for w in name.replace("_", " ").split() if len(w) > 2]
            score = sum(1 for w in slug_words if w in prompt_lower)
            scored.append((score, name, text))

        scored.sort(key=lambda t: -t[0])

        if scored and scored[0][0] > 0:
            _, top_name, top_text = scored[0]
            return f"=== Dashboard: {top_name} ===\n{top_text}"

        # No keyword match — let the LLM see all of them.
        return "\n\n".join(f"=== Dashboard: {name} ===\n{text}" for _, name, text in scored)

    def handle(self, prompt: str, history: list | None = None) -> str:
        context = self._pick_context(prompt)
        if not context:
            return (
                "I don't have any dashboard training materials loaded. "
                "Please run `python scripts/parse_training_materials.py` first."
            )
        response = self.resources.large_llm.query(
            prompt=prompt,
            context=context,
            system=(
                "You are a helpful data assistant. Always respond in plain text only. "
                "Never use markdown, code blocks, bullet points with symbols, or any "
                "formatting. Just use clear plain sentences. Answer the user's question "
                "using the dashboard training documentation provided as context. If the "
                "answer is not present in the documentation, say so plainly."
            ),
            history=history,
        )
        return response
