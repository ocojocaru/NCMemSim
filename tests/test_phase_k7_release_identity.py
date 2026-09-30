from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.validate_v1_2_release_identity import (
    HISTORICAL_JSON_SHA256,
    validate,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v1_2_final_version_identity_is_aligned():
    result = validate(ROOT)
    assert result["release_version"] == "1.2.0"
    assert result["previous_stable_release"] == "1.1.0"
    assert result["citation_date"] == "2026-09-30"
    assert result["stable_v1_1_paths_retained"] == 238
    assert result["v1_2_proposed_stable_additions"] == 59
    assert result["v1_2_public_provisional_additions"] == 0


def test_k7a_review_retains_development_provenance():
    review = json.loads(
        (ROOT / "docs/v1_2_api_review.json").read_text(encoding="utf-8")
    )
    assert review["baseline_release"] == "v1.1.0"
    assert review["baseline_release_commit"] == (
        "3e926fccb3a02a1d0682941e52f48439d87a3733"
    )
    assert review["review_source_commit"] == (
        "b762dc10debabafcfc0aeb9e5b3788745773c14b"
    )
    assert review["candidate_version"] == "1.2.0"
    assert review["development_version"] == "1.2.0.dev0"
    assert review["stable_v1_1_exact_path_count"] == 238
    assert len(review["proposed_stable_additions"]) == 59
    assert review["public_provisional_additions"] == []
    assert review["status"] == "reviewed_candidate_surface_not_release_approval"


@pytest.fixture
def candidate_copy(tmp_path):
    files = list(HISTORICAL_JSON_SHA256) + [
        "docs/v1_2_api_review.json",
        "CITATION.cff",
        "ncmemsim/_version.py",
        "README.md",
        "docs/index.md",
        "docs/roadmap.md",
        "docs/stochastic_ensembles.md",
    ]
    for name in files:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


@pytest.mark.parametrize("name", sorted(HISTORICAL_JSON_SHA256))
def test_identity_rejects_edits_anywhere_in_historical_snapshots(
    candidate_copy,
    name,
):
    path = candidate_copy / name
    data = json.loads(path.read_text(encoding="utf-8"))
    data["unreviewed_evidence"] = "changed"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="historical snapshot changed"):
        validate(candidate_copy)


def test_identity_accepts_historical_json_formatting_changes(candidate_copy):
    for name in HISTORICAL_JSON_SHA256:
        path = candidate_copy / name
        data = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(
            json.dumps(data, indent=4, sort_keys=True),
            encoding="utf-8",
        )
    assert validate(candidate_copy)["citation_date"] == "2026-09-30"


@pytest.mark.parametrize(
    "fault",
    ["package", "citation", "release_date", "doi"],
)
def test_identity_rejects_inconsistent_or_premature_identity(
    candidate_copy,
    fault,
):
    citation_path = candidate_copy / "CITATION.cff"
    text = citation_path.read_text(encoding="utf-8")
    if fault == "package":
        (candidate_copy / "ncmemsim/_version.py").write_text(
            '__version__ = "1.2.0.dev0"\n',
            encoding="utf-8",
        )
    elif fault == "citation":
        text = text.replace("version: 1.2.0", "version: 1.1.0")
    elif fault == "release_date":
        text = text.replace(
            "date-released: 2026-09-30",
            "date-released: 2026-09-29",
        )
    else:
        text += "\ndoi: 10.0000/unassigned\n"
    citation_path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        validate(candidate_copy)


@pytest.mark.parametrize(
    "field,value",
    [
        ("baseline_release", "v1.0.0"),
        ("candidate_version", "1.1.0"),
        ("development_version", "1.2.0.dev1"),
        ("stable_v1_1_exact_path_count", 237),
    ],
)
def test_identity_rejects_changed_k7a_review_provenance(
    candidate_copy,
    field,
    value,
):
    path = candidate_copy / "docs/v1_2_api_review.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data[field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        validate(candidate_copy)


def test_identity_rejects_changed_v1_2_api_counts(candidate_copy):
    path = candidate_copy / "docs/v1_2_api_review.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["proposed_stable_additions"] = data["proposed_stable_additions"][:-1]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="proposed stable API count"):
        validate(candidate_copy)


@pytest.mark.parametrize("surface", ["readme", "index", "roadmap", "phase_k"])
def test_identity_rejects_stale_release_status(candidate_copy, surface):
    paths = {
        "readme": candidate_copy / "README.md",
        "index": candidate_copy / "docs/index.md",
        "roadmap": candidate_copy / "docs/roadmap.md",
        "phase_k": candidate_copy / "docs/stochastic_ensembles.md",
    }
    path = paths[surface]
    text = path.read_text(encoding="utf-8")
    replacements = {
        "readme": ("**Current stable release:** `1.2.0`", "stale"),
        "index": (
            "Version `1.2.0` completes Phase K and is the current stable release.",
            "stale",
        ),
        "roadmap": (
            "released as `v1.2.0`",
            "stale",
        ),
        "phase_k": (
            "**Status: released as `v1.2.0`; all required exact-candidate local and remote release gates passed.**",
            "stale",
        ),
    }
    old, new = replacements[surface]
    path.write_text(text.replace(old, new), encoding="utf-8")
    with pytest.raises(ValueError):
        validate(candidate_copy)
