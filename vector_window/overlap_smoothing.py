"""
Overlap Smoothing for Semantic Vector Sliding Window.
Applies weighted blending at window boundaries to eliminate jarring context transitions.
"""
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class BlendRegion:
    """Represents an overlap blending region between two windows."""
    window_a_id: str
    window_b_id: str
    overlap_start: int
    overlap_end: int
    overlap_size: int
    blend_weights: List[float] = field(default_factory=list)


class OverlapSmoother:
    """Handles weighted blending at window overlap zones."""

    def __init__(self, overlap_fraction: float = 0.2, blend_function: str = "linear"):
        if not math.isfinite(overlap_fraction) or not 0.0 <= overlap_fraction <= 1.0:
            raise ValueError("overlap_fraction must be finite and between 0 and 1")
        if blend_function not in {"linear", "cosine", "sigmoid"}:
            raise ValueError("blend_function must be linear, cosine, or sigmoid")
        self.overlap_fraction = overlap_fraction
        self.blend_function = blend_function
        self._blend_log: List[Dict[str, Any]] = []

    def compute_overlap_size(self, window_size: int) -> int:
        """Compute overlap size based on window size and configured fraction."""
        if window_size < 0:
            raise ValueError("window_size cannot be negative")
        return min(window_size, max(0, int(window_size * self.overlap_fraction)))

    def compute_blend_weights(self, overlap_size: int) -> List[float]:
        """Compute blending weights for the overlap region."""
        if overlap_size <= 0:
            return []
        if self.blend_function == "linear":
            return [i / (overlap_size - 1) if overlap_size > 1 else 0.5
                    for i in range(overlap_size)]
        elif self.blend_function == "cosine":
            return [
                0.5 * (1 - math.cos(math.pi * i / (overlap_size - 1)))
                if overlap_size > 1 else 0.5
                for i in range(overlap_size)
            ]
        elif self.blend_function == "sigmoid":
            return [
                self._sigmoid((i - overlap_size / 2) / max(overlap_size / 6, 1))
                for i in range(overlap_size)
            ]
        else:
            return [0.5] * overlap_size

    def blend_windows(self, window_a: List[Any], window_b: List[Any],
                      overlap_size: Optional[int] = None) -> Tuple[List[Any], BlendRegion]:
        """Blend two windows at their overlap zone."""
        if overlap_size is None:
            overlap_size = self.compute_overlap_size(min(len(window_a), len(window_b)))

        if overlap_size < 0:
            raise ValueError("overlap_size cannot be negative")
        overlap_size = min(overlap_size, len(window_a), len(window_b))
        weights = self.compute_blend_weights(overlap_size)
        if overlap_size == 0:
            region = BlendRegion(
                window_a_id=f"window_{id(window_a)}",
                window_b_id=f"window_{id(window_b)}",
                overlap_start=len(window_a),
                overlap_end=len(window_a),
                overlap_size=0,
                blend_weights=[],
            )
            result = list(window_a) + list(window_b)
            self._blend_log.append({
                "overlap_size": 0,
                "blend_function": self.blend_function,
                "result_size": len(result),
                "timestamp": time.time(),
            })
            return result, region

        # Extract overlap zones
        zone_a = window_a[-overlap_size:]
        zone_b = window_b[:overlap_size]

        # Blend
        blended_zone = []
        for i in range(overlap_size):
            w = weights[i]
            if isinstance(zone_a[i], (int, float)) and isinstance(zone_b[i], (int, float)):
                blended = zone_a[i] * (1 - w) + zone_b[i] * w
                blended_zone.append(blended)
            else:
                blended_zone.append(zone_a[i] if w < 0.5 else zone_b[i])

        # Construct result: window_a (without overlap tail) + blended + window_b (without overlap head)
        result = window_a[:-overlap_size] + blended_zone + window_b[overlap_size:]

        region = BlendRegion(
            window_a_id=f"window_{id(window_a)}",
            window_b_id=f"window_{id(window_b)}",
            overlap_start=len(window_a) - overlap_size,
            overlap_end=len(window_a) - overlap_size + overlap_size,
            overlap_size=overlap_size,
            blend_weights=weights,
        )

        self._blend_log.append({
            "overlap_size": overlap_size,
            "blend_function": self.blend_function,
            "result_size": len(result),
            "timestamp": time.time(),
        })

        return result, region

    def smooth_sequence(self, windows: List[List[Any]],
                       overlap_size: Optional[int] = None) -> List[Any]:
        """Smooth a sequence of windows by blending overlaps."""
        if not windows:
            return []
        if len(windows) == 1:
            return list(windows[0])

        result = windows[0]
        for i in range(1, len(windows)):
            result, _ = self.blend_windows(result, windows[i], overlap_size)
        return result

    def get_blend_log(self) -> List[Dict[str, Any]]:
        return list(self._blend_log)

    def get_stats(self) -> Dict[str, Any]:
        if not self._blend_log:
            return {"total_blends": 0}
        return {
            "total_blends": len(self._blend_log),
            "avg_overlap_size": sum(b["overlap_size"] for b in self._blend_log) / len(self._blend_log),
            "blend_function": self.blend_function,
            "overlap_fraction": self.overlap_fraction,
        }

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))
