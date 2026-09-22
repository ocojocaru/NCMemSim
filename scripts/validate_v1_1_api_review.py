"""Validate the additive v1.1 API/result review without rewriting v1.0."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_stable_api_proposal import build_proposal

PROVISIONAL_NAMES = ['TATBarrierProfile', 'build_tat_barrier_profile', 'evaluate_tat_species', 'linear_wkb_transmission', 'BarrierHeightCorrection', 'CorrectedTATBarrierProfile', 'apply_image_force_barrier_correction', 'build_corrected_tat_barrier_profile', 'evaluate_tat_species_with_barrier_correction', 'image_force_barrier_lowering_J']
EXPECTED_RESULT_KEYS = {
    "configuration_and_provenance",
    "conditional_rate_results",
    "integrated_transport_results",
    "sensitivity_results",
    "report_results",
}

def validate(root: Path) -> dict:
    review = json.loads((root / "docs/v1_1_api_review.json").read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "status",
        "baseline_release",
        "baseline_release_commit",
        "review_source_commit",
        "candidate_version",
        "development_version",
        "stable_v1_exact_path_count",
        "legacy_transport_package_exports",
        "transport_addition_export_order",
        "proposed_stable_additions",
        "public_provisional_additions",
        "public_importable_not_separately_stable_modules",
        "internal_policy",
        "selection_rationale",
        "public_provisional_rationale",
        "result_semantics_review",
    }
    if set(review) != required or review["schema_version"] != 1:
        raise ValueError("unsupported v1.1 API review schema")
    if review["status"] != "reviewed_candidate_surface_not_release_approval":
        raise ValueError("v1.1 review must remain a candidate review, not release approval")
    if review["baseline_release"] != "v1.0.0" or review["candidate_version"] != "1.1.0":
        raise ValueError("unexpected release identities")
    if review["development_version"] != "1.1.0.dev0":
        raise ValueError("unexpected development version")
    if review["stable_v1_exact_path_count"] != 204:
        raise ValueError("frozen v1 path count changed")

    baseline = json.loads((root / "docs/stable_api_proposal.json").read_text(encoding="utf-8"))
    baseline_paths = [entry["import_path"] for entry in baseline["entries"]]
    if len(baseline_paths) != 204 or len(set(baseline_paths)) != 204:
        raise ValueError("frozen v1 proposal is not 204 unique paths")
    if build_proposal(root, baseline_paths) != baseline:
        raise ValueError("frozen v1 proposal drifted during v1.1 review")

    legacy = review["legacy_transport_package_exports"]
    addition_names = review["transport_addition_export_order"]
    if len(legacy) != 13 or len(addition_names) != 44:
        raise ValueError("unexpected transport legacy/addition counts")
    if len(set(legacy)) != 13 or len(set(addition_names)) != 44:
        raise ValueError("duplicate transport export classification")
    if set(legacy) & set(addition_names):
        raise ValueError("legacy and additive transport surfaces overlap")

    transport = importlib.import_module("ncmemsim.transport")
    if list(transport.__all__) != legacy + addition_names:
        raise ValueError("ncmemsim.transport.__all__ differs from reviewed J7a surface")

    addition_paths = [f"ncmemsim.transport.{name}" for name in addition_names]
    candidate = build_proposal(root, baseline_paths + addition_paths)
    by_path = {entry["import_path"]: entry for entry in candidate["entries"]}

    provisional_paths = sorted(f"ncmemsim.transport.{name}" for name in PROVISIONAL_NAMES)
    stable_paths = sorted(set(addition_paths) - set(provisional_paths))
    if len(stable_paths) != 34 or len(provisional_paths) != 10:
        raise ValueError("unexpected stable/provisional split")
    if set(stable_paths) | set(provisional_paths) != set(addition_paths):
        raise ValueError("stable/provisional split does not cover all additions")
    if set(stable_paths) & set(provisional_paths):
        raise ValueError("stable/provisional split overlaps")

    expected_stable = [by_path[path] for path in stable_paths]
    expected_provisional = [by_path[path] for path in provisional_paths]
    if review["proposed_stable_additions"] != expected_stable:
        raise ValueError("v1.1 proposed stable signatures/source contracts drifted")
    if review["public_provisional_additions"] != expected_provisional:
        raise ValueError("v1.1 provisional signatures/source contracts drifted")

    inventory = json.loads((root / "docs/api_inventory.json").read_text(encoding="utf-8"))
    inventory_modules = {item["module"] for item in inventory["modules"]}
    implementation_modules = review["public_importable_not_separately_stable_modules"]
    if len(implementation_modules) != 6 or len(set(implementation_modules)) != 6:
        raise ValueError("unexpected implementation-module classification")
    if not set(implementation_modules) <= inventory_modules:
        raise ValueError("reviewed implementation module missing from source inventory")

    if set(review["result_semantics_review"]) != EXPECTED_RESULT_KEYS:
        raise ValueError("result-semantics review categories changed")
    if any(
        not isinstance(value, str) or not value.strip()
        for value in review["result_semantics_review"].values()
    ):
        raise ValueError("empty result-semantics review statement")
    for field in ("internal_policy", "selection_rationale", "public_provisional_rationale"):
        if not isinstance(review[field], str) or not review[field].strip():
            raise ValueError("missing review rationale: " + field)
    return review

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        review = validate(root)
    except (ValueError, KeyError, TypeError, OSError, ImportError) as exc:
        print("v1.1 API/result review FAIL:", exc, file=sys.stderr)
        return 1
    print(
        "v1.1 API/result review PASS: "
        f"{review['stable_v1_exact_path_count']} retained v1 paths + "
        f"{len(review['proposed_stable_additions'])} proposed stable additions + "
        f"{len(review['public_provisional_additions'])} public provisional additions; "
        "release approval not implied."
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
