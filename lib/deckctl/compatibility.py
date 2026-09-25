"""Exact, evidence-scoped compatibility; never infer support from latest/version ranges."""
import json
import platform
from pathlib import Path
from . import core


def system():
    values = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value.strip('"\'')
    return {'os': values.get('ID', 'unknown'), 'version': values.get('VERSION_ID', 'unknown'),
            'build': values.get('BUILD_ID', 'unknown'), 'architecture': platform.machine(),
            'decky_version': 'unknown', 'kernel': platform.release(), 'model': core.detect_hardware().get('model', 'unknown')}


def database():
    data = core.load_json(core.ROOT/'compatibility/records.json')
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('records'), list):
        raise ValueError('Invalid compatibility database')
    identities = set()
    for row in data['records']:
        required = ('component', 'component_version', 'os', 'version', 'build', 'architecture', 'model', 'kernel', 'decky_version', 'date', 'evidence')
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k] for k in required):
            raise ValueError('Incomplete compatibility evidence')
        if row.get('status') not in ('TESTED', 'SUPPORTED', 'UNSUPPORTED'): raise ValueError('Invalid compatibility state')
        identity = tuple(row[k] for k in required[:7]) + (row['model'],)
        if identity in identities: raise ValueError('Duplicate compatibility record')
        identities.add(identity)
    return data['records']


def resolve(component, version, host, records):
    matches = [r for r in records if r['component'] == component and r['component_version'] == version
               and all(r[k] == host[k] for k in ('os', 'version', 'build', 'architecture', 'model'))]
    if matches:
        match = matches[0]
        if match['status'] == 'UNSUPPORTED': return dict(match)
        if (version != 'unknown' and match.get('kernel') == host.get('kernel')
                and (not component.startswith('plugin:') or
                     (host.get('decky_version', 'unknown') != 'unknown' and match.get('decky_version') == host.get('decky_version')))):
            return dict(match)
    return {'component': component, 'component_version': version, 'status': 'UNKNOWN',
            'reason': 'No exact, reviewed compatibility evidence for this system/component combination.'}


def report():
    host = system(); records = database()
    rows = [resolve('workstation', (core.ROOT/'VERSION').read_text().strip(), host, records)]
    # Package discovery is installation evidence only, never load/compatibility proof.
    for folder, plugin in core._decky_installed_plugins().items():
        try:
            package = core.load_json(Path(plugin['path'])/'package.json', {})
            version = str(package.get('version') or 'unknown')
        except (OSError, ValueError, KeyError): version = 'unknown'
        rows.append(resolve('plugin:'+folder, version, host, records))
    return {'schema_version': 1, 'system': host, 'components': rows,
            'policy': 'UNKNOWN warns; UNSUPPORTED blocks planned installation. No remote refresh is trusted automatically.'}


def command(as_json=False, verbose=False):
    data = report()
    if as_json: print(json.dumps(data, indent=2))
    else:
        print('Steam Deck Workstation Compatibility')
        print(json.dumps(data['system'], sort_keys=True))
        for row in data['components']:
            print(row['component'], row['status'], row.get('reason', row.get('evidence', '')))
        if verbose: print(data['policy'])
    return 1 if any(r['status'] == 'UNSUPPORTED' for r in data['components']) else 2 if any(r['status'] == 'UNKNOWN' for r in data['components']) else 0
