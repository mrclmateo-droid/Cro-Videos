from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CropPlan:
    """Recorte estático. Para tracking dinámico esto evolucionará a una lista de keyframes."""
    x: int
    y: int
    w: int
    h: int


class Reframer(Protocol):
    def plan(self, *, src_w: int, src_h: int, target_aspect: float, source_url: str,
             start: float, end: float) -> CropPlan: ...
