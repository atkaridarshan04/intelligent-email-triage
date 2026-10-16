"""
adapter.py — Re-exports from src.models for backwards compatibility.

The canonical definitions live in src/models/:
  - ModelAdapter, ModelOutput, STRUCTURED_COLS  →  src.models.base
  - LightGBMAdapter                             →  src.models.lgbm_model
"""
from src.models.base import ModelAdapter, ModelOutput, STRUCTURED_COLS
from src.models.lgbm_model import LightGBMAdapter

__all__ = ["ModelAdapter", "ModelOutput", "STRUCTURED_COLS", "LightGBMAdapter"]
