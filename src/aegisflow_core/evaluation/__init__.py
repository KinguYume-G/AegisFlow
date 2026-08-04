"""Versioned evaluation datasets, runners, and comparison evidence."""

from aegisflow_core.evaluation.baseline import SingleAgentBaselineRunner
from aegisflow_core.evaluation.contracts import DatasetManifest, EvaluationCase
from aegisflow_core.evaluation.datasets import load_jsonl_cases, load_manifest
from aegisflow_core.evaluation.reporting import EvaluationReport, build_report

__all__ = [
    "DatasetManifest",
    "EvaluationCase",
    "EvaluationReport",
    "SingleAgentBaselineRunner",
    "build_report",
    "load_jsonl_cases",
    "load_manifest",
]
