"""Read-only diagnosis and explicit, targeted repair dispatch."""
import contextlib
import io
import json
from . import core, containers, android, run_log


def diagnose(module=None, as_json=False):
    if module == 'docker':
        data = {'docker': containers.status_data()}
    elif module == 'waydroid':
        output = io.StringIO()
        with contextlib.redirect_stdout(output): android.status(True)
        data = {'waydroid': json.loads(output.getvalue())}
    else:
        if module and module not in core.module_manifests(): raise ValueError('Unknown module: '+module)
        targets = [module] if module else core.topo(core.enabled_modules())
        data = {mid: core.module_status(mid) for mid in targets}
    if as_json: print(json.dumps(data, indent=2))
    else:
        for name, row in data.items():
            print(name+': '+json.dumps(row, indent=2))
            print('Suggested next step: deckctl repair '+name)
        print('Diagnosis only; no repairs, service starts, downloads or container tests were run.')
    states = {row.get('status') for row in data.values()}
    if states & {'STOPPED_OR_UNREACHABLE', 'TEST_FAILED'}: return 1
    if states & {'NOT_CONFIGURED', 'API_READY', 'TEST_REQUIRED'}: return 2
    return core.status_exit(data)


def repair(module):
    # A target is mandatory. Never call every legacy doctor action speculatively.
    if module not in core.module_manifests() and module not in ('docker', 'waydroid', 'shortcuts'):
        raise ValueError('Unknown repair target: '+module)
    with run_log.execution('repair') as run:
        run.event(module, 'INFO', 'RUNNING', 'Explicit targeted repair requested')
        if module == 'docker': code = containers.provision()
        elif module == 'waydroid': code = android.repair()
        elif module == 'shortcuts':
            from . import shortcut_ops
            code = shortcut_ops.repair(False, False, None)
        else: code = core.doctor(module)
        run.finish(code)
        return code
