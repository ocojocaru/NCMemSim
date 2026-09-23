"""Validate the v1.1.0 final-version candidate identity without rewriting v1.0 evidence."""
from __future__ import annotations

import ast
import json
import hashlib
from pathlib import Path
import re
import sys

EXPECTED_RELEASE = "1.1.0"
PREVIOUS_STABLE = "1.0.0"
# Semantic JSON digests from baseline 70a022f; independent of line endings.
# These snapshots are historical, including J7a, and are not v1.1 approval.
HISTORICAL_JSON_SHA256 = {
    "docs/archival_citation.json": "3d3d01b928a3816d6f6c447abf0aa6f3a1950f520bac08bd842e5a06d8296f74",
    "docs/final_candidate_clean_distributions.json": "c96ee92b1406e79c12800a92d462b7cf1cf3a55812cfcc3a75a118a778b580e4",
    "docs/final_candidate_gates.json": "4dd604272cc02d49979921c3bfd72b30b6ddc47256b82231e20492384afa7a9a",
    "docs/final_candidate_local_regression.json": "2f498edb2f25956967f0f6bef09ffd4fe161476e9c0f0c420ffdbed7defdbc8d",
    "docs/final_candidate_remote_evidence.json": "b26aceb101f79fe2aabce9d2c0cea71d40b3750401e1e00bf7b8bcfb5b1082e1",
    "docs/final_candidate_strict_documentation.json": "796d5817b2706f5fb24bbff66691e76bfac3d053f5c9131d225556445f575247",
    "docs/release_readiness.json": "a3e79052b56379d94d3896e69379854b4cd7855102ce65d359c3f4c21ace3158",
    "docs/stable_api_proposal.json": "f81ceea1e665a86b36bd96a07a5570cafc838ae45ac6670c4f4221f310ebdffa",
    "docs/v1_1_api_review.json": "cd3f019c57adb6e1d1370c02ca594e2e4ac3f3e28da3e8004d4cecce53697690"
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


def validate(root: Path) -> dict:
    package_version = _package_version(root)
    if package_version != EXPECTED_RELEASE:
        raise ValueError(f"package version must be {EXPECTED_RELEASE}, got {package_version}")

    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    if "doi:" in citation.lower():
        raise ValueError("CITATION.cff must not claim an unassigned DOI")
    if _citation_field(citation, "version") != EXPECTED_RELEASE:
        raise ValueError("CITATION.cff version must match the v1.1.0 candidate")
    if re.search(r"(?m)^date-released:", citation):
        raise ValueError("unpublished candidate must not claim a release date")

    for name, expected in HISTORICAL_JSON_SHA256.items():
        data = json.loads((root / name).read_text(encoding="utf-8"))
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        if hashlib.sha256(encoded).hexdigest() != expected:
            raise ValueError("historical snapshot changed: " + name)

    readiness = json.loads((root / "docs/release_readiness.json").read_text(encoding="utf-8"))
    if readiness.get("preparation_version") != PREVIOUS_STABLE or readiness.get("name") != "v1.0 stability preparation readiness" or readiness.get("ready_for_candidate") is not True:
        raise ValueError("historical v1.0 readiness evidence changed")

    archival = json.loads((root / "docs/archival_citation.json").read_text(encoding="utf-8"))
    if archival.get("preparation_version") != PREVIOUS_STABLE or archival.get("current_citation_version") != PREVIOUS_STABLE or archival.get("final_release_version") != PREVIOUS_STABLE:
        raise ValueError("historical v1.0 archival evidence changed")

    final_gates = json.loads((root / "docs/final_candidate_gates.json").read_text(encoding="utf-8"))
    if final_gates.get("preparation_version") != PREVIOUS_STABLE or final_gates.get("name") != "v1.0 final candidate gate plan" or final_gates.get("status") != "passed":
        raise ValueError("historical v1.0 final-gate evidence changed")

    review = json.loads((root / "docs/v1_1_api_review.json").read_text(encoding="utf-8"))
    if review.get("baseline_release") != "v1.0.0" or review.get("candidate_version") != EXPECTED_RELEASE or review.get("development_version") != "1.1.0.dev0" or review.get("status") != "reviewed_candidate_surface_not_release_approval":
        raise ValueError("J7a API review provenance changed")
    if len(review.get("proposed_stable_additions", [])) != 34:
        raise ValueError("unexpected v1.1 proposed stable API count")
    if len(review.get("public_provisional_additions", [])) != 10:
        raise ValueError("unexpected v1.1 provisional API count")

    readme = (root / "README.md").read_text(encoding="utf-8")
    if "**Current release candidate version:** `1.1.0`" not in readme:
        raise ValueError("README does not identify the v1.1.0 release candidate")
    if "**Latest published stable release:** `1.0.0`" not in readme:
        raise ValueError("README must retain v1.0.0 as the latest published release before tagging")

    advanced = (root / "docs/advanced_transport.md").read_text(encoding="utf-8")
    if "The current `1.1.0` final-version candidate" not in advanced:
        raise ValueError("advanced-transport status is not at J7c")

    roadmap = (root / "docs/roadmap.md").read_text(encoding="utf-8")
    if "J7c final-version candidate prepared" not in roadmap:
        raise ValueError("roadmap is not at J7c")

    return {
        "release_version": EXPECTED_RELEASE,
        "previous_stable_release": PREVIOUS_STABLE,
        "citation_date": None,
        "stable_v1_paths_retained": 204,
        "v1_1_proposed_stable_additions": 34,
        "v1_1_public_provisional_additions": 10,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        result = validate(root)
    except (ValueError, KeyError, TypeError, OSError, SyntaxError) as exc:
        print("v1.1 release identity FAIL:", exc, file=sys.stderr)
        return 1
    print(
        "v1.1 release identity PASS: "
        f"{result['release_version']} candidate; "
        f"{result['stable_v1_paths_retained']} retained v1 paths; "
        f"{result['v1_1_proposed_stable_additions']} proposed stable + "
        f"{result['v1_1_public_provisional_additions']} public provisional additions; "
        "historical v1.0 release evidence retained; v1.1 release approval not implied."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
