"""Validate recorded remote final candidate gate evidence."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

REMOTE_GATES = {"supported_runtime_ci", "remote_documentation"}
LOCAL_GATES = {"full_local_regression", "strict_documentation_audit", "clean_installed_distributions"}


def _version(root: Path) -> str:
    tree = ast.parse((root / "ncmemsim/_version.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    raise ValueError("missing package version")


def validate(root: Path) -> dict:
    evidence = json.loads((root / "docs/final_candidate_remote_evidence.json").read_text(encoding="utf-8"))
    if evidence.get("schema_version") != 1:
        raise ValueError("unsupported remote evidence schema")
    if evidence.get("preparation_version") != _version(root):
        raise ValueError("remote evidence preparation version differs from package")
    if evidence.get("source_branch") != "prep/v1.0-stability":
        raise ValueError("unexpected remote evidence source branch")
    if evidence.get("status") != "passed_pending_evidence_commit_confirmation":
        raise ValueError("unexpected remote evidence status")
    if not re.fullmatch(r"[0-9a-f]{40}", evidence.get("verified_commit", "")):
        raise ValueError("invalid verified commit")
    checks = {item["id"]: item for item in evidence.get("verified_checks", [])}
    if set(checks) != REMOTE_GATES:
        raise ValueError("remote gate evidence inventory changed")
    if any(item.get("state") != "passed" or not item.get("workflow") for item in checks.values()):
        raise ValueError("remote gate evidence is incomplete")
    if set(evidence.get("not_covered", [])) != LOCAL_GATES:
        raise ValueError("local gates must remain outside remote evidence")

    readiness = json.loads((root / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {item["id"]: item for item in readiness["final_candidate_checks"]}
    if {gate for gate, item in states.items() if item["state"] == "passed"} != REMOTE_GATES:
        raise ValueError("only remote gates may be marked passed in this step")
    if {gate for gate, item in states.items() if item["state"] == "not_run"} != LOCAL_GATES:
        raise ValueError("local gates must remain not_run")
    if readiness["ready_for_candidate"] is not False:
        raise ValueError("candidate readiness must remain false until local gates pass")
    for gate in REMOTE_GATES:
        if set(states[gate]["evidence"]) != {"docs/final_candidate_remote_evidence.md", "docs/final_candidate_remote_evidence.json"}:
            raise ValueError("remote gate evidence paths changed")
    return evidence


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        evidence = validate(root)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("Remote candidate gate evidence FAIL:", exc, file=sys.stderr)
        return 1
    print("Remote candidate gate evidence PASS: " + evidence["verified_commit"] + "; local final gates remain not_run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
