"""Validate the additive v1.2 API/result review without rewriting v1.1 evidence."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_stable_api_proposal import build_proposal


BASELINE_RELEASE = "v1.1.0"
EXPECTED_BASELINE_COMMIT = "3e926fccb3a02a1d0682941e52f48439d87a3733"
EXPECTED_REVIEW_SOURCE_COMMIT = "b762dc10debabafcfc0aeb9e5b3788745773c14b"
EXPECTED_CANDIDATE_VERSION = "1.2.0"
EXPECTED_DEVELOPMENT_VERSION = "1.2.0.dev0"
EXPECTED_V1_0_STABLE_COUNT = 204
EXPECTED_V1_1_STABLE_ADDITIONS = 34
EXPECTED_V1_1_BASELINE_COUNT = 238
EXPECTED_ENSEMBLE_EXPORT_COUNT = 59

EXPECTED_IMPLEMENTATION_MODULES = [
    "ncmemsim.ensemble.correlation",
    "ncmemsim.ensemble.distributions",
    "ncmemsim.ensemble.dtco",
    "ncmemsim.ensemble.execution",
    "ncmemsim.ensemble.feasibility",
    "ncmemsim.ensemble.metrics",
    "ncmemsim.ensemble.realization",
    "ncmemsim.ensemble.reporting",
    "ncmemsim.ensemble.rng",
    "ncmemsim.ensemble.sampling",
    "ncmemsim.ensemble.spec",
    "ncmemsim.ensemble.specification",
    "ncmemsim.ensemble.statistics",
]

EXPECTED_RESULT_KEYS = {
    "stochastic_specification_and_sampling",
    "realization_and_execution",
    "population_metrics_and_statistics",
    "feasibility_and_eligibility",
    "pareto_analysis",
    "reporting_and_interpretation",
}

REQUIRED_REVIEW_KEYS = {
    "schema_version",
    "status",
    "baseline_release",
    "baseline_release_commit",
    "review_source_commit",
    "candidate_version",
    "development_version",
    "stable_v1_1_exact_path_count",
    "ensemble_addition_export_order",
    "proposed_stable_additions",
    "public_provisional_additions",
    "public_importable_not_separately_stable_modules",
    "internal_policy",
    "selection_rationale",
    "public_provisional_rationale",
    "result_semantics_review",
}


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path) -> dict:
    review = _load_json(root / "docs/v1_2_api_review.json")

    if set(review) != REQUIRED_REVIEW_KEYS or review["schema_version"] != 1:
        raise ValueError("unsupported v1.2 API review schema")
    if review["status"] != "reviewed_candidate_surface_not_release_approval":
        raise ValueError("v1.2 review must remain candidate evidence, not release approval")
    if review["baseline_release"] != BASELINE_RELEASE:
        raise ValueError("unexpected v1.2 compatibility baseline")
    if review["candidate_version"] != EXPECTED_CANDIDATE_VERSION:
        raise ValueError("unexpected v1.2 candidate version")
    if review["development_version"] != EXPECTED_DEVELOPMENT_VERSION:
        raise ValueError("unexpected v1.2 development version")
    if review["stable_v1_1_exact_path_count"] != EXPECTED_V1_1_BASELINE_COUNT:
        raise ValueError("unexpected v1.1 stable baseline count")

    tag_commit = _git(root, "rev-parse", f"{BASELINE_RELEASE}^{{commit}}")
    if tag_commit != EXPECTED_BASELINE_COMMIT:
        raise ValueError("published v1.1.0 tag no longer resolves to the reviewed baseline commit")
    if review["baseline_release_commit"] != EXPECTED_BASELINE_COMMIT:
        raise ValueError("v1.2 review records the wrong v1.1.0 baseline commit")
    if review["review_source_commit"] != EXPECTED_REVIEW_SOURCE_COMMIT:
        raise ValueError("v1.2 review source commit changed")
    _git(root, "cat-file", "-e", f"{EXPECTED_REVIEW_SOURCE_COMMIT}^{{commit}}")

    stable_v1 = _load_json(root / "docs/stable_api_proposal.json")
    v1_1_review = _load_json(root / "docs/v1_1_api_review.json")
    v1_0_entries = stable_v1["entries"]
    v1_1_additions = v1_1_review["proposed_stable_additions"]

    if len(v1_0_entries) != EXPECTED_V1_0_STABLE_COUNT:
        raise ValueError("unexpected frozen v1.0 stable API count")
    if len(v1_1_additions) != EXPECTED_V1_1_STABLE_ADDITIONS:
        raise ValueError("unexpected v1.1 stable-addition count")

    expected_baseline_entries = v1_0_entries + v1_1_additions
    baseline_paths = [entry["import_path"] for entry in expected_baseline_entries]
    if (
        len(baseline_paths) != EXPECTED_V1_1_BASELINE_COUNT
        or len(set(baseline_paths)) != EXPECTED_V1_1_BASELINE_COUNT
    ):
        raise ValueError("v1.1 stable compatibility baseline is not 238 unique paths")

    current_baseline_entries = build_proposal(root, baseline_paths)["entries"]
    expected_by_path = {
        entry["import_path"]: entry
        for entry in expected_baseline_entries
    }
    current_by_path = {
        entry["import_path"]: entry
        for entry in current_baseline_entries
    }
    if set(expected_by_path) != set(current_by_path):
        raise ValueError("published v1.1 stable API paths drifted")
    changed_baseline = sorted(
        path
        for path in expected_by_path
        if expected_by_path[path] != current_by_path[path]
    )
    if changed_baseline:
        raise ValueError(
            "published v1.1 stable API/result contracts drifted: "
            + ", ".join(changed_baseline)
        )

    ensemble = importlib.import_module("ncmemsim.ensemble")
    exports = list(ensemble.__all__)
    if len(exports) != EXPECTED_ENSEMBLE_EXPORT_COUNT:
        raise ValueError("unexpected ncmemsim.ensemble export count")
    if len(set(exports)) != EXPECTED_ENSEMBLE_EXPORT_COUNT:
        raise ValueError("duplicate ncmemsim.ensemble exports")
    if review["ensemble_addition_export_order"] != exports:
        raise ValueError("ncmemsim.ensemble.__all__ differs from the reviewed K7a surface")

    addition_paths = [f"ncmemsim.ensemble.{name}" for name in exports]
    if set(addition_paths) & set(baseline_paths):
        raise ValueError("Phase K additions overlap the v1.1 stable baseline")

    candidate_entries = build_proposal(root, baseline_paths + addition_paths)["entries"]
    candidate_by_path = {
        entry["import_path"]: entry
        for entry in candidate_entries
    }
    expected_additions = [candidate_by_path[path] for path in addition_paths]

    if len(review["proposed_stable_additions"]) != EXPECTED_ENSEMBLE_EXPORT_COUNT:
        raise ValueError("unexpected v1.2 proposed-stable addition count")
    if review["proposed_stable_additions"] != expected_additions:
        raise ValueError("v1.2 proposed stable signatures/source contracts drifted")
    if review["public_provisional_additions"] != []:
        raise ValueError("K7a review unexpectedly classifies package exports as provisional")

    implementation_modules = review["public_importable_not_separately_stable_modules"]
    if implementation_modules != EXPECTED_IMPLEMENTATION_MODULES:
        raise ValueError("unexpected Phase K implementation-module classification")

    inventory = _load_json(root / "docs/api_inventory.json")
    inventory_modules = {item["module"] for item in inventory["modules"]}
    if not set(EXPECTED_IMPLEMENTATION_MODULES) <= inventory_modules:
        raise ValueError("reviewed Phase K implementation module missing from source inventory")
    if "ncmemsim.ensemble._serialization" not in inventory_modules:
        raise ValueError("private Phase K serialization helper missing from source inventory")
    if "ncmemsim.ensemble._serialization" in implementation_modules:
        raise ValueError("private Phase K serialization helper was classified as a public implementation module")

    semantics = review["result_semantics_review"]
    if set(semantics) != EXPECTED_RESULT_KEYS:
        raise ValueError("result-semantics review categories changed")
    if any(
        not isinstance(value, str) or not value.strip()
        for value in semantics.values()
    ):
        raise ValueError("empty v1.2 result-semantics review statement")

    required_semantics = {
        "stochastic_specification_and_sampling": "not claims",
        "realization_and_execution": "not silently reclassified",
        "population_metrics_and_statistics": "rather than statistically converged",
        "feasibility_and_eligibility": "not manufacturing-yield",
        "pareto_analysis": "not an intrinsically best device",
        "reporting_and_interpretation": "do not establish experimental calibration",
    }
    for key, phrase in required_semantics.items():
        if phrase not in semantics[key]:
            raise ValueError(f"missing scientific boundary in {key}: {phrase}")

    for field in (
        "internal_policy",
        "selection_rationale",
        "public_provisional_rationale",
    ):
        if not isinstance(review[field], str) or not review[field].strip():
            raise ValueError("missing v1.2 review rationale: " + field)

    return review


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        review = validate(root)
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        ImportError,
        subprocess.CalledProcessError,
    ) as exc:
        print("v1.2 API/result review FAIL:", exc, file=sys.stderr)
        return 1

    print(
        "v1.2 API/result review PASS: "
        f"{review['stable_v1_1_exact_path_count']} retained v1.1 stable paths + "
        f"{len(review['proposed_stable_additions'])} proposed stable additions + "
        f"{len(review['public_provisional_additions'])} public provisional additions; "
        "release approval not implied."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
