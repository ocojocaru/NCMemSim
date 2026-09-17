"""Distribution validator rejects incomplete wheel and source archives."""
import io
import tarfile
import zipfile
import pytest
from scripts.validate_dtco_distribution import REQUIRED, check_archive

@pytest.mark.parametrize('kind', ['wheel', 'sdist'])
@pytest.mark.parametrize('complete', [True, False])
def test_archive_module_inventory(tmp_path, kind, complete):
    names = sorted(REQUIRED)
    if not complete:
        names.remove('ncmemsim/dtco/reporting.py')
    if kind == 'wheel':
        path = tmp_path / 'ncmemsim.whl'
        with zipfile.ZipFile(path, 'w') as archive:
            for name in names:
                archive.writestr(name, '')
    else:
        path = tmp_path / 'ncmemsim.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            for name in names:
                member = tarfile.TarInfo('ncmemsim-0.12.0.dev0/' + name)
                archive.addfile(member, io.BytesIO(b''))
    if complete:
        check_archive(path)
    else:
        with pytest.raises(ValueError, match='reporting.py'):
            check_archive(path)
