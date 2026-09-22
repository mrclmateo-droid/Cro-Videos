from typing import Protocol


class LLMProvider(Protocol):
    def complete_json(self, *, system: str, user: str, tool_name: str, schema: dict, max_tokens: int = 4096) -> dict:
        """Devuelve un objeto que cumple `schema` (salida estructurada)."""
        ...
