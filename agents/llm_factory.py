"""
Deterministic mock inference adapter with identifier-pattern checks.
"""
from typing import Dict, Any, Optional
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Semantic Vector Sliding Window"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return f"[{self.system_name} mock]: No model inference or clinical validation was performed."


class LLMFactory:
    """Creates only the implemented mock client, never a mislabeled remote client."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Semantic Vector Sliding Window"):
        prov = str(provider).lower()
        if prov in ["mock", "deterministic", "test"]:
            return MockLLM(system_name)
        raise ValueError("Unsupported model provider: only 'mock' is implemented")
