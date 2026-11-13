# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Verify candidate identity and rejection of stale or duplicated citation fields."""
from pathlib import Path
import shutil

import pytest

from scripts.validate_v1_11_release_identity import ROOT, validate_identity


def test_candidate_identity():
    validate_identity(ROOT)


@pytest.mark.parametrize('line', ['doi: 10.5281/zenodo.23973765', 'version: 1.11.0'])
def test_invalid_citation_rejected(tmp_path, line):
    (tmp_path / 'ncmemsim').mkdir()
    shutil.copyfile(ROOT / 'ncmemsim/_version.py', tmp_path / 'ncmemsim/_version.py')
    citation = Path(ROOT / 'CITATION.cff').read_text(encoding='utf-8')
    (tmp_path / 'CITATION.cff').write_text(citation + line + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='candidate citation'):
        validate_identity(tmp_path)
