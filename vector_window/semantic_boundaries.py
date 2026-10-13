"""
Semantic Boundary Detection for Semantic Vector Sliding Window.
Detects topic shifts using embedding similarity to insert intelligent window boundaries.
"""
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class BoundaryType(str, Enum):
    TOPIC_SHIFT = "topic_shift"
    SECTION_BREAK = "section_break"
    GRADUAL_DRIFT = "gradual_drift"
    NO_BOUNDARY = "no_boundary"


@dataclass
class SemanticBoundary:
    """Represents a detected semantic boundary."""
    position: int
    boundary_type: BoundaryType
    similarity_score: float
    threshold: float
    confidence: float
    context_before: str = ""
    context_after: str = ""


@dataclass
class BoundaryDetectionResult:
    """Result of boundary detection on a document."""
    boundaries: List[SemanticBoundary]
    total_chunks: int
    avg_similarity: float
    min_similarity: float
    detection_time_ms: float


class SemanticBoundaryDetector:
    """Detects topic boundaries using embedding similarity analysis."""

    def __init__(self, similarity_threshold: float = 0.45,
                 drift_window: int = 3,
                 min_segment_size: int = 2):
        if not math.isfinite(similarity_threshold) or not -1.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be finite and between -1 and 1")
        if not isinstance(drift_window, int) or drift_window < 1:
            raise ValueError("drift_window must be a positive integer")
        if not isinstance(min_segment_size, int) or min_segment_size < 1:
            raise ValueError("min_segment_size must be a positive integer")
        self.similarity_threshold = similarity_threshold
        self.drift_window = drift_window
        self.min_segment_size = min_segment_size
        self._detection_log: List[Dict[str, Any]] = []

    def detect_boundaries(self, chunks: List[str],
                         embeddings: Optional[List[List[float]]] = None) -> BoundaryDetectionResult:
        """Detect semantic boundaries in a sequence of text chunks."""
        start_time = time.time()

        if embeddings is not None:
            if len(embeddings) != len(chunks):
                raise ValueError("embeddings must have exactly one vector per chunk")
            if embeddings:
                dimension = len(embeddings[0])
                if dimension == 0 or any(len(v) != dimension for v in embeddings):
                    raise ValueError("embeddings must be non-empty vectors of equal dimension")
                if any(not math.isfinite(x) for v in embeddings for x in v):
                    raise ValueError("embeddings must contain only finite numbers")

        if len(chunks) < 2:
            return BoundaryDetectionResult(
                boundaries=[], total_chunks=len(chunks),
                avg_similarity=1.0, min_similarity=1.0,
                detection_time_ms=0.0,
            )

        # Compute similarities between consecutive chunks
        if embeddings is not None:
            similarities = self._cosine_similarities_from_embeddings(embeddings)
        else:
            similarities = self._text_similarities(chunks)

        # Detect boundaries
        boundaries = []
        for i, sim in enumerate(similarities):
            boundary_type = self._classify_boundary(sim, similarities, i)
            if boundary_type != BoundaryType.NO_BOUNDARY:
                confidence = self._compute_confidence(sim, similarities, i)
                boundaries.append(SemanticBoundary(
                    position=i + 1,
                    boundary_type=boundary_type,
                    similarity_score=sim,
                    threshold=self.similarity_threshold,
                    confidence=confidence,
                    context_before=chunks[i][-100:] if i < len(chunks) else "",
                    context_after=chunks[i + 1][:100] if i + 1 < len(chunks) else "",
                ))

        # Enforce minimum segment size
        boundaries = self._enforce_min_segment(boundaries, len(chunks))

        elapsed_ms = (time.time() - start_time) * 1000
        avg_sim = sum(similarities) / len(similarities) if similarities else 1.0
        min_sim = min(similarities) if similarities else 1.0

        result = BoundaryDetectionResult(
            boundaries=boundaries,
            total_chunks=len(chunks),
            avg_similarity=avg_sim,
            min_similarity=min_sim,
            detection_time_ms=elapsed_ms,
        )

        self._detection_log.append({
            "total_chunks": len(chunks),
            "boundaries_found": len(boundaries),
            "avg_similarity": avg_sim,
            "min_similarity": min_sim,
            "timestamp": time.time(),
        })

        return result

    def split_at_boundaries(self, chunks: List[str],
                           embeddings: Optional[List[List[float]]] = None) -> List[List[str]]:
        """Split chunks into segments at detected boundaries."""
        result = self.detect_boundaries(chunks, embeddings)
        boundary_positions = {b.position for b in result.boundaries}

        segments = []
        current_segment = []
        for i, chunk in enumerate(chunks):
            current_segment.append(chunk)
            if i + 1 in boundary_positions and len(current_segment) >= self.min_segment_size:
                segments.append(current_segment)
                current_segment = []
        if current_segment:
            segments.append(current_segment)
        return segments

    def _cosine_similarities_from_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Compute cosine similarities between consecutive embeddings."""
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)
        return similarities

    def _text_similarities(self, chunks: List[str]) -> List[float]:
        """Compute text-based similarities between consecutive chunks (Jaccard)."""
        similarities = []
        for i in range(len(chunks) - 1):
            sim = self._jaccard_similarity(chunks[i], chunks[i + 1])
            similarities.append(sim)
        return similarities

    def _classify_boundary(self, similarity: float, all_similarities: List[float],
                          position: int) -> BoundaryType:
        """Classify the type of boundary based on similarity patterns."""
        if similarity < self.similarity_threshold * 0.5:
            return BoundaryType.TOPIC_SHIFT
        if similarity < self.similarity_threshold:
            # Check for gradual drift
            start = max(0, position - self.drift_window)
            end = min(len(all_similarities), position + self.drift_window + 1)
            window = all_similarities[start:end]
            if len(window) >= 3:
                trend = window[-1] - window[0]
                if trend < -0.15:
                    return BoundaryType.GRADUAL_DRIFT
            return BoundaryType.SECTION_BREAK
        return BoundaryType.NO_BOUNDARY

    def _compute_confidence(self, similarity: float, all_similarities: List[float],
                           position: int) -> float:
        """Compute confidence score for a boundary detection."""
        mean_sim = sum(all_similarities) / len(all_similarities)
        std_sim = math.sqrt(sum((s - mean_sim) ** 2 for s in all_similarities) / len(all_similarities))
        if std_sim == 0:
            return 0.5
        z_score = (mean_sim - similarity) / std_sim
        return min(1.0, max(0.0, z_score / 3.0))

    def _enforce_min_segment(self, boundaries: List[SemanticBoundary],
                            total_chunks: int) -> List[SemanticBoundary]:
        """Ensure all segments, including first and last, meet the minimum."""
        accepted = []
        previous = 0
        for boundary in boundaries:
            if boundary.position - previous < self.min_segment_size:
                continue
            if total_chunks - boundary.position < self.min_segment_size:
                continue
            accepted.append(boundary)
            previous = boundary.position
        return accepted

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            raise ValueError("cosine vectors must have the same non-zero dimension")
        if any(not math.isfinite(x) for x in a + b):
            raise ValueError("cosine vectors must contain finite numbers")
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _jaccard_similarity(text_a: str, text_b: str) -> float:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a and not words_b:
            return 1.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    def get_detection_log(self) -> List[Dict[str, Any]]:
        return list(self._detection_log)
