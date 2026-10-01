# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Build the Phase K7a v1.2.0 API/result compatibility review snapshot.

This builder preserves the published v1.1.0 compatibility baseline and records
the additive public ``ncmemsim.ensemble`` surface as candidate review evidence.
It does not bump the package version and does not approve or publish v1.2.0.
"""
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
CANDIDATE_VERSION = "1.2.0"
DEVELOPMENT_VERSION = "1.2.0.dev0"
EXPECTED_V1_0_STABLE_COUNT = 204
EXPECTED_V1_1_STABLE_ADDITIONS = 34
EXPECTED_V1_1_BASELINE_COUNT = 238
EXPECTED_ENSEMBLE_EXPORT_COUNT = 59

IMPLEMENTATION_MODULES = [
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

RESULT_SEMANTICS_REVIEW = {
    "stochastic_specification_and_sampling": (
        "Phase K samples explicitly declared mathematical distributions and "
        "dependence definitions with deterministic RNG/sample identities; these "
        "definitions are not claims that the selected distributions or "
        "correlations are true fabrication-process distributions."
    ),
    "realization_and_execution": (
        "Realization identity, domain validation, binding application and "
        "execution failure provenance preserve every attempted sample. "
        "Simulation failure is not silently reclassified as physical "
        "infeasibility."
    ),
    "population_metrics_and_statistics": (
        "Population summaries are computed over the declared assessed membership "
        "and retain denominators, units and sample membership. Small synthetic "
        "ensembles are deterministic comparison evidence rather than statistically "
        "converged fabrication-population estimates."
    ),
    "feasibility_and_eligibility": (
        "simulated_pass_fraction and ensemble_feasibility_fraction are "
        "simulation-defined quantities. They are not manufacturing-yield "
        "estimates without an independently calibrated fabrication-population "
        "model."
    ),
    "pareto_analysis": (
        "Pareto ranks express exact trade-offs under the explicitly declared "
        "objectives and eligibility constraints. A non-dominated point is not an "
        "intrinsically best device and q05 from the six-sample K6c reference is "
        "not a statistically converged fabrication-tail estimate."
    ),
    "reporting_and_interpretation": (
        "Immutable hashes and report bundles establish internal identity, linkage "
        "and reproducibility. They do not establish experimental calibration, "
        "model validity outside the declared scope, or manufacturing yield."
    ),
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


def build_review(root: Path = ROOT) -> dict:
    """Build the deterministic K7a review payload from the current source tree."""

    # Dereference an annotated release tag to the commit it identifies.
    baseline_commit = _git(root, "rev-parse", f"{BASELINE_RELEASE}^{{commit}}")
    source_commit = _git(root, "rev-parse", "HEAD")

    stable_v1 = _load_json(root / "docs/stable_api_proposal.json")
    v1_1_review = _load_json(root / "docs/v1_1_api_review.json")

    v1_0_entries = stable_v1["entries"]
    v1_1_additions = v1_1_review["proposed_stable_additions"]

    if len(v1_0_entries) != EXPECTED_V1_0_STABLE_COUNT:
        raise ValueError("unexpected frozen v1.0 stable API count")
    if len(v1_1_additions) != EXPECTED_V1_1_STABLE_ADDITIONS:
        raise ValueError("unexpected v1.1 stable-addition count")

    expected_entries = v1_0_entries + v1_1_additions
    baseline_paths = [entry["import_path"] for entry in expected_entries]
    if (
        len(baseline_paths) != EXPECTED_V1_1_BASELINE_COUNT
        or len(set(baseline_paths)) != EXPECTED_V1_1_BASELINE_COUNT
    ):
        raise ValueError("v1.1 stable compatibility baseline is not 238 unique paths")

    # build_proposal canonicalizes entry ordering, so compare the frozen baseline
    # by import path rather than by list position.
    current_entries = build_proposal(root, baseline_paths)["entries"]
    expected_by_path = {entry["import_path"]: entry for entry in expected_entries}
    current_by_path = {entry["import_path"]: entry for entry in current_entries}
    if set(expected_by_path) != set(current_by_path):
        missing = sorted(set(expected_by_path) - set(current_by_path))
        extra = sorted(set(current_by_path) - set(expected_by_path))
        raise ValueError(
            "published v1.1 stable API paths drifted: "
            f"missing={missing!r}, extra={extra!r}"
        )
    changed = sorted(
        path
        for path in expected_by_path
        if expected_by_path[path] != current_by_path[path]
    )
    if changed:
        raise ValueError(
            "published v1.1 stable API/result contracts drifted: "
            + ", ".join(changed)
        )

    ensemble = importlib.import_module("ncmemsim.ensemble")
    export_order = list(ensemble.__all__)
    if len(export_order) != EXPECTED_ENSEMBLE_EXPORT_COUNT:
        raise ValueError("unexpected ncmemsim.ensemble export count")
    if len(set(export_order)) != EXPECTED_ENSEMBLE_EXPORT_COUNT:
        raise ValueError("duplicate ncmemsim.ensemble exports")

    addition_paths = [f"ncmemsim.ensemble.{name}" for name in export_order]
    if set(baseline_paths) & set(addition_paths):
        raise ValueError("Phase K additions overlap the v1.1 stable baseline")

    candidate = build_proposal(root, baseline_paths + addition_paths)
    by_path = {entry["import_path"]: entry for entry in candidate["entries"]}
    proposed_stable = [by_path[path] for path in addition_paths]

    return {
        "schema_version": 1,
        "status": "reviewed_candidate_surface_not_release_approval",
        "baseline_release": BASELINE_RELEASE,
        "baseline_release_commit": baseline_commit,
        "review_source_commit": source_commit,
        "candidate_version": CANDIDATE_VERSION,
        "development_version": DEVELOPMENT_VERSION,
        "stable_v1_1_exact_path_count": EXPECTED_V1_1_BASELINE_COUNT,
        "ensemble_addition_export_order": export_order,
        "proposed_stable_additions": proposed_stable,
        "public_provisional_additions": [],
        "public_importable_not_separately_stable_modules": IMPLEMENTATION_MODULES,
        "internal_policy": (
            "Private implementation helpers, including "
            "ncmemsim.ensemble._serialization, are not public API. Direct imports "
            "from implementation modules remain outside the separately frozen "
            "stable-alias proposal unless represented by an explicit package-level "
            "ncmemsim.ensemble export."
        ),
        "selection_rationale": (
            "All 59 explicit ncmemsim.ensemble package exports are proposed as "
            "stable additive v1.2 API. Phase K introduced them through the package "
            "__all__ surface, froze their scientific contracts incrementally, "
            "uses immutable result/specification objects where applicable, and "
            "completed deterministic identity, failure-accounting and reporting "
            "gates without modifying the published v1.1 stable API."
        ),
        "public_provisional_rationale": (
            "No explicit ncmemsim.ensemble package export is classified as "
            "public provisional in the K7a candidate review. Lower-level "
            "implementation-module paths are importable but are not separately "
            "proposed as stable aliases."
        ),
        "result_semantics_review": RESULT_SEMANTICS_REVIEW,
    }


def write_review(
    root: Path = ROOT,
    output: Path | None = None,
) -> Path:
    """Write the canonical v1.2 API review JSON."""

    target = output if output is not None else root / "docs/v1_2_api_review.json"
    review = build_review(root)
    target.write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def main() -> int:
    try:
        target = write_review()
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        ImportError,
        subprocess.CalledProcessError,
    ) as exc:
        print("v1.2 API/result review build FAIL:", exc, file=sys.stderr)
        return 1

    review = _load_json(target)
    print(
        "v1.2 API/result review built: "
        f"{review['stable_v1_1_exact_path_count']} retained v1.1 stable paths + "
        f"{len(review['proposed_stable_additions'])} proposed stable additions + "
        f"{len(review['public_provisional_additions'])} public provisional additions; "
        "release approval not implied."
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
