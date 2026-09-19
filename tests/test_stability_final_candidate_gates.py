"""Final candidate gate metadata records a complete candidate-ready state."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_final_candidate_gates import validate


ROOT = Path(__file__).resolve().parents[1]


def test_final_candidate_gate_plan_is_complete():
    plan = validate(ROOT)
    assert plan["status"] == "passed"
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    assert readiness["ready_for_candidate"] is True
    states = {check["id"]: check for check in readiness["final_candidate_checks"]}
    assert all(item["state"] == "passed" for item in states.values())
    assert set(plan["completed_evidence"]) == set(states)


@pytest.mark.parametrize("fault", ["status", "ready_false", "missing_evidence", "remote_notrun"])
def test_final_candidate_gate_plan_rejects_incomplete_final_state(tmp_path, fault):
    import shutil

    shutil.copytree(ROOT / "docs", tmp_path / "docs")
    shutil.copytree(ROOT / "ncmemsim", tmp_path / "ncmemsim")
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    plan_path = tmp_path / "docs/final_candidate_gates.json"
    readiness_path = tmp_path / "docs/release_readiness.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    if fault == "status":
        plan["status"] = "configured_not_run"
    elif fault == "ready_false":
        readiness["ready_for_candidate"] = False
    elif fault == "missing_evidence":
        plan["completed_evidence"].pop("clean_installed_distributions")
    else:
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "remote_documentation":
                check["state"] = "not_run"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
    with pytest.raises(ValueError):
        validate(tmp_path)
