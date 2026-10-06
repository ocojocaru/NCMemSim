# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Published identity fixtures independent of current development version."""
from pathlib import Path
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def published_v1_3_copy(tmp_path, monkeypatch):
    for folder in ('docs', 'ncmemsim'):
        shutil.copytree(ROOT/folder, tmp_path/folder)
    for name in ('README.md', 'CHANGELOG.md', 'CITATION.cff'):
        shutil.copyfile(ROOT/name, tmp_path/name)
    snapshots = ROOT/'tests/fixtures/releases/v1_3_0'
    for source in snapshots.rglob('*'):
        if source.is_file():
            destination = tmp_path/source.relative_to(snapshots)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    from scripts import validate_v1_3_api_review as gate
    monkeypatch.setattr(gate, '__version__', '1.3.0')
    return tmp_path


@pytest.fixture
def published_v1_4_copy(tmp_path):
    destination=tmp_path/'published-v1_4'
    for folder in ('docs','ncmemsim','tests/fixtures','.github'):
        shutil.copytree(ROOT/folder,destination/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):
        shutil.copyfile(ROOT/name,destination/name)
    snapshots=ROOT/'tests/fixtures/releases/v1_4_0'
    for source in snapshots.rglob('*'):
        if source.is_file():
            target=destination/source.relative_to(snapshots)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
    return destination
