from abc import ABC, abstractmethod
from typing import Type, Dict, Any

class LLM(ABC):
    # 1. Access this directly or via a classmethod, not an instance property
    _registry: Dict[str, Type["LLM"]] = {}

    # 2. Fix the signature: remove 'name' from the arguments and use a class attribute instead
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # We look for a 'provider_name' defined inside the child class
        if hasattr(cls, "provider_name"):
            LLM._registry[cls.provider_name.lower()] = cls

    def __init__(self):
        pass

    def _build_messages(self, prompt: str, context: str, system: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": f"User question:\n{prompt}\n\nContext:\n{context}"}
        ]

    @abstractmethod  # 3. Use the actual decorator instead of raising NotImplementedError
    def query(self, prompt: str, context: str, system: str) -> str:
        """Subclasses must implement this."""
        pass


# --- PROVIDERS ---

# 4. Define the name inside the class body. This avoids the Python 3.9 TypeError.
class GroqLLM(LLM):
    provider_name = "groq"

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        super().__init__()
        self.client = Groq(api_key=api_key)
        self.model = model

    def query(self, prompt: str, context: str, system: str) -> str:
        messages = self._build_messages(prompt, context, system)
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model
        )
        return response.choices[0].message.content


# --- FACTORY ---

def get_llm(name: str, **kwargs) -> LLM:
    name_lower = name.lower()
    # Use LLM._registry directly (the dictionary)
    if name_lower not in LLM._registry:
        available = list(LLM._registry.keys())
        raise ValueError(f"LLM '{name}' not supported. Available: {available}")

    llm_class = LLM._registry[name_lower]
    return llm_class(**kwargs)