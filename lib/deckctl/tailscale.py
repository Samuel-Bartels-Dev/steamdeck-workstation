"""Read-only Tailscale readiness without persisting peer or authentication data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import re


def connect_ui():
    """Keep authentication output private; hand only the login URL to the browser."""
    from . import privilege
    if status()['connected']: return None
    executable = binary()
    if not executable: raise RuntimeError('Tailscale installation did not produce its CLI. Retry this item.')
    try:
        result = subprocess.run(privilege.command([executable, 'up', '--timeout=10s', '--operator=deck', '--ssh']),
                                env=privilege.environment(), stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return 'Tailscale connection timed out. Retry this item in the setup window.'
    report = status()
    if report['connected']: return None
    if report['backend'] == 'NeedsMachineAuth':
        return 'Approve this Steam Deck in your Tailscale admin console, then choose Retry here.'
    # Never print or persist the authentication output, peer details, or login URL.
    match = re.search(r'https://login\.tailscale\.com/a/[A-Za-z0-9_-]+', result.stdout+'\n'+result.stderr)
    if match:
        try:
            opened = subprocess.run(['xdg-open', match.group(0)], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return 'Could not open Tailscale sign-in in your browser. Check the default browser, then Retry here.'
        if opened.returncode: return 'Could not open Tailscale sign-in in your browser. Check the default browser, then Retry here.'
        return 'Tailscale sign-in opened in your browser. Finish signing in, then choose Retry or Resume here; no terminal is needed.'
    return 'Tailscale is not connected yet. Check that its service is running, then choose Retry here.'


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
