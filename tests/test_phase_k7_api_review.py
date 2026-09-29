from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_v1_2_api_review import (
    EXPECTED_BASELINE_COMMIT,
    EXPECTED_REVIEW_SOURCE_COMMIT,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v1_2_review_retains_exact_v1_1_contract_and_classifies_all_additions():
    review = validate(ROOT)
    assert review["stable_v1_1_exact_path_count"] == 238
    assert len(review["ensemble_addition_export_order"]) == 59
    assert len(review["proposed_stable_additions"]) == 59
    assert review["public_provisional_additions"] == []


def test_v1_2_review_identity_and_provenance_are_frozen():
    review = validate(ROOT)
    assert review["baseline_release"] == "v1.1.0"
    assert review["baseline_release_commit"] == EXPECTED_BASELINE_COMMIT
    assert review["review_source_commit"] == EXPECTED_REVIEW_SOURCE_COMMIT
    assert review["candidate_version"] == "1.2.0"
    assert review["development_version"] == "1.2.0.dev0"


def test_v1_2_stable_surface_matches_the_complete_package_export_surface():
    review = validate(ROOT)
    expected = {
        f"ncmemsim.ensemble.{name}"
        for name in review["ensemble_addition_export_order"]
    }
    stable = {
        entry["import_path"]
        for entry in review["proposed_stable_additions"]
    }
    provisional = {
        entry["import_path"]
        for entry in review["public_provisional_additions"]
    }
    assert stable == expected
    assert not provisional
    assert not (stable & provisional)


def test_v1_2_private_serialization_helper_is_not_a_stable_alias():
    review = validate(ROOT)
    stable = {
        entry["import_path"]
        for entry in review["proposed_stable_additions"]
    }
    implementation_modules = set(
        review["public_importable_not_separately_stable_modules"]
    )
    assert "ncmemsim.ensemble._serialization" not in stable
    assert "ncmemsim.ensemble._serialization" not in implementation_modules


def test_v1_2_review_preserves_scientific_result_boundaries():
    review = validate(ROOT)
    semantics = review["result_semantics_review"]
    assert "not claims" in semantics["stochastic_specification_and_sampling"]
    assert "not silently reclassified" in semantics["realization_and_execution"]
    assert "rather than statistically converged" in semantics["population_metrics_and_statistics"]
    assert "not manufacturing-yield" in semantics["feasibility_and_eligibility"]
    assert "not an intrinsically best device" in semantics["pareto_analysis"]
    assert "do not establish experimental calibration" in semantics["reporting_and_interpretation"]


def test_v1_2_review_is_not_release_approval():
    review = json.loads(
        (ROOT / "docs/v1_2_api_review.json").read_text(encoding="utf-8")
    )
    assert review["status"] == "reviewed_candidate_surface_not_release_approval"
