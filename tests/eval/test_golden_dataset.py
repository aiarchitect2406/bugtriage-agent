"""Pytest test case for ADK 2.0 Golden Dataset Evaluation."""

import pytest
from tests.eval.run_eval import run_adk_evaluation_suite

def test_golden_dataset_evaluation_accuracy():
    """Asserts that ADK 2.0 Agent passes 100% of golden dataset evaluation trajectories."""
    success = run_adk_evaluation_suite()
    assert success is True, "ADK 2.0 Agent failed one or more golden dataset evaluation trajectories!"
