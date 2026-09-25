"""Small CLI adapter for production diagnostics and run history."""
from . import compatibility, preflight, run_log, diagnostics, core


def add_parser(sp):
    for name in ('preflight', 'compatibility'):
        parser = sp.add_parser(name)
        parser.add_argument('--json', action='store_true')
        if name == 'preflight': parser.add_argument('--online', action='store_true', help='Probe required HTTPS endpoints with bounded timeouts.')
        else: parser.add_argument('--verbose', action='store_true', help='Explain compatibility evidence policy.')
    test = sp.add_parser('test')
    test.add_argument('mode', choices=('quick', 'full', 'module'), help='SAFE diagnostics; full adds network probes, not live container/Android tests.')
    test.add_argument('module', nargs='?', help='Required module identifier for test module.')
    test.add_argument('--json', action='store_true')
    cleanup = sp.add_parser('cleanup')
    cleanup.add_argument('--dry-run', action='store_true', help='Preview only known hash-matched, verified installer artifacts.')
    repair = sp.add_parser('repair')
    repair.add_argument('module', help='Explicit module, docker, waydroid or shortcuts target.')
    logs = sp.add_parser('logs')
    sub = logs.add_subparsers(dest='logs_action', required=True)
    for name in ('latest', 'list', 'errors'): sub.add_parser(name)
    show = sub.add_parser('show'); show.add_argument('module', help='Exact item/module ID from the latest run.')
    clean = sub.add_parser('clean'); clean.add_argument('--all', action='store_true', help='Remove inactive history except the newest failure; preserve unrecognized files.')


def dispatch(args):
    if args.cmd == 'test':
        from . import safe_tests
        if (args.mode == 'module') != (args.module is not None): raise ValueError('Use test module MODULE, or test quick/full without a module')
        return safe_tests.run(args.mode, args.module, args.json)
    if args.cmd == 'cleanup':
        from . import setup_cleanup
        return setup_cleanup.cleanup(args.dry_run)
    if args.cmd == 'preflight': return preflight.command(args.json, args.online)
    if args.cmd == 'compatibility': return compatibility.command(args.json, args.verbose)
    if args.cmd == 'repair': return diagnostics.repair(args.module)
    if args.cmd == 'logs': return run_log.command(args.logs_action, getattr(args, 'module', None), getattr(args, 'all', False))
    return None


HELP = {
    'test': ('Run SAFE diagnostics with a durable timing/result record.', 'quick checks health and offline preflight; full adds bounded HTTPS probes; module runs one verifier. No container launches, Android boot, installs or repairs. Exit 0 pass, 1 failed, 2 warning/configuration required.', 'test quick --json'),
    'cleanup': ('Clean only verified, unchanged staged project installers.', 'Uses the existing fingerprinted cleanup policy. Never sweeps arbitrary temporary files, model caches or user downloads. --dry-run previews changes.', 'cleanup --dry-run'),
    'preflight': ('Check selected installation prerequisites without changing installed components.',
                  'Reports architecture, commands, writable destinations, estimated space and compatibility. --online adds bounded HTTPS probes. Exit 0 pass, 1 blocked, 2 warnings. Unknown sizes are not capacity guarantees.', 'preflight --json'),
    'compatibility': ('Report exact, reviewed compatibility evidence.',
                      'Read-only local records. Unknown combinations remain UNKNOWN. Exit 0 known supported/tested, 1 unsupported, 2 unknown. Does not certify plugin loading.', 'compatibility --json'),
    'repair': ('Explicitly repair one selected module or supported target.',
               'May install, update configuration or launch vendor setup. Preserves existing module repair behavior. No implicit repair-all. Docker uses the existing rootless provider; waydroid uses protected Android repair.', 'repair docker'),
    'logs latest': ('Print the latest run directory.', 'Read-only. Logs are private and should be reviewed before sharing.', 'logs latest'),
    'logs list': ('List recorded runs and results.', 'Read-only. RUNNING without an active installer can indicate interruption.', 'logs list'),
    'logs errors': ('Show error events from the latest run.', 'Read-only structured events; detailed item stderr is in the run directory.', 'logs errors'),
    'logs show': ('Show a module or item event stream from the latest run.', 'Use the exact identifier, for example terminal:ghostty. Read-only.', 'logs show terminal:ghostty'),
    'logs clean': ('Remove expired inactive run history safely.', 'Keeps 10 install/apply/test and 5 repair/update runs; failures 30 days and newest failure indefinitely. --all still preserves active runs, newest failure and unrecognized content.', 'logs clean'),
}


def operation(name, callback, check=False):
    with run_log.execution(name) as journal:
        if check:
            data = preflight.report(online=True)
            core.save_json(journal.path/'plan.json', {'preflight': data})
            for row in data['checks']:
                journal.event('preflight', 'ERROR' if row['status'] == 'FAIL' else 'INFO', row['status'], row['name']+': '+row['message'])
                print(row['status']+' '+row['name']+': '+row['message'])
            if data['status'] == 'FAIL':
                journal.finish(1)
                print('Installation blocked. Full log: '+str(journal.path))
                return 1
        code = callback()
        journal.finish(code)
        print('Run log: '+str(journal.path))
        return code
