"""Verify the release archive and offline resources before Pages deployment."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile

def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    return path

def prepare(archive, output):
    metadata = json.loads(Path(__file__).with_name('release-package.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == metadata['sha256'], 'Archive SHA-256 mismatch'
    assert not output.exists(), 'Output directory already exists'
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert len(names) == len(set(names)), 'Duplicate ZIP paths'
        assert sum(x.file_size for x in bundle.infolist()) < 1_000_000_000, 'Pages size limit exceeded'
        for entry in bundle.infolist():
            safe_path(entry.filename)
            assert not stat.S_ISLNK(entry.external_attr >> 16), 'Symlink not allowed'
        for required in ('index.html', 'sw.js', 'manifest.webmanifest', 'offline-manifest.json'):
            assert required in names, f'Missing root entry: {required}'
        manifest = json.loads(bundle.read('offline-manifest.json'))
        assert manifest['id'] == metadata['release_id'], 'Release identity mismatch'
        total = 0
        for resource in manifest['resources']:
            safe_path(resource['path'])
            data = bundle.read(resource['path'])
            assert len(data) == resource['bytes'], resource['path']
            assert hashlib.sha256(data).hexdigest() == resource['sha256'], resource['path']
            total += len(data)
        assert total == manifest['bytes'], 'Manifest size mismatch'
        bundle.extractall(output)
    (output / '.nojekyll').touch()
    print(f"Verified {len(names)} files; {len(manifest['resources'])} offline resources; release {manifest['id']}")

if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
