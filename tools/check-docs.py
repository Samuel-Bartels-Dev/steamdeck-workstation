#!/usr/bin/env python3
"""Check local inline Markdown file links (not external URLs or heading anchors)."""
import argparse
import re
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    errors=[]
    for path in ROOT.rglob('*.md'):
        text=re.sub(r'```.*?```','',path.read_text(),flags=re.S)
        for target in re.findall(r'\]\(([^\s)]+)(?:\s+[^)]*)?\)',text):
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',target) or target.startswith('#'): continue
            file=unquote(target.split('#',1)[0])
            if file and not (path.parent/file).exists(): errors.append(f'{path.relative_to(ROOT)}: {file}')
    if errors: raise SystemExit('Missing local documentation links:\n'+'\n'.join(errors))
    print('Local documentation file references: PASS')
if __name__=='__main__': main()
