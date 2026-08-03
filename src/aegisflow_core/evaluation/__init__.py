"""Versioned evaluation datasets, runners, and comparison evidence."""

from aegisflow_core.evaluation.baseline import SingleAgentBaselineRunner
from aegisflow_core.evaluation.contracts import DatasetManifest, EvaluationCase
from aegisflow_core.evaluation.datasets import load_jsonl_cases, load_manifest

__all__ = [
    "DatasetManifest",
    "EvaluationCase",
    "SingleAgentBaselineRunner",
    "load_jsonl_cases",
    "load_manifest",
]
