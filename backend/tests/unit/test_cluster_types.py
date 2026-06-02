"""Unit tests for cluster type helpers."""

from core.cluster_types import is_assignment_cluster


def test_is_assignment_cluster_accepts_assignment() -> None:
    assert is_assignment_cluster("assignment") is True


def test_is_assignment_cluster_accepts_legacy_type() -> None:
    assert is_assignment_cluster("student_paper_review") is True


def test_is_assignment_cluster_rejects_other_types() -> None:
    assert is_assignment_cluster("external_paper_review") is False
