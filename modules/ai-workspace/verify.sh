#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH="$DECKCTL_ROOT/lib" python3 - <<'PYCODE'
import contextlib,io,json
from deckctl import ai_workspace
output=io.StringIO()
with contextlib.redirect_stdout(output):
    ai_workspace.status(True)
print(json.dumps(json.loads(output.getvalue())))
PYCODE
