"""Permanent runtime selection and integrity checks; source release gates stay in CI."""
import hashlib
import json
from pathlib import Path
import stat

MANIFEST = 'runtime-manifest.json'
TREES = {'bin', 'lib', 'modules', 'config', 'compatibility', 'host', 'LICENSES', 'docs'}
FILES = {'VERSION', 'LICENSE', 'README.md', 'THIRD-PARTY-NOTICES.md', 'install.sh',
         'uninstall.sh', 'bootstrap.sh', 'tools/install-control-plane', 'tools/redact-support-bundle'}
JUNK = {'.git', '__pycache__', '.pytest_cache', 'support-bundles'}
REQUIRED = {'VERSION', 'bin/deckctl', 'lib/deckctl/cli.py', 'lib/deckctl/ui/Setup.qml',
            'config/default.json', 'config/aliases.json', 'tools/install-control-plane', 'install.sh'}


def selected(relative):
    path = Path(relative)
    return (not any(part in JUNK for part in path.parts)
            and path.suffix not in ('.pyc', '.pyo')
            and not path.is_relative_to('docs/ai')
            and (str(path) in FILES or path.parts[0] in TREES))


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if not selected(relative): continue
        if path.is_symlink(): raise ValueError(f'Runtime contains a symlink: {relative}')
        if path.is_dir(): continue
        if not stat.S_ISREG(path.stat().st_mode): raise ValueError(f'Unsupported runtime file: {relative}')
        result[str(relative)] = {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                 'mode':path.stat().st_mode & 0o777}
    return result


def write_manifest(root):
    files = inventory(root)
    missing = REQUIRED - files.keys()
    if missing: raise ValueError('Missing runtime files: '+', '.join(sorted(missing)))
    (root/MANIFEST).write_text(json.dumps({'format':1, 'version':(root/'VERSION').read_text().strip(),
                                        'files':files}, indent=2)+'\n')
    validate(root)


def validate(root):
    marker = root/MANIFEST
    if marker.is_symlink(): raise ValueError('Runtime manifest must not be a symlink')
    data = json.loads(marker.read_text())
    if not isinstance(data, dict) or type(data.get('format')) is not int or data.get('format') != 1 or data.get('version') != (root/'VERSION').read_text().strip():
        raise ValueError('Invalid runtime manifest format or version')
    actual = inventory(root)
    if REQUIRED - actual.keys() or data.get('files') != actual:
        raise ValueError('Runtime integrity mismatch: missing, modified or unexpected runtime files')
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if any(part in JUNK for part in rel.parts) or path.suffix in ('.pyc','.pyo'): continue
        if path.is_symlink(): raise ValueError(f'Unexpected runtime symlink: {rel}')
        if not path.is_dir() and str(rel) != MANIFEST and not selected(rel):
            raise ValueError(f'Unexpected non-runtime file: {rel}')
    for manifest in (root/'modules').glob('*/module.json'):
        module = json.loads(manifest.read_text())
        for action in module.get('actions', {}).values():
            target = manifest.parent/action
            if not target.resolve().is_relative_to(manifest.parent.resolve()) or not target.is_file() or not target.stat().st_mode & 0o111:
                raise ValueError(f'Invalid runtime module action: {target}')
    return len(actual)
