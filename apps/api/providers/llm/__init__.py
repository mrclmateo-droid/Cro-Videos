from app.config import get_settings
from app.errors import PermanentError

from .base import LLMProvider

__all__ = ["get_llm_provider", "LLMProvider"]


def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "anthropic":
        if not s.anthropic_api_key:
            raise PermanentError("Falta ANTHROPIC_API_KEY en infra/.env")
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(s.anthropic_api_key, s.anthropic_model)
    raise PermanentError(f"LLM_PROVIDER no soportado: {s.llm_provider}")
