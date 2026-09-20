from __future__ import annotations

import json
from pathlib import Path
import re

import ncmemsim


ROOT = Path(__file__).resolve().parents[1]


def test_j0_uses_development_version_and_retains_stable_citation():
    assert ncmemsim.__version__ == "1.1.0.dev0"
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"(?m)^version:\s*['\"]?([^'\"\s]+)", citation)
    assert match and match.group(1) == "1.0.0"


def test_j0_scope_freezes_v1_behavior_and_has_no_implemented_physics_claim():
    page = (ROOT / "docs/advanced_transport.md").read_text(encoding="utf-8")
    for required in (
        "J0 only",
        "New mechanisms are disabled by default",
        "reproduce that baseline exactly when disabled",
        "does not yet add trap-assisted transport",
        "Synthetic examples demonstrate deterministic implementation behavior only",
        "J7 - final release gates",
    ):
        assert required in page


def test_j0_navigation_and_source_distribution_include_scope_page():
    assert "Advanced transport physics: advanced_transport.md" in (
        ROOT / "mkdocs.yml"
    ).read_text(encoding="utf-8")
    validator = (ROOT / "scripts/validate_dtco_distribution.py").read_text(
        encoding="utf-8"
    )
    assert "'docs/advanced_transport.md'" in validator


def test_development_pushes_do_not_trigger_expensive_actions():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    docs = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert 'branches: ["main"]' in ci
    assert 'branches: ["main"]' in docs
    assert "dev/v1.1.0-advanced-transport" not in ci + docs
    assert "workflow_dispatch:" in ci and "workflow_dispatch:" in docs


def test_approved_v1_surface_remains_the_compatibility_baseline():
    proposal = json.loads(
        (ROOT / "docs/stable_api_proposal.json").read_text(encoding="utf-8")
    )
    assert proposal["status"] == "approved_for_v1_release"
    assert proposal["preparation_version"] == "1.0.0"
    assert len(proposal["entries"]) == 204


def test_runtime_version_literal_is_not_frozen_as_an_api_signature():
    inventory = json.loads(
        (ROOT / "docs/api_inventory.json").read_text(encoding="utf-8")
    )
    module = next(
        item for item in inventory["modules"] if item["module"] == "ncmemsim._version"
    )
    version = next(
        item for item in module["public_assignments"] if item["name"] == "__version__"
    )
    assert version["expression"] == "<runtime-version>"
