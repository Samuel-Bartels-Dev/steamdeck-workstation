#!/usr/bin/env python3
"""Render/check manuals from the exact parser metadata used at runtime."""
import argparse
import textwrap
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib'))
from deckctl.cli import build_parser
from deckctl.helptext import walk

def manual_help(parser):
    """Canonicalize only synopsis whitespace across Python argparse versions.

    Python 3.13 changed usage wrapping even at a fixed formatter width. Keep
    every usage token and all subsequent help text; do not weaken drift checks.
    """
    synopsis, separator, body = parser.format_help().strip().partition('\n\n')
    synopsis = textwrap.fill(' '.join(synopsis.split()), width=88,
                             subsequent_indent='       ',
                             break_long_words=False, break_on_hyphens=False)
    return synopsis + separator + body


def documents():
    version=(ROOT/'VERSION').read_text().strip()
    markdown=[f'# deckctl command manual — v{version}\n',
              'Generated from the runtime help registry. Use `deckctl help COMMAND` or `deckctl COMMAND --help`.\n',
              'For setup and maintenance entry points, see [Script reference](SCRIPTS.md).\n']
    man=[f'.TH DECKCTL 1 "" "{version}" "User Commands"', '.SH NAME', 'deckctl \\- Steam Deck workstation control plane']
    for path,parser in walk(build_parser()):
        name='deckctl'+(' '+' '.join(path) if path else '')
        text=manual_help(parser)
        markdown.extend([f'## {name}\n', '```text\n'+text+'\n```\n'])
        man.extend(['.SH "'+name.upper()+'"', '.nf'])
        for line in text.splitlines():
            line=line.replace('\\',r'\e').replace('-',r'\-')
            if line.startswith(('.',"'")): line=r'\&'+line
            man.append(line)
        man.append('.fi')
    return {ROOT/'docs/COMMANDS.md':'\n'.join(markdown)+'\n', ROOT/'docs/man/deckctl.1':'\n'.join(man)+'\n'}

def main():
    p=argparse.ArgumentParser(description=__doc__,epilog='Writes docs/COMMANDS.md and docs/man/deckctl.1; --check is read-only and exits 1 for drift.')
    p.add_argument('--check',action='store_true',help='Compare generated text to committed manuals without writing.')
    args=p.parse_args()
    for path,text in documents().items():
        if args.check:
            if not path.is_file() or path.read_text()!=text: raise SystemExit(f'Out-of-date manual: {path}')
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    return 0
if __name__=='__main__': raise SystemExit(main())
