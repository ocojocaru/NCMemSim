from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_v1_1_api_review import validate

ROOT = Path(__file__).resolve().parents[1]

def test_v1_1_review_retains_exact_v1_contract_and_classifies_all_additions():
    review = validate(ROOT)
    assert review["stable_v1_exact_path_count"] == 204
    assert len(review["legacy_transport_package_exports"]) == 13
    assert len(review["transport_addition_export_order"]) == 44
    assert len(review["proposed_stable_additions"]) == 34
    assert len(review["public_provisional_additions"]) == 10

def test_v1_1_stable_and_provisional_surfaces_are_disjoint_and_complete():
    review = validate(ROOT)
    all_paths = {
        f"ncmemsim.transport.{name}"
        for name in review["transport_addition_export_order"]
    }
    stable = {entry["import_path"] for entry in review["proposed_stable_additions"]}
    provisional = {
        entry["import_path"] for entry in review["public_provisional_additions"]
    }
    assert not (stable & provisional)
    assert stable | provisional == all_paths

def test_v1_1_low_level_numeric_primitives_remain_public_provisional():
    review = validate(ROOT)
    provisional = {
        entry["import_path"] for entry in review["public_provisional_additions"]
    }
    assert "ncmemsim.transport.linear_wkb_transmission" in provisional
    assert "ncmemsim.transport.build_tat_barrier_profile" in provisional
    assert "ncmemsim.transport.image_force_barrier_lowering_J" in provisional
    assert "ncmemsim.transport.evaluate_tat_species" in provisional

def test_v1_1_review_preserves_scientific_result_boundaries():
    review = validate(ROOT)
    semantics = review["result_semantics_review"]
    assert "not device leakage current density" in semantics["conditional_rate_results"]
    assert "distinct from `FAILED`" in semantics["integrated_transport_results"]
    assert "structurally confounded" in semantics["sensitivity_results"]
    assert "not experimental calibration" in semantics["report_results"]

def test_v1_1_review_is_not_release_approval():
    review = json.loads((ROOT / "docs/v1_1_api_review.json").read_text(encoding="utf-8"))
    assert review["status"] == "reviewed_candidate_surface_not_release_approval"
