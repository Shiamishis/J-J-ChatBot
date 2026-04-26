import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, Type

# REMOVE: from src.RAG.handlers.base_handler import Handler

# Use "Any" or a string "Handler" for typing to break the cycle
HANDLER_REGISTRY: Dict[str, Any] = {}

def get_all_handlers() -> list[Any]:
    return list(HANDLER_REGISTRY.values())

def get_all_handler_names() -> list[str]:
    return list(HANDLER_REGISTRY.keys())

def register_handler(name: str):
    def decorator(cls: Type[Any]):
        # We check subclassing inside the decorator to avoid top-level imports
        # Or just trust the developer and remove the issubclass check
        HANDLER_REGISTRY[name] = cls
        return cls

    return decorator


def get_handler(intent: str, agent: Any) -> Any:
    # Print for debugging - see if your handlers are actually there
    # print(f"DEBUG: Current Registry: {list(HANDLER_REGISTRY.keys())}")

    handler_cls = HANDLER_REGISTRY.get(intent)
    if not handler_cls:
        handler_cls = HANDLER_REGISTRY.get("base_handler")
        if not handler_cls:
            raise ValueError(f"No handler registered for intent: {intent}. "
                             f"Available: {list(HANDLER_REGISTRY.keys())}")

    return handler_cls(agent)


def _autodiscover():
    package_dir = Path(__file__).parent
    # Add 'base_handler' and '__init__' to the skip list
    skip_list = ("registry", "base_handler", "__init__")

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name in skip_list:
            continue

        # Use absolute import
        module_path = f"src.RAG.handlers.{module_info.name}"
        importlib.import_module(module_path)


# RUN DISCOVERY
_autodiscover()
