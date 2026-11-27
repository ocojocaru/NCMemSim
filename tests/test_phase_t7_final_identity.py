# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Verify published identity and rejection of stale or duplicated citation fields."""
from pathlib import Path
import shutil

import pytest

from scripts.validate_v1_11_release_identity import ROOT, validate_identity, validate_retained


PUBLISHED = ROOT / 'tests/fixtures/releases/v1_11_0'


def test_published_identity():
    validate_retained(ROOT)
    validate_identity(PUBLISHED)


@pytest.mark.parametrize('line', ['doi: 10.5281/zenodo.23973765', 'version: 1.11.0'])
def test_invalid_citation_rejected(tmp_path, line):
    (tmp_path / 'ncmemsim').mkdir()
    shutil.copyfile(PUBLISHED / 'ncmemsim/_version.py', tmp_path / 'ncmemsim/_version.py')
    citation = Path(PUBLISHED / 'CITATION.cff').read_text(encoding='utf-8')
    (tmp_path / 'CITATION.cff').write_text(citation + line + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='published citation'):
        validate_identity(tmp_path)
