"""Release gate detects missing or stale audited source content."""
import io
import tarfile
import pytest
from scripts.validate_dtco_distribution import REQUIRED, SOURCE_REQUIRED, check_source_content

@pytest.mark.parametrize('fault', [None, 'missing', 'changed', 'duplicate'])
def test_audited_source_bytes(tmp_path, fault):
    root = tmp_path / 'checkout'
    names = REQUIRED | SOURCE_REQUIRED | {'README.md', 'MANIFEST.in', 'docs/assets/new.svg'}
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('audited ' + name).encode())
    archive_path = tmp_path / 'release.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        for name in sorted(names):
            if name == 'docs/assets/new.svg' and fault == 'missing':
                continue
            content = (root / name).read_bytes()
            if name == 'docs/assets/new.svg' and fault == 'changed':
                content = b'stale asset'
            member = tarfile.TarInfo('release/' + name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
            if name == 'docs/assets/new.svg' and fault == 'duplicate':
                archive.addfile(member, io.BytesIO(content))
    if fault:
        with pytest.raises(ValueError, match='docs/assets/new.svg'):
            check_source_content(archive_path, root)
    else:
        assert check_source_content(archive_path, root) == len(names)

@pytest.mark.parametrize('kind', ['wheel', 'sdist'])
@pytest.mark.parametrize('name', ['sampling', 'propagation', 'sample_analysis', 'robust', 'robust_reporting'])
def test_robust_module_required(tmp_path, kind, name):
    import zipfile
    from scripts.validate_dtco_distribution import check_archive
    missing = f'ncmemsim/dtco/{name}.py'
    names = (REQUIRED if kind == 'wheel' else REQUIRED | SOURCE_REQUIRED) - {missing}
    path = tmp_path / ('release.whl' if kind == 'wheel' else 'release.tar.gz')
    if kind == 'wheel':
        with zipfile.ZipFile(path, 'w') as archive:
            for item in names:
                archive.writestr(item, '')
    else:
        with tarfile.open(path, 'w:gz') as archive:
            for item in names:
                archive.addfile(tarfile.TarInfo('release/' + item), io.BytesIO(b''))
    with pytest.raises(ValueError, match=missing):
        check_archive(path)
