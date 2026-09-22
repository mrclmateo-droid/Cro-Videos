from .base import CropPlan


class CenterReframer:
    """MVP: recorte centrado. Reemplazable por un reframer con face/speaker tracking."""

    def plan(self, *, src_w: int, src_h: int, target_aspect: float, **_) -> CropPlan:
        if src_w / src_h >= target_aspect:
            h = src_h
            w = round(h * target_aspect)
        else:
            w = src_w
            h = round(w / target_aspect)
        w -= w % 2
        h -= h % 2
        x = (src_w - w) // 2
        y = (src_h - h) // 2
        return CropPlan(x=x - x % 2, y=y - y % 2, w=w, h=h)
