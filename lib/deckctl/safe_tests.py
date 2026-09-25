"""SAFE diagnostics only. Container launches and vendor repairs are never implicit."""
import contextlib
import io
import json
import time
from . import core, lifecycle, preflight, run_log


def run(mode='quick', module=None, as_json=False):
    with run_log.execution('test') as journal:
        started = time.monotonic()
        if mode == 'module':
            if module not in core.module_manifests(): raise ValueError('Unknown module')
            modules = {module: core.module_status(module)}
            checks = None
        else:
            # Existing health collectors stay silent for a single valid JSON result.
            with contextlib.redirect_stdout(io.StringIO()): health = lifecycle.health(True)
            modules = health['modules']
            checks = preflight.report(online=mode == 'full')
        code = core.status_exit(modules)
        if checks and checks['status'] == 'FAIL': code = 1
        elif checks and checks['status'] == 'WARN' and code == 0: code = 2
        data = {'schema_version': 1, 'run_id': journal.id, 'safety': 'SAFE', 'mode': mode,
                'modules': modules, 'preflight': checks, 'exit_code': code,
                'duration_ms': round((time.monotonic()-started)*1000),
                'not_tested': ['container launch', 'Android boot', 'Game Mode plugin load', 'reboot', 'fresh install', 'upgrade']}
        core.save_json(journal.path/'plan.json', data)
        journal.finish(code)
        if as_json: print(json.dumps(data, indent=2))
        else:
            core.print_table([(k,v.get('status','UNKNOWN'),v.get('message','')) for k,v in modules.items()])
            print('SAFE checks finished. Exit:', code, 'Run:', journal.id)
        return code
