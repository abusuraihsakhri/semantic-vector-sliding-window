"""
Window Size Auto-Tuning for Semantic Vector Sliding Window.
Dynamically adjusts window size based on query complexity heuristics.
"""
import math
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class TuningDecision:
    """Record of an auto-tuning decision."""
    query: str
    complexity: QueryComplexity
    base_window_size: int
    adjusted_window_size: int
    factors: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


class WindowAutoTuner:
    """Dynamically adjusts window size based on query complexity."""

    def __init__(self, base_window_size: int = 512,
                 min_window_size: int = 128,
                 max_window_size: int = 2048):
        self.base_window_size = base_window_size
        self.min_window_size = min_window_size
        self.max_window_size = max_window_size
        self._tuning_log: List[TuningDecision] = []

    def classify_complexity(self, query: str) -> QueryComplexity:
        """Classify query complexity using heuristics."""
        score = self._compute_complexity_score(query)
        if score < 0.3:
            return QueryComplexity.SIMPLE
        elif score < 0.7:
            return QueryComplexity.MODERATE
        return QueryComplexity.COMPLEX

    def compute_window_size(self, query: str, context: Optional[Dict[str, Any]] = None) -> int:
        """Compute optimal window size for a given query."""
        ctx = context or {}
        complexity = self.classify_complexity(query)
        factors = self._compute_factors(query, complexity, ctx)

        multiplier = 1.0
        for factor_value in factors.values():
            multiplier *= factor_value

        adjusted = int(self.base_window_size * multiplier)
        adjusted = max(self.min_window_size, min(self.max_window_size, adjusted))

        decision = TuningDecision(
            query=query[:100],
            complexity=complexity,
            base_window_size=self.base_window_size,
            adjusted_window_size=adjusted,
            factors=factors,
        )
        self._tuning_log.append(decision)
        return adjusted

    def _compute_complexity_score(self, query: str) -> float:
        """Compute a 0-1 complexity score for a query."""
        score = 0.0
        # Length factor
        length = len(query)
        score += min(length / 500, 0.3)
        # Entity count (capitalized words as proxy)
        entities = len(re.findall(r'\b[A-Z][a-z]+\b', query))
        score += min(entities / 10, 0.2)
        # Technical terms
        technical_markers = ["differential", "algorithm", "protocol", "analysis",
                           "comparison", "evaluation", "assessment", "diagnosis"]
        tech_count = sum(1 for t in technical_markers if t.lower() in query.lower())
        score += min(tech_count / 5, 0.2)
        # Question complexity (multiple clauses)
        clauses = query.count(",") + query.count(";") + query.count(" and ") + query.count(" or ")
        score += min(clauses / 5, 0.15)
        # Domain-specific terms
        domain_terms = ["patient", "clinical", "treatment", "medication", "lab",
                       "imaging", "pathology", "surgical", "pharmacokinetic"]
        domain_count = sum(1 for t in domain_terms if t.lower() in query.lower())
        score += min(domain_count / 5, 0.15)
        return min(score, 1.0)

    def _compute_factors(self, query: str, complexity: QueryComplexity,
                        context: Dict[str, Any]) -> Dict[str, float]:
        """Compute multipliers for window size adjustment."""
        factors = {}
        # Complexity factor
        complexity_map = {
            QueryComplexity.SIMPLE: 0.5,
            QueryComplexity.MODERATE: 1.0,
            QueryComplexity.COMPLEX: 1.8,
        }
        factors["complexity"] = complexity_map[complexity]

        # Token density factor (if available)
        if "token_density" in context:
            density = context["token_density"]
            factors["density"] = 1.2 if density > 0.8 else (0.8 if density < 0.3 else 1.0)

        # Historical performance factor
        if "avg_relevance_score" in context:
            relevance = context["avg_relevance_score"]
            factors["performance"] = 1.3 if relevance > 0.8 else (0.7 if relevance < 0.4 else 1.0)

        return factors

    def get_tuning_log(self) -> List[Dict[str, Any]]:
        return [
            {
                "query": d.query,
                "complexity": d.complexity.value,
                "base": d.base_window_size,
                "adjusted": d.adjusted_window_size,
                "factors": d.factors,
            }
            for d in self._tuning_log
        ]

    def get_stats(self) -> Dict[str, Any]:
        if not self._tuning_log:
            return {"total_decisions": 0}
        sizes = [d.adjusted_window_size for d in self._tuning_log]
        complexities = [d.complexity.value for d in self._tuning_log]
        return {
            "total_decisions": len(self._tuning_log),
            "avg_window_size": sum(sizes) / len(sizes),
            "min_window_size": min(sizes),
            "max_window_size": max(sizes),
            "complexity_distribution": {
                c: complexities.count(c) for c in set(complexities)
            },
        }
