"""Content verification shared by restore and removable-storage migration."""
from __future__ import annotations
import hashlib
import os
import shutil
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def no_links(path):
    path=Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError(f'Symlink path requires review: {path}')

def inventory(root):
    root=Path(root);no_links(root)
    if not root.is_dir():raise ValueError(f'Directory missing: {root}')
    out={}
    for base,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(base)/name
            if p.is_symlink() or not (p.is_dir() or p.is_file()):raise ValueError(f'Unsupported file type: {p}')
            rel=str(p.relative_to(root))
            out[rel]={'kind':'directory'} if p.is_dir() else {'kind':'file','size':p.stat().st_size,'sha256':digest(p)}
    return out

def differences(expected,actual):
    return [name for name,value in expected.items() if actual.get(name)!=value]

def nearest(path):
    path=Path(path)
    while not path.exists():path=path.parent
    return path

def require_space(requests):
    groups={}
    for path,size in requests:
        existing=nearest(path);device=existing.stat().st_dev
        row=groups.setdefault(device,[existing,0]);row[1]+=size
    for path,size in groups.values():
        if shutil.disk_usage(path).free<size+16*1024*1024:
            raise ValueError(f'Insufficient free space on {path}; need {size} bytes plus 16 MiB reserve')

def atomic_merge(source,dest):
    """Never follow destination links; preserve unrelated files and stage each write."""
    import tempfile
    no_links(dest)
    if dest.exists():inventory(dest)
    dest.mkdir(parents=True,exist_ok=True)
    for base,dirs,files in os.walk(source):
        target=dest/Path(base).relative_to(source)
        target.mkdir(parents=True,exist_ok=True)
        for name in dirs:(target/name).mkdir(exist_ok=True)
        for name in files:
            out=target/name;no_links(out)
            fd,tmp=tempfile.mkstemp(prefix='.deckctl-restore-',dir=target)
            try:
                os.close(fd);shutil.copy2(Path(base)/name,tmp);os.replace(tmp,out)
            finally:
                Path(tmp).unlink(missing_ok=True)
