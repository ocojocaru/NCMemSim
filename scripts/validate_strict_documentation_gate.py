"""Validate strict documentation final-gate evidence."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys


def _version(root: Path) -> str:
    tree = ast.parse((root / "ncmemsim/_version.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    raise ValueError("missing package version")


def validate(root: Path) -> dict:
    evidence = json.loads((root / "docs/final_candidate_strict_documentation.json").read_text(encoding="utf-8"))
    if evidence.get("schema_version") != 1:
        raise ValueError("unsupported strict documentation evidence schema")
    if evidence.get("preparation_version") != _version(root):
        raise ValueError("strict documentation evidence version differs from package")
    if evidence.get("source_branch") != "prep/v1.0-stability":
        raise ValueError("unexpected strict documentation source branch")
    if not re.fullmatch(r"[0-9a-f]{40}", evidence.get("tested_commit", "")):
        raise ValueError("invalid tested commit")
    if evidence.get("status") != "passed":
        raise ValueError("unexpected strict documentation evidence status")
    result = evidence.get("observed_result", "")
    for token in ("MkDocs strict build passed", "7070 local references", "116 Python"):
        if token not in result:
            raise ValueError("strict documentation evidence must record audited result details")
    if set(evidence.get("not_covered", [])) != {"clean_installed_distributions"}:
        raise ValueError("strict documentation evidence must leave clean distributions open")

    readiness = json.loads((root / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {item["id"]: item for item in readiness["final_candidate_checks"]}
    if states["strict_documentation_audit"]["state"] != "passed":
        raise ValueError("strict documentation gate must be passed")
    expected = {
        "docs/final_candidate_strict_documentation.md",
        "docs/final_candidate_strict_documentation.json",
        "scripts/validate_documentation.py",
    }
    if set(states["strict_documentation_audit"]["evidence"]) != expected:
        raise ValueError("strict documentation evidence paths changed")
    if states["clean_installed_distributions"]["state"] != "not_run" or states["clean_installed_distributions"]["evidence"]:
        raise ValueError("clean installed distributions must remain not_run")
    for gate in ("full_local_regression", "supported_runtime_ci", "remote_documentation"):
        if states[gate]["state"] != "passed":
            raise ValueError(gate + " must remain passed")
    if readiness["ready_for_candidate"] is not False:
        raise ValueError("candidate readiness must remain false until every final gate passes")
    return evidence


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        evidence = validate(root)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("Strict documentation gate evidence FAIL:", exc, file=sys.stderr)
        return 1
    print("Strict documentation gate evidence PASS: " + evidence["tested_commit"] + "; clean distribution gate remains not_run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
