"""Cluster type constants for Assignment/Submission hierarchy."""

from __future__ import annotations

ASSIGNMENT_CLUSTER_TYPES: frozenset[str] = frozenset({"assignment", "student_paper_review"})

MODULE_STUDENT_PAPER_REVIEW = "student_paper_review"


def is_assignment_cluster(cluster_type: str) -> bool:
    """Return True when the cluster represents an SPR Assignment."""
    return cluster_type in ASSIGNMENT_CLUSTER_TYPES
