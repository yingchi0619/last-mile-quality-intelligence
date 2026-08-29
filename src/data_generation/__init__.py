"""Reproducible synthetic-data generation package."""

from .config import GenerationConfig
from .generator import generate_all, run_generation

__all__ = ["GenerationConfig", "generate_all", "run_generation"]
