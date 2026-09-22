"""Interfaz para AI B-Roll (fuera del MVP). Sin implementación a propósito: se conectará una API
de stock footage o de generación de imagen/video, con sus credenciales en infra/.env."""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class BrollAsset:
    url: str
    kind: str  # "image" | "video"
    source: str


class BrollProvider(Protocol):
    def search(self, query: str, *, limit: int = 5) -> list[BrollAsset]: ...
