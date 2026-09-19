"""Validate full local regression final-gate evidence."""
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
    evidence = json.loads((root / "docs/final_candidate_local_regression.json").read_text(encoding="utf-8"))
    if evidence.get("schema_version") != 1:
        raise ValueError("unsupported local regression evidence schema")
    if evidence.get("preparation_version") != _version(root):
        raise ValueError("local regression evidence version differs from package")
    if evidence.get("source_branch") != "prep/v1.0-stability":
        raise ValueError("unexpected local regression source branch")
    if not re.fullmatch(r"[0-9a-f]{40}", evidence.get("tested_commit", "")):
        raise ValueError("invalid tested commit")
    if evidence.get("status") != "passed":
        raise ValueError("unexpected local regression evidence status")
    if "passed" not in evidence.get("observed_result", ""):
        raise ValueError("local regression evidence must record a passed observed result")
    if "pytest" not in evidence.get("command", ""):
        raise ValueError("local regression evidence must record pytest command")
    if set(evidence.get("not_covered", [])) != {"strict_documentation_audit", "clean_installed_distributions"}:
        raise ValueError("local regression evidence must leave docs/distribution gates open")

    readiness = json.loads((root / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {item["id"]: item for item in readiness["final_candidate_checks"]}
    if states["full_local_regression"]["state"] != "passed":
        raise ValueError("full local regression gate must be passed")
    if set(states["full_local_regression"]["evidence"]) != {"docs/final_candidate_local_regression.md", "docs/final_candidate_local_regression.json"}:
        raise ValueError("full local regression evidence paths changed")
    for gate in ("strict_documentation_audit", "clean_installed_distributions"):
        if states[gate]["state"] != "not_run" or states[gate]["evidence"]:
            raise ValueError(gate + " must remain not_run")
    for gate in ("supported_runtime_ci", "remote_documentation"):
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
        print("Local regression gate evidence FAIL:", exc, file=sys.stderr)
        return 1
    print("Local regression gate evidence PASS: " + evidence["tested_commit"] + "; docs/distribution gates remain not_run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
