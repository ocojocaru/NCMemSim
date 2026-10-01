# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Validate the published v1.2.0 release identity without rewriting published v1.0/v1.1 evidence."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import sys


EXPECTED_RELEASE = "1.2.0"
RELEASE_DATE = "2026-09-30"
PREVIOUS_STABLE = "1.1.0"
PREVIOUS_STABLE_RELEASE_COMMIT = "3e926fccb3a02a1d0682941e52f48439d87a3733"
K7A_REVIEW_SOURCE_COMMIT = "b762dc10debabafcfc0aeb9e5b3788745773c14b"

HISTORICAL_JSON_SHA256 = {
    "docs/archival_citation.json": "3d3d01b928a3816d6f6c447abf0aa6f3a1950f520bac08bd842e5a06d8296f74",
    "docs/final_candidate_clean_distributions.json": "c96ee92b1406e79c12800a92d462b7cf1cf3a55812cfcc3a75a118a778b580e4",
    "docs/final_candidate_gates.json": "4dd604272cc02d49979921c3bfd72b30b6ddc47256b82231e20492384afa7a9a",
    "docs/final_candidate_local_regression.json": "2f498edb2f25956967f0f6bef09ffd4fe161476e9c0f0c420ffdbed7defdbc8d",
    "docs/final_candidate_remote_evidence.json": "b26aceb101f79fe2aabce9d2c0cea71d40b3750401e1e00bf7b8bcfb5b1082e1",
    "docs/final_candidate_strict_documentation.json": "796d5817b2706f5fb24bbff66691e76bfac3d053f5c9131d225556445f575247",
    "docs/release_readiness.json": "a3e79052b56379d94d3896e69379854b4cd7855102ce65d359c3f4c21ace3158",
    "docs/stable_api_proposal.json": "f81ceea1e665a86b36bd96a07a5570cafc838ae45ac6670c4f4221f310ebdffa",
    "docs/v1_1_api_review.json": "cd3f019c57adb6e1d1370c02ca594e2e4ac3f3e28da3e8004d4cecce53697690",
}


def _package_version(root: Path) -> str:
    tree = ast.parse((root / "ncmemsim/_version.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    raise ValueError("missing package version")


def _citation_field(text: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)}:\s*['\"]?([^'\"\n]+)", text)
    if not match:
        raise ValueError("missing citation field: " + field)
    return match.group(1).strip()


def _semantic_json_digest(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    encoded = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(root: Path) -> dict:
    package_version = _package_version(root)
    if package_version != EXPECTED_RELEASE:
        raise ValueError(
            f"package version must be {EXPECTED_RELEASE}, got {package_version}"
        )

    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    if "doi:" in citation.lower():
        raise ValueError("CITATION.cff must not claim an unassigned DOI")
    if _citation_field(citation, "version") != EXPECTED_RELEASE:
        raise ValueError("CITATION.cff version must match the v1.2.0 release")
    if _citation_field(citation, "date-released") != RELEASE_DATE:
        raise ValueError(f"CITATION.cff date-released must be {RELEASE_DATE}")

    for name, expected in HISTORICAL_JSON_SHA256.items():
        if _semantic_json_digest(root / name) != expected:
            raise ValueError("historical snapshot changed: " + name)

    review = json.loads(
        (root / "docs/v1_2_api_review.json").read_text(encoding="utf-8")
    )
    if review.get("schema_version") != 1:
        raise ValueError("unsupported v1.2 API review schema")
    if review.get("status") != "reviewed_candidate_surface_not_release_approval":
        raise ValueError("K7a API review status changed")
    if review.get("baseline_release") != "v1.1.0":
        raise ValueError("K7a baseline release changed")
    if review.get("baseline_release_commit") != PREVIOUS_STABLE_RELEASE_COMMIT:
        raise ValueError("K7a v1.1 baseline commit changed")
    if review.get("review_source_commit") != K7A_REVIEW_SOURCE_COMMIT:
        raise ValueError("K7a review source commit changed")
    if review.get("candidate_version") != EXPECTED_RELEASE:
        raise ValueError("K7a candidate version changed")
    if review.get("development_version") != "1.2.0.dev0":
        raise ValueError("K7a development provenance changed")
    if review.get("stable_v1_1_exact_path_count") != 238:
        raise ValueError("unexpected retained v1.1 stable-path count")

    additions = review.get("proposed_stable_additions", [])
    provisional = review.get("public_provisional_additions", [])
    export_order = review.get("ensemble_addition_export_order", [])
    if len(additions) != 59 or len(export_order) != 59:
        raise ValueError("unexpected v1.2 proposed stable API count")
    if provisional != []:
        raise ValueError("v1.2 review must retain zero public provisional additions")

    addition_paths = [item.get("import_path") for item in additions]
    if len(set(addition_paths)) != 59:
        raise ValueError("v1.2 proposed stable additions are not unique")
    if any(
        not isinstance(path, str) or not path.startswith("ncmemsim.ensemble.")
        for path in addition_paths
    ):
        raise ValueError("v1.2 stable additions escaped the reviewed ensemble surface")

    readme = (root / "README.md").read_text(encoding="utf-8")
    if "**Current stable release:** `1.2.0`" not in readme:
        raise ValueError("README does not identify v1.2.0 as the current stable release")
    if "**Latest published stable release:** `1.1.0`" in readme:
        raise ValueError("README still identifies v1.1.0 as the latest stable release")

    index = (root / "docs/index.md").read_text(encoding="utf-8")
    if (
        "Version `1.2.0` completes Phase K and is the current stable release."
        not in index
    ):
        raise ValueError(
            "documentation index does not identify the completed v1.2.0 release"
        )

    roadmap = (root / "docs/roadmap.md").read_text(encoding="utf-8")
    if "released as `v1.2.0`" not in roadmap:
        raise ValueError("roadmap does not identify v1.2.0 as released")
    if "released as `v1.1.0`" not in roadmap:
        raise ValueError("roadmap no longer retains the published v1.1.0 baseline")

    phase_k = (root / "docs/stochastic_ensembles.md").read_text(encoding="utf-8")
    if (
        "**Status: released as `v1.2.0`; all required exact-candidate local and remote release gates passed.**"
        not in phase_k
    ):
        raise ValueError(
            "Phase K status does not identify the completed v1.2.0 release"
        )
    if "package identity `1.2.0.dev0`" not in phase_k:
        raise ValueError("K7b development-version provenance was not retained")

    return {
        "release_version": EXPECTED_RELEASE,
        "previous_stable_release": PREVIOUS_STABLE,
        "citation_date": RELEASE_DATE,
        "stable_v1_1_paths_retained": 238,
        "v1_2_proposed_stable_additions": 59,
        "v1_2_public_provisional_additions": 0,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        result = validate(root)
    except (ValueError, KeyError, TypeError, OSError, SyntaxError) as exc:
        print("v1.2 release identity FAIL:", exc, file=sys.stderr)
        return 1
    print(
        "v1.2 release identity PASS: "
        f"{result['release_version']} release ({result['citation_date']}); "
        f"{result['stable_v1_1_paths_retained']} retained v1.1 stable paths; "
        f"{result['v1_2_proposed_stable_additions']} proposed stable + "
        f"{result['v1_2_public_provisional_additions']} public provisional additions; "
        "published v1.0/v1.1 evidence retained."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
