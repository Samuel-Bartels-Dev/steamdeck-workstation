#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"

# Existing working install wins. Avoid replacing a healthy user install on every reconcile.
if command -v codex >/dev/null 2>&1 && codex --version >/dev/null 2>&1; then
  echo "[skip] Codex CLI already installed: $(codex --version 2>/dev/null | head -n1)"
  exit 0
fi

have_curl=false
command -v curl >/dev/null 2>&1 && have_curl=true
if [[ "$have_curl" != true ]]; then
  echo "curl is required to install Codex CLI." >&2
  exit 1
fi

echo "Installing Codex CLI using OpenAI's standalone Linux installer..."
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

installed=false
if curl -fsSL --retry 2 https://chatgpt.com/codex/install.sh -o "$tmp/codex-install.sh"; then
  if sh "$tmp/codex-install.sh"; then
    installed=true
  fi
fi

# Normalize discovery. OpenAI's standalone installer may manage its own package path;
# keep ~/.local/bin on PATH but do not replace a healthy command.
export PATH="$HOME/.local/bin:$HOME/.codex/bin:$PATH"
if command -v codex >/dev/null 2>&1 && codex --version >/dev/null 2>&1; then
  echo "Codex installed: $(codex --version 2>/dev/null | head -n1)"
  exit 0
fi

# Fallback: fetch the latest official x86_64 Linux release directly from openai/codex.
echo "Standalone installer did not leave a runnable codex command; trying official GitHub release fallback..."
python3 - "$tmp" <<'PY'
import json, os, sys, urllib.request
out=sys.argv[1]
api='https://api.github.com/repos/openai/codex/releases/latest'
req=urllib.request.Request(api,headers={'User-Agent':'steamdeck-workstation'})
with urllib.request.urlopen(req,timeout=30) as r:
    data=json.load(r)
wanted='codex-x86_64-unknown-linux-musl.tar.gz'
asset=next((a for a in data.get('assets',[]) if a.get('name')==wanted),None)
if not asset:
    raise SystemExit(f'Official release asset not found: {wanted}')
url=asset['browser_download_url']
path=os.path.join(out,wanted)
req=urllib.request.Request(url,headers={'User-Agent':'steamdeck-workstation'})
with urllib.request.urlopen(req,timeout=60) as r, open(path,'wb') as f:
    while True:
        chunk=r.read(1024*1024)
        if not chunk: break
        f.write(chunk)
print(path)
PY
archive="$tmp/codex-x86_64-unknown-linux-musl.tar.gz"
tar -xzf "$archive" -C "$tmp"
binary="$(find "$tmp" -maxdepth 2 -type f -name 'codex-x86_64-unknown-linux-musl' -print -quit)"
if [[ -z "$binary" ]]; then
  echo "Could not locate Codex binary after extracting official release." >&2
  exit 1
fi
install -m 0755 "$binary" "$HOME/.local/bin/codex"

if ! "$HOME/.local/bin/codex" --version >/dev/null 2>&1; then
  echo "Codex binary was installed but did not execute successfully." >&2
  exit 1
fi

echo "Codex installed: $($HOME/.local/bin/codex --version | head -n1)"
