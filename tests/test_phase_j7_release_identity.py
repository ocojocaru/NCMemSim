from __future__ import annotations

import json
import shutil
import pytest
from pathlib import Path

from scripts.validate_v1_1_release_identity import HISTORICAL_JSON_SHA256, validate

ROOT = Path(__file__).resolve().parents[1]


def test_v1_1_final_version_identity_is_aligned():
    result = validate(ROOT)
    assert result["release_version"] == "1.1.0"
    assert result["previous_stable_release"] == "1.0.0"
    assert result["stable_v1_paths_retained"] == 204
    assert result["v1_1_proposed_stable_additions"] == 34
    assert result["v1_1_public_provisional_additions"] == 10


def test_v1_0_release_records_remain_historical():
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    archival = json.loads((ROOT / "docs/archival_citation.json").read_text(encoding="utf-8"))
    gates = json.loads((ROOT / "docs/final_candidate_gates.json").read_text(encoding="utf-8"))
    assert readiness["preparation_version"] == "1.0.0"
    assert archival["final_release_version"] == "1.0.0"
    assert gates["preparation_version"] == "1.0.0"


def test_j7a_review_retains_development_provenance():
    review = json.loads((ROOT / "docs/v1_1_api_review.json").read_text(encoding="utf-8"))
    assert review["candidate_version"] == "1.1.0"
    assert review["development_version"] == "1.1.0.dev0"
    assert review["status"] == "reviewed_candidate_surface_not_release_approval"


@pytest.fixture
def candidate_copy(tmp_path):
    files = list(HISTORICAL_JSON_SHA256) + [
        "CITATION.cff", "ncmemsim/_version.py", "README.md",
        "docs/advanced_transport.md", "docs/roadmap.md",
    ]
    for name in files:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


@pytest.mark.parametrize("name", sorted(HISTORICAL_JSON_SHA256))
def test_identity_rejects_edits_anywhere_in_historical_snapshots(candidate_copy, name):
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
        path.write_text(json.dumps(data, indent=4, sort_keys=True), encoding="utf-8")
    assert validate(candidate_copy)["citation_date"] is None


@pytest.mark.parametrize("fault", ["package", "citation", "release_date", "doi"])
def test_identity_rejects_inconsistent_or_premature_identity(candidate_copy, fault):
    path = candidate_copy / "CITATION.cff"
    text = path.read_text(encoding="utf-8")
    if fault == "package":
        (candidate_copy / "ncmemsim/_version.py").write_text('__version__ = "1.1.0.dev0"\n')
    elif fault == "citation":
        text = text.replace("version: 1.1.0", "version: 1.0.0")
    elif fault == "release_date":
        text += "\ndate-released: 2026-09-23\n"
    else:
        text += "\ndoi: 10.0000/unassigned\n"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        validate(candidate_copy)


def test_archival_validator_rejects_rewritten_historical_citation(candidate_copy):
    from scripts.validate_archival_citation import validate as validate_archival

    path = candidate_copy / "docs/archival_citation.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["current_citation_version"] = "0.9.0"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="historical citation version"):
        validate_archival(candidate_copy)
