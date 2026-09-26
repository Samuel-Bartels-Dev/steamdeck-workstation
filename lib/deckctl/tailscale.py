"""Read-only Tailscale readiness without persisting peer or authentication data."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def binary():
    candidates = [shutil.which('tailscale'), '/opt/tailscale/tailscale']
    return next((str(p) for p in candidates if p and Path(p).is_file() and os.access(p, os.X_OK)), None)


def status():
    executable = binary()
    report = {'installed':bool(executable), 'connected':False, 'backend':'Unavailable', 'warnings':[]}
    if not executable:
        return {**report, 'message':'Tailscale is not installed.'}
    try:
        result = subprocess.run([executable,'status','--json'], capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=8)
        data = json.loads(result.stdout)
        if not isinstance(data, dict): raise ValueError('Invalid status response')
        backend = data.get('BackendState')
        report['backend'] = backend if backend in ('Running','Stopped','NeedsLogin','NeedsMachineAuth','NoState','Starting') else 'Unknown'
        report['connected'] = result.returncode == 0 and backend == 'Running'
        # Use fixed summaries; raw status may include peer names and login URLs.
        health = data.get('Health') or []
        if health:
            report['warnings'] = ['MagicDNS configuration needs attention; see Tailscale DNS guidance.'] if any('dns' in str(h).lower() or 'resolved' in str(h).lower() for h in health) else ['Tailscale reports a health warning; inspect tailscale status.']
        messages = {'Running':'Tailscale is connected; existing installation reused.',
                    'NeedsLogin':'Tailscale is installed; sign in to your tailnet.',
                    'NeedsMachineAuth':'Tailscale is installed; approve this device in your tailnet.',
                    'Stopped':'Tailscale is installed but stopped; resume the connection.',
                    'Starting':'Tailscale is starting; recheck shortly.'}
        report['message'] = messages.get(report['backend'], 'Tailscale is installed; service status is unavailable.')
        if result.returncode and backend == 'Running': report['message'] = 'Tailscale status command failed; recheck the service.'
    except (OSError, ValueError, subprocess.SubprocessError):
        report['message'] = 'Tailscale is installed, but its service status could not be read.'
    report['message'] += (' ' + ' '.join(report['warnings'])) if report['warnings'] else ''
    return report
