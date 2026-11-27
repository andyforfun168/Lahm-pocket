"""Verify the release archive and offline resources before Pages deployment."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile

def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    return path

def validate_offline_manifest(manifest):
    assert manifest.get('schema') == 1, 'Invalid offline schema'
    assert re.fullmatch(r'[-a-zA-Z0-9.]{1,48}', manifest.get('version', '')), 'Invalid offline version'
    assert re.fullmatch(r'r[a-f0-9]{24}', manifest.get('id', '')), 'Invalid offline release ID'
    resources = manifest.get('resources')
    assert isinstance(resources, list) and 2 <= len(resources) <= 3000, 'Invalid offline resource count'
    seen = set()
    for entry in resources:
        path = entry.get('path', '')
        assert isinstance(path, str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9/_.-]*', path), f'Invalid offline path: {path}'
        assert not any(part in ('', '.', '..') or part.startswith('.') or part == '__MACOSX' for part in path.split('/')), f'Hidden or unsafe offline file: {path}'
        assert path not in seen, f'Duplicate offline path: {path}'
        seen.add(path)
        assert re.fullmatch(r'[a-f0-9]{64}', entry.get('sha256', '')), f'Invalid offline digest: {path}'
        assert type(entry.get('bytes')) is int and 0 <= entry['bytes'] <= 64*1024**2, f'Invalid offline size: {path}'
    assert {'index.html', 'manifest.webmanifest'} <= seen, 'Missing offline entry point'
    assert manifest.get('bytes') == sum(entry['bytes'] for entry in resources) <= 1024**3, 'Invalid offline total size'

def prepare(archive, output):
    metadata = json.loads(Path(__file__).with_name('release-package.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == metadata['sha256'], 'Archive SHA-256 mismatch'
    assert not output.exists(), 'Output directory already exists'
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert len(names) == len(set(names)), 'Duplicate ZIP paths'
        assert not any('lab-' in p or p.endswith('pairing.json') or p.endswith('TEST-README.md') for p in names), 'Test build must never be deployed'
        assert sum(x.file_size for x in bundle.infolist()) < 1_000_000_000, 'Pages size limit exceeded'
        for entry in bundle.infolist():
            path = safe_path(entry.filename)
            assert not any(part.startswith('.') or part == '__MACOSX' for part in path.parts), 'System metadata must not be published'
            assert not stat.S_ISLNK(entry.external_attr >> 16), 'Symlink not allowed'
        for required in ('index.html', 'sw.js', 'manifest.webmanifest', 'offline-manifest.json'):
            assert required in names, f'Missing root entry: {required}'
        manifest = json.loads(bundle.read('offline-manifest.json'))
        validate_offline_manifest(manifest)
        assert manifest['id'] == metadata['release_id'], 'Release identity mismatch'
        if 'release-version.json' in names:
            version_marker = json.loads(bundle.read('release-version.json'))
            expected_marker = {key: manifest[key] for key in ('schema', 'id', 'version')}
            assert version_marker == expected_marker, 'Release version marker mismatch'
        allowed = {r['path'] for r in manifest['resources']} | {'sw.js', 'offline-manifest.json'}
        online_files = metadata.get('online_files', [])
        assert isinstance(online_files, list) and all(isinstance(name, str) for name in online_files), 'Invalid online file list'
        online = set(online_files)
        assert len(online) == len(online_files) and not online & allowed, 'Duplicate online file'
        assert all(name == '_headers' or name.startswith('assets/') for name in online), 'Invalid online file'
        assert set(names) == allowed | online, 'Undeclared files in normal release'
        assert b'lab-entry' not in bundle.read('index.html'), 'Test entry is not allowed'
        push_meta = b'<meta name="ramu-push-api" content="https://pocket-lahm-reminders.pocket-lahm-168.workers.dev/">'
        assert bundle.read('index.html').count(push_meta) == 1, 'Production push endpoint is missing'
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
