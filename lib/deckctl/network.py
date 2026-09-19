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
