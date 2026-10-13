"""Regression tests for semantic window boundaries, overlaps, and audit signing."""
import pytest

from agents.base import AuditTrail
from vector_window.semantic_boundaries import SemanticBoundaryDetector
from vector_window.overlap_smoothing import OverlapSmoother


def test_audit_chain_detects_modified_signed_metadata():
    trail = AuditTrail(secret_key="known-test-only-key")
    trail.log("worker", "internal", "CREATE", {"count": 1})
    trail.log("worker", "internal", "UPDATE", {"count": 2})
    assert trail.verify_integrity()
    external = trail.get_trail()
    external[0]["event_type"] = "TAMPER"
    assert trail.verify_integrity()  # defensive snapshot
    trail.logs[0]["event_type"] = "TAMPER"
    assert not trail.verify_integrity()


def test_audit_chain_detects_signature_forgery_without_valid_key():
    trail = AuditTrail(secret_key="known-test-only-key")
    trail.log("worker", "internal", "CREATE", {"count": 1})
    trail.logs[0]["payload_hash"] = "0" * 64
    assert not trail.verify_integrity()


def test_boundary_minimum_applies_to_first_and_last_segment():
    detector = SemanticBoundaryDetector(similarity_threshold=0.5, min_segment_size=2)
    chunks = ["a", "b", "c", "d", "e"]
    # Every consecutive cosine pair is maximally dissimilar.
    embeddings = [[1, 0], [0, 1], [1, 0], [0, 1], [1, 0]]
    result = detector.split_at_boundaries(chunks, embeddings)
    assert result == [["a", "b"], ["c", "d", "e"]]
    assert all(len(segment) >= 2 for segment in result)


@pytest.mark.parametrize("embeddings", [
    [[1, 0]],
    [[1, 0], [1]],
    [[1, float("nan")], [0, 1]],
    [[], []],
])
def test_boundary_rejects_invalid_embedding_shapes(embeddings):
    with pytest.raises(ValueError):
        SemanticBoundaryDetector().detect_boundaries(["one", "two"], embeddings)


def test_overlap_zero_keeps_all_elements():
    smooth = OverlapSmoother(overlap_fraction=0)
    merged, region = smooth.blend_windows([1, 2], [3, 4])
    assert merged == [1, 2, 3, 4]
    assert region.overlap_size == 0
    assert smooth.blend_windows([], [1])[0] == [1]
    assert smooth.smooth_sequence([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_overlap_rejects_negative_and_invalid_parameters():
    with pytest.raises(ValueError):
        OverlapSmoother(overlap_fraction=-0.1)
    with pytest.raises(ValueError):
        OverlapSmoother(blend_function="other")
    with pytest.raises(ValueError):
        OverlapSmoother().blend_windows([1], [2], overlap_size=-1)
