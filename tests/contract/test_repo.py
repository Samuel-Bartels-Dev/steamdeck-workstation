#!/usr/bin/env python3
import json, os, py_compile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; errors=[]; mods={}
for p in sorted((ROOT/'modules').glob('*/module.json')):
    try: d=json.loads(p.read_text())
    except Exception as e: errors.append(f"{p}: invalid JSON: {e}"); continue
    mid=d.get('id')
    if not mid: errors.append(f"{p}: missing id"); continue
    if mid in mods: errors.append(f"duplicate module id {mid}")
    mods[mid]=(p.parent,d)
    if not (p.parent/'README.md').exists(): errors.append(f"{mid}: README.md missing")
    if d.get('api_version')!=1: errors.append(f"{mid}: unsupported api_version")
    for required_action in ('install','verify','doctor'):
        if required_action not in d.get('actions',{}): errors.append(f'{mid}: missing action {required_action}')
    for action,rel in d.get('actions',{}).items():
        q=p.parent/rel
        if not q.resolve().is_relative_to(p.parent.resolve()): errors.append(f'{mid}: action escapes module: {rel}')
        if not q.is_file(): errors.append(f"{mid}: action {action} points to missing {rel}")
        elif not os.access(q,os.X_OK): errors.append(f"{mid}: action {action} not executable: {rel}")
for mid,(base,d) in mods.items():
    for dep in d.get('depends_on',[]):
        if dep not in mods: errors.append(f"{mid}: unknown dependency {dep}")
seen=set(); temp=set()
def visit(i):
    if i in seen: return
    if i in temp: errors.append(f"dependency cycle at {i}"); return
    temp.add(i)
    for dep in mods[i][1].get('depends_on',[]):
        if dep in mods: visit(dep)
    temp.remove(i); seen.add(i)
for i in mods: visit(i)
for required in ['AGENTS.md','CLAUDE.md','README.md','docs/PRINCIPLES.md','config/default.json','config/aliases.json']:
    if not (ROOT/required).exists(): errors.append(f"missing {required}")
try:
    for py in sorted((ROOT/'lib/deckctl').glob('*.py')):
        py_compile.compile(str(py),doraise=True)
except Exception as e: errors.append(f"python compile: {e}")
defaults=json.loads((ROOT/'config/default.json').read_text())
for mid in defaults.get('modules',{}):
    if mid not in mods: errors.append(f'Configured module does not exist: {mid}')
if errors:
    print('REPO VALIDATION FAILED'); [print('-',e) for e in errors]; sys.exit(1)
# User-visible behavior guardrails catch cross-release regressions that schema checks cannot.
r=__import__('subprocess').run([sys.executable,str(ROOT/'tests/contract/test_regressions.py')],cwd=ROOT)
if r.returncode:
    sys.exit(r.returncode)
r=__import__('subprocess').run([sys.executable,str(ROOT/'tests/contract/test_v0219.py')],cwd=ROOT)
if r.returncode:
    sys.exit(r.returncode)
for script in ['tests/contract/test_v0220.py','tests/contract/test_v0221.py','tests/contract/test_v0222.py','tests/contract/test_v0223.py','tests/contract/test_v0224.py','tests/contract/test_v0225.py','tests/contract/test_v0226.py','tests/contract/test_containers.py','tests/contract/test_desktop_apps.py','tests/contract/test_app_choices.py','tests/contract/test_ai_workspace.py','tests/contract/test_setup_window.py','tests/contract/test_component_options.py','tests/contract/test_claude_code.py','tools/check-docs.py']:
    r=__import__('subprocess').run([sys.executable,str(ROOT/script)],cwd=ROOT)
    if r.returncode: sys.exit(r.returncode)
print(f"REPO VALIDATION PASS — {len(mods)} modules")
