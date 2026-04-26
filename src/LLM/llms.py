from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type, Dict

class LLM(ABC):
    _registry: Dict[str, Type["LLM"]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "provider_name"):
            LLM._registry[cls.provider_name.lower()] = cls

    def __init__(self):
        pass

    def _build_messages(
        self,
        prompt: str,
        context: str,
        system: str,
        history: list[dict] | None = None
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": f"User question:\n{prompt}\n\nContext:\n{context}"})
        return messages

    def query(
        self,
        prompt: str,
        context: str,
        system: str,
        history: list[dict] | None = None
    ) -> str:
        try:
            return self._query(prompt, context, system, history)
        except Exception as e:
            raise RuntimeError(f"LLM query failed ({self.__class__.__name__}): {e}") from e

    @abstractmethod
    def _query(
        self,
        prompt: str,
        context: str,
        system: str,
        history: list[dict] | None = None
    ) -> str:
        """Subclasses must implement this."""
        pass


# --- PROVIDERS ---

class GroqLLM(LLM):
    provider_name = "groq"

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        super().__init__()
        self.client = Groq(api_key=api_key)
        self.model = model

    def _query(
        self,
        prompt: str,
        context: str,
        system: str,
        history: list[dict] | None = None
    ) -> str:
        messages = self._build_messages(prompt, context, system, history)
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model
        )
        return response.choices[0].message.content


# --- FACTORY ---

def get_llm(name: str, **kwargs) -> LLM:
    name_lower = name.lower()
    if name_lower not in LLM._registry:
        available = list(LLM._registry.keys())
        raise ValueError(f"LLM '{name}' not supported. Available: {available}")

    llm_class = LLM._registry[name_lower]
    return llm_class(**kwargs)