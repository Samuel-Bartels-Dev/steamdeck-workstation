from __future__ import annotations
import json, re, shutil, socket, subprocess, time
from . import core

def _run(cmd,timeout=8):
    try:
        r=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
        return r.returncode,(r.stdout+r.stderr).strip()
    except Exception as e: return 1,str(e)

def _ping(host):
    rc,out=_run(['ping','-c','3','-W','2',host],10)
    vals=[float(x) for x in re.findall(r'time[=<]([0-9.]+)\s*ms',out)]
    return {'ok':rc==0,'samples_ms':vals,'avg_ms':round(sum(vals)/len(vals),1) if vals else None,'output':out[-600:]}

def _tailscale_samples(output):
    """Parse successful CLI replies; the last successful reply is the current route."""
    replies=[]
    for line in output.splitlines():
        if not line.lower().startswith('pong from '):
            continue
        match=re.search(r'\bin\s+([0-9.]+)\s*ms\b|\btime[= ]([0-9.]+)\s*ms\b',line,re.I)
        if not match:
            continue
        route='relay' if re.search(r'\b(?:DERP|relay)\b',line,re.I) else 'direct' if re.search(r'\bvia\s+\S+',line,re.I) else 'unknown'
        replies.append((float(match.group(1) or match.group(2)),route))
    return replies

def remote_test(host):
    target=host['target']
    print(f'Target: {target}')
    replies=[]
    if shutil.which('tailscale'):
        # --until-direct defaults to true and may hide an initial relay route.
        rc,out=_run(['tailscale','ping','--c','5','--until-direct=false',target],timeout=15)
        replies=_tailscale_samples(out)
        if replies:
            samples=[ms for ms,_ in replies]
            routes=[route for _,route in replies]
            path=routes[-1]
            print(f"Tailscale: {path.upper()} | replies {len(replies)}/5 (missed {5-len(replies)}) | avg {sum(samples)/len(samples):.1f} ms | spread {max(samples)-min(samples):.1f} ms")
            if 'relay' in routes and path=='direct': print('Route became direct during the test.')
        else:
            print(f'Tailscale: no measured replies ({out[-200:] or "command failed"})')
        if rc and replies: print('Tailscale command reported a warning; inspect the path before streaming.')
    else:
        print('Tailscale: CLI not found; route and latency unknown.')

    reachable=False
    try:
        with socket.create_connection((target,int(host.get('sunshine_port',47984))),timeout=2):
            reachable=True
        print('Sunshine TCP probe: PASS')
    except OSError as exc:
        print(f'Sunshine TCP probe: WARN ({exc})')

    if not reachable or not replies:
        print('Preset: unavailable until host connectivity and route can be measured.')
        return 1
    samples=[ms for ms,_ in replies]
    spread=max(samples)-min(samples)
    loss=5-len(samples)
    if replies[-1][1]!='direct' or loss or spread>30 or sum(samples)/len(samples)>100:
        preset='720p60 at 8 Mbps; try 720p30 if it still stutters'
    else:
        preset='720p60 at 10 Mbps; try 1080p60 at 15 Mbps if stable'
    print(f'Moonlight starting preset: {preset}')
    print('This is a latency/path estimate, not a bandwidth test. Lower bitrate if Moonlight shows frame drops; compare hotel Wi-Fi and a phone hotspot.')
    return 0

def test(host=None,as_json=False):
    data={}
    rc,route=_run(['ip','route','show','default']) if shutil.which('ip') else (1,'')
    m=re.search(r'default via ([^ ]+).* dev ([^ ]+)',route)
    data['route']={'raw':route,'gateway':m.group(1) if m else None,'interface':m.group(2) if m else None}
    if data['route']['gateway']: data['gateway_ping']=_ping(data['route']['gateway'])
    data['internet_dns']={'ok':False}
    try:
        socket.getaddrinfo('github.com',443); data['internet_dns']={'ok':True}
    except Exception as e: data['internet_dns']={'ok':False,'error':str(e)}
    if shutil.which('nmcli'):
        _,wifi=_run(['nmcli','-t','-f','ACTIVE,SSID,SIGNAL,RATE,FREQ,DEVICE','dev','wifi'])
        data['wifi']=next((x for x in wifi.splitlines() if x.startswith('yes:')),None)
    if shutil.which('tailscale'):
        rc,ts=_run(['tailscale','status'])
        data['tailscale']={'ok':rc==0,'summary':ts[:1200]}
    else: data['tailscale']={'ok':False,'summary':'CLI not found'}
    if host:
        h=core.host_registry().get(host)
        if not h: raise SystemExit(f'Unknown registered host: {host}')
        data['remote_target']=h['target']; data['remote_ping']=_ping(h['target'])
    if as_json: print(json.dumps(data,indent=2)); return data
    print('NETWORK DIAGNOSTICS')
    print(f"Route       {data['route'].get('gateway') or '-'} via {data['route'].get('interface') or '-'}")
    if data.get('wifi'): print(f"Wi-Fi       {data['wifi']}")
    gp=data.get('gateway_ping'); print(f"Gateway     {'PASS' if gp and gp['ok'] else 'WARN'} avg={gp.get('avg_ms') if gp else '-'} ms")
    print(f"DNS         {'PASS' if data['internet_dns']['ok'] else 'FAIL'}")
    print(f"Tailscale   {'PASS' if data['tailscale']['ok'] else 'WARN'}")
    if host:
        rp=data.get('remote_ping'); print(f"Remote      {'PASS' if rp and rp['ok'] else 'WARN'} avg={rp.get('avg_ms') if rp else '-'} ms")
    return data
