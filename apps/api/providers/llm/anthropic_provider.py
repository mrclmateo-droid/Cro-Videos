import anthropic

from app.errors import PermanentError


class AnthropicProvider:
    """Salida estructurada mediante tool use forzado (más robusto que parsear JSON de texto libre)."""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete_json(self, *, system: str, user: str, tool_name: str, schema: dict, max_tokens: int = 4096) -> dict:
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[{"name": tool_name, "description": "Devuelve el resultado estructurado.", "input_schema": schema}],
                tool_choice={"type": "tool", "name": tool_name},
            )
        except anthropic.AuthenticationError as e:
            raise PermanentError("ANTHROPIC_API_KEY inválida o sin permisos") from e
        except anthropic.NotFoundError as e:
            raise PermanentError(f"Modelo no disponible: {self.model}. Revisá ANTHROPIC_MODEL") from e
        for block in resp.content:
            if block.type == "tool_use":
                return dict(block.input)
        raise RuntimeError("El LLM no devolvió salida estructurada")
