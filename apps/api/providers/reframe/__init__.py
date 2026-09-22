from .base import CropPlan, Reframer
from .center import CenterReframer

__all__ = ["get_reframer", "CropPlan", "Reframer"]


def get_reframer() -> Reframer:
    return CenterReframer()
