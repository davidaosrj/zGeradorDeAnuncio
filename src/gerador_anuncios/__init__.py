"""Gerador automatizado de anúncios."""

from .ollama import OllamaClient, OllamaError
from .offline import OfflineGenerationError, generate_offline

__all__ = ["OllamaClient", "OllamaError", "OfflineGenerationError", "generate_offline"]
