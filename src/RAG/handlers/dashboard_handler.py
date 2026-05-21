from src.RAG.handlers.base_handler import Handler
from src.RAG.handlers.registry import register_handler
from src.RAG.resources import Resources


@register_handler("dashboard_handler")
class DashboardHandler(Handler):
    description = (
        "Acts as a user guide for the front-end reporting interface. It answers 'how-to' questions "
        "based on training manuals, documentation and dashboards. "
        "Use this for (Positive): Navigation help ('Where is the Monthly Coverage report?'), "
        "UI instructions ('How do I export this chart to a PDF?'), metric logic/definitions and kpi explanations"
        "('What logic is used to calculate the Health Score?' or 'What does the red color-coding indicate?')"
        "and questions about the specific dashboard('What is this chart about'). "
        "Do NOT use this for (Negative): Requests for live data values ('What is the current Health Score "
        "for Client X?'), database technical questions ('What is the data type of the health_score column?'), "
        "or web searches ('What are competitors doing?')."
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
