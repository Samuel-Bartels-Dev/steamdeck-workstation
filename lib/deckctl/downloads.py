"""Atomic bounded HTTPS downloads for small staged artifacts, with honest integrity state."""
import hashlib
import os
from pathlib import Path
import tempfile
import time
import urllib.request
from . import install_progress, run_log


def fetch(url, destination, *, sha256=None, limit=32*1024*1024, validate=None):
    if not url.startswith('https://'): raise ValueError('Downloads require HTTPS')
    if destination.is_symlink(): raise ValueError('Refusing symlink download destination')
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.download-', dir=destination.parent)
    temporary = Path(name); started = time.monotonic(); size = 0; digest = hashlib.sha256()
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'deckctl'})
        with os.fdopen(fd, 'wb') as output, urllib.request.urlopen(request, timeout=30) as response:
            if not response.geturl().startswith('https://'): raise ValueError('Insecure download redirect')
            expected = response.headers.get('Content-Length')
            total = int(expected) if expected is not None else None
            if total is not None and (total <= 0 or total > limit): raise ValueError('Invalid download size')
            while True:
                chunk = response.read(65536)
                if not chunk: break
                size += len(chunk)
                if size > limit: raise ValueError('Download size limit exceeded')
                output.write(chunk); digest.update(chunk)
                install_progress.report('Downloading', 'Receiving staged installer', size, total)
            if not size or (total is not None and size != total): raise ValueError('Empty or incomplete download')
            output.flush(); os.fsync(output.fileno())
        if sha256 and digest.hexdigest() != sha256: raise ValueError('Download SHA-256 mismatch')
        if validate: validate(temporary)
        temporary.replace(destination)
        result = {'bytes':size, 'duration_ms':round((time.monotonic()-started)*1000),
                  'sha256':digest.hexdigest(), 'integrity':'UPSTREAM_SHA256' if sha256 else 'STRUCTURE_ONLY' if validate else 'UNVERIFIED',
                  'retries':0, 'cache_used':False}
        run_log.event('download', 'DONE', 'Artifact staged; '+result['integrity'], **result)
        return result
    finally: temporary.unlink(missing_ok=True)


def desktop_entry(path):
    text = path.read_text()
    if not text.startswith('[Desktop Entry]') or '\nExec=' not in text:
        raise ValueError('Invalid desktop installer (possibly an HTML/error response)')
