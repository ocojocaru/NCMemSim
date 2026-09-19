"""Clean installed distribution gate records final candidate readiness."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_clean_distribution_gate import validate_evidence


ROOT = Path(__file__).resolve().parents[1]


def test_clean_distribution_gate_marks_candidate_ready():
    evidence = validate_evidence(ROOT)
    assert evidence["status"] == "passed"
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    assert readiness["ready_for_candidate"] is True
    states = {check["id"]: check for check in readiness["final_candidate_checks"]}
    assert all(check["state"] == "passed" for check in states.values())
    assert "scripts/validate_clean_distribution_gate.py" in states["clean_installed_distributions"]["evidence"]


@pytest.mark.parametrize("fault", ["ready_false", "clean_not_run", "missing_evidence", "wrong_version"])
def test_clean_distribution_gate_rejects_inconsistent_metadata(tmp_path, fault):
    import shutil

    shutil.copytree(ROOT / "docs", tmp_path / "docs")
    shutil.copytree(ROOT / "ncmemsim", tmp_path / "ncmemsim")
    shutil.copytree(ROOT / "scripts", tmp_path / "scripts")
    readiness_path = tmp_path / "docs/release_readiness.json"
    evidence_path = tmp_path / "docs/final_candidate_clean_distributions.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if fault == "ready_false":
        readiness["ready_for_candidate"] = False
    elif fault == "clean_not_run":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["state"] = "not_run"
    elif fault == "missing_evidence":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["evidence"] = []
    else:
        evidence["preparation_version"] = "0.0.0"
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(ValueError):
        validate_evidence(tmp_path)
