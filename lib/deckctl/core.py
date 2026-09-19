from __future__ import annotations
import tempfile
import json, os, re, shlex, shutil, socket, subprocess, sys, tarfile, time, zipfile
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
STATE = Path(os.environ.get("DECKCTL_STATE", Path.home()/".local/state/deckctl"))
CONFIG_HOME = Path(os.environ.get("DECKCTL_CONFIG", Path.home()/".config/deckctl"))

def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default

def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    # A unique, private sibling prevents concurrent writes sharing a temp file.
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps(data, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def module_manifests():
    out = {}
    for p in sorted((ROOT/"modules").glob("*/module.json")):
        d = load_json(p, {})
        if d.get("id"):
            out[d["id"]] = (p.parent, d)
    return out

def enabled_modules():
    cfg = load_json(ROOT/"config/default.json", {})
    return [k for k, v in cfg.get("modules", {}).items() if v]

def topo(ids: List[str]):
    mods = module_manifests(); seen=set(); temp=set(); order=[]
    def visit(i):
        if i in seen: return
        if i in temp: raise RuntimeError(f"dependency cycle at {i}")
        if i not in mods: raise RuntimeError(f"unknown module dependency: {i}")
        temp.add(i)
        for d in mods[i][1].get("depends_on", []): visit(d)
        temp.remove(i); seen.add(i); order.append(i)
    for i in ids: visit(i)
    return order

def run_action(mid, action, capture=False):
    base, manifest = module_manifests()[mid]
    rel = manifest.get("actions", {}).get(action)
    if not rel: return None
    p = base/rel
    env = os.environ.copy()
    env.update({"PYTHONDONTWRITEBYTECODE":"1", "DECKCTL_ROOT":str(ROOT), "DECKCTL_STATE":str(STATE), "DECKCTL_CONFIG":str(CONFIG_HOME)})
    return subprocess.run([str(p)], cwd=base, env=env, text=True, capture_output=capture, timeout=60 if action == "verify" else None)

def module_status(mid):
    try:
        r = run_action(mid, "verify", capture=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status":"FAILED", "message":str(exc)}
    if r is None: return {"status":"FAILED", "message":"No verifier defined"}
    for line in reversed((r.stdout or "").strip().splitlines()):
        try:
            d=json.loads(line)
            if isinstance(d, dict) and d.get("status") in {"READY", "DEGRADED", "CONFIG_REQUIRED", "NOT_INSTALLED", "FAILED", "OPTIONAL"}:
                if r.returncode and d["status"] == "READY":
                    return {"status":"FAILED", "message":"Verifier exited nonzero while reporting READY"}
                return d
        except Exception:
            pass
    return {"status":"FAILED", "message":(r.stderr or r.stdout or "Verifier returned no status").strip()[-400:]}

def detect_hardware():
    vals=[]
    for n in ["product_name","board_name","product_version","bios_version"]:
        p=Path("/sys/devices/virtual/dmi/id")/n
        try: vals.append(p.read_text(errors="ignore").strip())
        except Exception: pass
    blob=" ".join(vals).lower()
    if "galileo" in blob or "steam deck oled" in blob: model="oled"
    elif "jupiter" in blob or "steam deck" in blob: model="lcd"
    else: model="unknown"
    osrel=Path('/etc/os-release')
    battery={}
    for bp in [Path('/sys/class/power_supply/BAT1'),Path('/sys/class/power_supply/BAT0')]:
        if not bp.exists(): continue
        def readnum(name):
            try: return float((bp/name).read_text().strip())
            except Exception: return None
        full=readnum('energy_full') or readnum('charge_full')
        design=readnum('energy_full_design') or readnum('charge_full_design')
        cap=readnum('capacity')
        battery={"path":str(bp),"charge_percent":cap,"health_percent":round(full/design*100,1) if full and design else None}
        break
    return {"model":model,"raw":vals,"is_steamos":osrel.exists() and 'steamos' in osrel.read_text(errors='ignore').lower(),"battery":battery}

def print_table(rows):
    if not rows: return
    width=max(len(r[0]) for r in rows)
    for a,b,c in rows: print(f"{a:<{width}}  {b:<17} {c}")

def plan():
    rows=[]
    for m in topo(enabled_modules()):
        st=module_status(m)
        rows.append((m, st.get("status","?"), st.get("message","")))
    print_table(rows)

def apply():
    failures = []
    progress=load_json(STATE/'provisioning.json',{}) or {}
    records=progress.setdefault('modules',{})
    version=(ROOT/'VERSION').read_text().strip()
    for mid in topo(enabled_modules()):
        print(f"\n==> {mid}")
        previous=records.get(mid,{})
        if previous.get('version')==version and previous.get('status') in ('READY','OPTIONAL'):
            check=module_status(mid)
            if check.get('status') in ('READY','OPTIONAL'):
                print(f'{mid}: verified current release; skipped')
                continue
        records[mid]={'status':'RUNNING','version':version}
        save_json(STATE/'provisioning.json',progress)
        try:
            r=run_action(mid,"install",capture=False)
            check=module_status(mid)
        except Exception as exc:
            records[mid]={'status':'FAILED','version':version,'message':str(exc)}
            save_json(STATE/'provisioning.json',progress)
            failures.append(mid)
            print(f'{mid}: failed: {exc}')
            continue
        records[mid]={'status':'FAILED' if r is not None and r.returncode else check.get('status','FAILED'),
                      'message':check.get('message',''),'version':version}
        save_json(STATE/'provisioning.json',progress)
        if (r is not None and r.returncode != 0) or check.get("status") in ("FAILED","NOT_INSTALLED"):
            failures.append(mid)
            print(f"[warn] {mid} provisioning failed; continuing for guided setup", file=sys.stderr)
    create_setup_shortcut()
    from . import setup_cleanup
    setup_cleanup.cleanup()
    print("\nProvisioning pass complete. Run: ./bin/deckctl verify")
    return 1 if failures else 0

def status_exit(data):
    states = {item.get("status") for item in data.values()}
    if states & {"FAILED", "NOT_INSTALLED"}: return 1
    if states & {"DEGRADED", "CONFIG_REQUIRED"}: return 2
    return 0

def verify(as_json=False):
    data={m:module_status(m) for m in topo(enabled_modules())}
    if as_json:
        print(json.dumps({"hardware":detect_hardware(),"modules":data},indent=2))
    else:
        print_table([(m,d.get("status","?"),d.get("message","")) for m,d in data.items()])
    return data

def doctor(mid=None):
    if mid is not None and mid not in module_manifests():
        raise SystemExit(f"Unknown module: {mid}")
    targets=[mid] if mid else topo(enabled_modules())
    for m in targets:
        s=module_status(m)
        if s["status"]=="READY":
            print(f"{m}: READY (no repair needed)"); continue
        r=run_action(m,"doctor",capture=False)
        if r is None: print(f"{m}: no automated doctor; see modules/{m}/README.md")
    return status_exit({m:module_status(m) for m in targets})

def storage_devices():
    cmd=["lsblk","-J","-o","NAME,PATH,TYPE,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS,RM,MODEL,FSAVAIL,FSUSE%"]
    try: return json.loads(subprocess.check_output(cmd,text=True)).get("blockdevices",[])
    except Exception: return []

def walk_blocks(nodes):
    for n in nodes:
        yield n
        yield from walk_blocks(n.get("children",[]) or [])

def storage_health(as_json=False, quiet=False):
    cfg=load_json(ROOT/"config/default.json",{}).get("storage",{})
    roles={cfg.get("games_label","DECK-GAMES"):"pc_games",cfg.get("emu_label","DECK-EMU"):"emulation"}
    rows=[]
    for n in walk_blocks(storage_devices()):
        if n.get("type") not in ("disk","part"): continue
        label=n.get("label") or ""
        role=roles.get(label,"internal/other" if not n.get("rm") else "unknown-removable")
        mounts=','.join(x for x in (n.get("mountpoints") or []) if x)
        rows.append({"name":n.get("name"),"size":n.get("size"),"label":label,"uuid":n.get("uuid") or "","mount":mounts,"role":role,"free":n.get("fsavail") or "","use_percent":n.get("fsuse%") or ""})
    if not quiet:
        if as_json: print(json.dumps(rows,indent=2))
        else:
            for r in rows: print(f"{r['name']:<10} {str(r['size']):<8} {r['role']:<18} free={r['free'] or '-':<8} use={r['use_percent'] or '-':<5} label={r['label'] or '-'} mount={r['mount'] or '-'}")
    return rows

def storage_recommend(game, system=None):
    g=game.strip().lower(); hints=load_json(ROOT/"config/game-hints.json",{})
    if system:
        pref="emu"; reasons=[f"explicit emulation system: {system}","ROM/disc payload belongs with the emulation library"]
    elif g in hints:
        pref=hints[g]["preferred"]; reasons=hints[g]["reasons"]
    elif any(x in g for x in ["world of warcraft","wow","diablo","call of duty","mmorpg"]):
        pref="internal"; reasons=["stateful/frequently updated workload","internal NVMe minimizes random-I/O and patching friction"]
    else:
        pref="games"; reasons=["default for large replaceable PC game payloads","keeps internal NVMe available for stateful/performance-sensitive content"]
    name={"internal":"INTERNAL NVMe","games":"DECK-GAMES","emu":"DECK-EMU"}[pref]
    print(f"Recommended: {name}\n")
    for r in reasons: print(f"- {r}")
    print("\nAdvisory only: benchmark or override per-title when a game behaves differently.")

def game_registry(): return load_json(CONFIG_HOME/"games.json",{}) or {}

def game_register(name, launcher, path, storage_role):
    d=game_registry(); d[name.lower()]={"name":name,"launcher":launcher,"path":path,"storage_role":storage_role}; save_json(CONFIG_HOME/"games.json",d); print(f"Registered {name}")

def game_ready(name, doctor_mode=False):
    d=game_registry().get(name.lower())
    if not d:
        print("UNREGISTERED\nUse: deckctl game register NAME --launcher ... --path ... --storage-role ...")
        return 2
    checks=[]; p=Path(os.path.expanduser(d["path"])); checks.append(("payload",p.exists(),str(p)))
    if d.get("storage_role") in ("pc_games","emulation"):
        scfg=load_json(ROOT/"config/default.json",{}).get("storage",{})
        label=scfg.get("games_label") if d["storage_role"]=="pc_games" else scfg.get("emu_label")
        checks.append(("storage",any(x.get("label")==label for x in storage_health(quiet=True)),label))
    print(f"{d['name']} — {d['launcher']}")
    for k,ok,detail in checks: print(f"{k:<14} {'PASS' if ok else 'FAIL':<5} {detail}")
    if doctor_mode and all(ok for _,ok,_ in checks): print("No file/storage fault found. Check launcher authentication, compatibility layer, and game-specific logs next.")
    return 0 if all(ok for _,ok,_ in checks) else 1

def host_registry(): return load_json(CONFIG_HOME/"hosts.json",{}) or {}

def remote_register(name,target,mac=None,relay=None,sunshine_port=47984):
    if not 1 <= sunshine_port <= 65535: raise SystemExit('Sunshine port must be 1..65535')
    for label, value in [('target', target), ('relay', relay)]:
        if value and (value.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_.:@%\[\]-]+', value)):
            raise SystemExit(f'Invalid {label}: use a hostname/IP or user@hostname')
    if mac: wol_packet(mac)
    d=host_registry(); d[name]={"target":target,"mac":mac,"relay_ssh":relay,"sunshine_port":sunshine_port}; save_json(CONFIG_HOME/"hosts.json",d); print(f"Registered host {name}")

def get_host(name):
    h=host_registry().get(name)
    if not h: raise SystemExit(f"Unknown host {name}. Use deckctl remote register ...")
    return h

def remote_test(name):
    h=get_host(name); target=h["target"]
    print(f"Target: {target}")
    if shutil.which("tailscale"):
        r=subprocess.run(["tailscale","ping","--c","3",target],text=True,capture_output=True)
        out=(r.stdout+r.stderr).strip(); print(out)
        times=[float(x) for x in re.findall(r'time[= ]([0-9.]+)\s*ms',out,re.I)]
        if times:
            avg=sum(times)/len(times); jitter=max(times)-min(times)
            print(f"Tailscale samples: {len(times)}/3  avg={avg:.1f} ms  spread={jitter:.1f} ms")
        if "DERP" in out.upper(): print("WARNING: relay/DERP path detected; remote-game latency may be higher.")
    else: print("Tailscale CLI not found; skipping tailnet path test.")
    try:
        with socket.create_connection((target,int(h.get("sunshine_port",47984))),timeout=2): print("Sunshine TCP probe: PASS")
    except Exception as e: print(f"Sunshine TCP probe: WARN ({e})")

def wol_packet(mac):
    raw=re.sub(r'[^0-9A-Fa-f]','',mac)
    if len(raw)!=12: raise ValueError("invalid MAC")
    return bytes.fromhex('FF'*6 + raw*16)

def remote_wake(name):
    h=get_host(name); mac=h.get("mac")
    if not mac: raise SystemExit("No MAC registered for host")
    pkt=wol_packet(mac); relay=h.get("relay_ssh")
    if relay and (relay.startswith("-") or not re.fullmatch(r"[A-Za-z0-9_.:@%\[\]-]+", relay)):
        raise SystemExit("Invalid SSH relay")
    if relay:
        py="import socket; p=bytes.fromhex(%r); s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1); s.sendto(p,('255.255.255.255',9))" % pkt.hex()
        subprocess.run(["ssh", "--", relay, "python3 -c " + shlex.quote(py)],check=True); print("Wake packet requested through SSH relay")
    else:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1); s.sendto(pkt,("255.255.255.255",9)); print("Wake packet sent on local LAN")

def remote_wait(name,timeout=90):
    if timeout <= 0: raise SystemExit("Timeout must be positive")
    h=get_host(name); target=h['target']; end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            with socket.create_connection((target,int(h.get('sunshine_port',47984))),timeout=2): print("Host/Sunshine reachable"); return 0
        except Exception: time.sleep(3)
    print("Timed out waiting for host"); return 1

def backup_saves():
    cfg=load_json(ROOT/"config/default.json",{}); dest=Path(os.path.expanduser(cfg.get("backup",{}).get("destination","~/DeckBackups"))); dest.mkdir(parents=True,exist_ok=True)
    candidates=[Path.home()/"Emulation/saves",Path.home()/"Emulation/storage",Path.home()/"Games/World of Warcraft/_retail_/WTF",Path.home()/"Games/World of Warcraft/_retail_/Interface/AddOns"]
    # Include SD-card Emulation save/storage locations if mounted.
    for emu in Path('/run/media').glob('*/Emulation') if Path('/run/media').exists() else []:
        candidates.extend([emu/'saves',emu/'storage'])
    existing=[]
    for p in candidates:
        if p.exists() and p not in existing: existing.append(p)
    stamp=time.strftime('%Y%m%d-%H%M%S'); out=dest/f"deck-state-{stamp}.tar.gz"
    with tarfile.open(out,"w:gz") as tf:
        tf.dereference=True
        for p in existing:
            logical=p
            source=p.resolve() if p.is_symlink() else p
            try: arc=str(logical.relative_to(Path.home()))
            except ValueError: arc='external/'+logical.name
            tf.add(source,arcname=arc)
    print(f"Created {out} with {len(existing)} source paths")

def inventory(as_json=False):
    data={"version":(ROOT/"VERSION").read_text().strip(),"hardware":detect_hardware(),"modules":{m:module_status(m) for m in topo(enabled_modules())},"storage":storage_health(quiet=True)}
    print(json.dumps(data,indent=2)); return data

def travel_lock(lock=True):
    p=STATE/"travel-lock.json"
    if lock:
        save_json(p,{"locked_at":time.strftime('%Y-%m-%dT%H:%M:%S%z'),"version":(ROOT/"VERSION").read_text().strip(),"hardware":detect_hardware()}); print(f"Travel lock recorded at {p}")
    else:
        if p.exists(): p.unlink()
        print("Travel lock removed")

def travel_check():
    data=verify(False); bad=[m for m,s in data.items() if s.get('status') in ('FAILED','NOT_INSTALLED')]
    print("\nTravel checks:")
    print(f"backup destination: {os.path.expanduser(load_json(ROOT/'config/default.json',{}).get('backup',{}).get('destination','~/DeckBackups'))}")
    print("remote: run `deckctl remote test <host>` from the actual away-network path before travel")
    print("PS5: test chiaki-ng using a phone hotspot/non-home network")
    print("RESULT:","READY WITH INTERACTIVE CHECKS" if not bad else "NOT READY")
    return 0 if not bad else 1

def support_bundle():
    outdir=ROOT/"support-bundles"; outdir.mkdir(exist_ok=True); stamp=time.strftime('%Y%m%d-%H%M%S'); work=STATE/f"support-{stamp}"; work.mkdir(parents=True,exist_ok=True)
    save_json(work/"inventory.json",{"version":(ROOT/'VERSION').read_text().strip(),"hardware":detect_hardware(),"modules":{m:module_status(m) for m in topo(enabled_modules())},"storage":storage_devices()})
    (work/"README.txt").write_text("Redacted deckctl support bundle. Review before sharing. No credential stores, ROMs, BIOS binaries, or private keys are intentionally collected.\n")
    out=outdir/f"deck-support-{stamp}.zip"
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in work.rglob('*'):
            if p.is_file(): z.write(p,p.relative_to(work))
    shutil.rmtree(work); print(out)

def ai_context(mid):
    if mid not in module_manifests(): raise SystemExit(f"Unknown module: {mid}")
    _,m=module_manifests()[mid]
    print("Read:\n- AGENTS.md")
    print(f"- modules/{mid}/{m.get('documentation',{}).get('primary','README.md')}")
    print("\nCurrent status:"); print(json.dumps(module_status(mid),indent=2))

def ai_task(mid,desc):
    if mid not in module_manifests(): raise SystemExit(f"Unknown module: {mid}")
    stamp=time.strftime('%Y%m%d-%H%M%S'); slug=re.sub(r'[^a-z0-9]+','-',desc.lower()).strip('-')[:48]; p=ROOT/'tasks/active'/f"DECK-{stamp}-{slug}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# {desc}\n\n## Goal\n{desc}\n\n## Scope\n`modules/{mid}/` and only directly required shared code.\n\n## Read\n- `AGENTS.md`\n- `modules/{mid}/README.md`\n- `modules/{mid}/module.json`\n\n## Requirements\n- Preserve module contract and idempotency.\n- Add/update verification and tests.\n\n## Out of scope\nUnrelated modules and broad refactors.\n\n## Acceptance criteria\n- Behavior is implemented and observable.\n- `./bin/deckctl repo validate` passes.\n\n## Validation\n- `./bin/deckctl verify`\n- relevant module tests\n\n## Rollback / recovery notes\nDocument any stateful changes.\n")
    print(p)



def setup_state():
    return load_json(STATE/"setup.json", {"completed": [], "skipped": []}) or {"completed": [], "skipped": []}

def save_setup_state(data):
    save_json(STATE/"setup.json", data)

def _flatpak_installed(app):
    try:
        return subprocess.run(["flatpak","info",app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except FileNotFoundError:
        return False

def _launch_path(path: Path):
    path=Path(path)
    if not path.exists():
        print(f"Cannot launch missing file: {path}")
        return False
    # gio launch is designed to execute DesktopAppInfo files. KDE fallback follows.
    if shutil.which("gio"):
        subprocess.Popen(["gio","launch",str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    if shutil.which("kioclient"):
        subprocess.Popen(["kioclient","exec",path.as_uri()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open",str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False

def _open_url(url):
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open",url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False

def _launch_flatpak(app):
    if not _flatpak_installed(app):
        print(f"Flatpak not installed: {app}")
        return False
    subprocess.Popen(["flatpak","run",app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True

def _deckctl_executable():
    """Return a deckctl path that works even in a fresh login shell.

    Guided setup is commonly launched with `bash -lc`, which does not reliably
    source ~/.bashrc on SteamOS. Never assume ~/.local/bin is already on PATH.
    """
    persistent = Path.home()/".local/bin/deckctl"
    if persistent.exists() or persistent.is_symlink():
        return persistent
    return ROOT/"bin/deckctl"


def _launch_terminal_command(command):
    import shlex
    if shutil.which("konsole"):
        # A login shell may not read ~/.bashrc, so guarantee the user-local bin
        # path for Codex/deckctl and other provisioned commands.
        wrapped = f'export PATH="$HOME/.local/bin:$PATH"; {command}; exec bash'
        subprocess.Popen(["konsole","-e","bash","-lc",wrapped], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False


def _guided_controller_templates_install():
    """Install controller templates synchronously during guided setup.

    This is a reconciliation action, not an interactive installer. Running it
    inline avoids opening a second Konsole window and lets setup verify the
    result immediately.
    """
    cmd=[str(_deckctl_executable()), "controller", "install-templates"]
    result=subprocess.run(cmd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    return result.returncode == 0


def _steam_shortcut_has(name: str):
    root=Path.home()/".local/share/Steam/userdata"
    if not root.exists(): return False
    needle=name.encode("utf-8")
    for vdf in root.glob("*/config/shortcuts.vdf"):
        try:
            if needle in vdf.read_bytes(): return True
        except Exception:
            pass
    return False

def _media_desktop_provisioned():
    appdir=Path.home()/".local/share/applications"
    bindir=Path.home()/".local/share/deckctl/media/bin"
    services=("netflix","hulu","crunchyroll","prime-video")
    return all((appdir/f"deck-media-{sid}.desktop").exists() and (bindir/sid).exists() for sid in services)

def _media_configured():
    appdir=Path.home()/".local/share/applications"
    services={"netflix":"Netflix","hulu":"Hulu","crunchyroll":"Crunchyroll","prime-video":"Prime Video"}
    return _media_desktop_provisioned() and all(_steam_shortcut_has(name) for name in services.values())

def media_status():
    appdir=Path.home()/".local/share/applications"
    services={"netflix":"Netflix","hulu":"Hulu","crunchyroll":"Crunchyroll","prime-video":"Prime Video"}
    chrome=_flatpak_installed("com.google.Chrome")
    print("MEDIA APPS")
    print(f"Chrome runtime: {'READY' if chrome else 'MISSING'}")
    submitted=Path.home()/".local/share/deckctl/media/submitted"
    for sid,name in services.items():
        launcher=(appdir/f"deck-media-{sid}.desktop").exists()
        steam=_steam_shortcut_has(name)
        receipt=(submitted/sid).exists()
        if launcher and steam: state="READY"
        elif launcher and receipt: state="PENDING STEAM REFRESH"
        elif launcher: state="LAUNCHER ONLY"
        else: state="NOT CONFIGURED"
        print(f"{name:<14} {state}")
    if not _media_configured():
        print("\nRepair/configure: ./bin/deckctl media setup")

def media_setup():
    helper=Path.home()/".local/share/deckctl/media/setup-media.sh"
    if not helper.exists():
        print("Media setup helper is not staged yet. Run: ./bin/deckctl apply")
        return 1
    print("Reconciling media launchers inline; this step will return here when finished.")
    result=subprocess.run([str(helper),"--all"])
    if result.returncode != 0:
        print(f"Media setup failed with exit code {result.returncode}; it will not be marked complete.")
        return result.returncode
    if not _media_desktop_provisioned():
        print("Media launcher verification failed; it will not be marked complete.")
        return 2
    if _media_configured():
        print("Media verification: READY in Steam.")
    else:
        print("Media verification: DESKTOP PROVISIONED / PENDING STEAM REFRESH.")
        print("Continue setup. Switching to Game Mode later will refresh Steam; rerun `dmedia` there-after from Desktop Mode if you want to audit it.")
    return 0


KEEPER_EXTENSION_ID = "bfogiafebfohielmmehodmfbbebbbpei"
KEEPER_WEBSTORE_URL = "https://chromewebstore.google.com/detail/keeper%C2%AE-password-manager/bfogiafebfohielmmehodmfbbebbbpei"

def _keeper_extension_paths():
    roots = [
        Path.home()/".var/app/com.google.Chrome/config/google-chrome",
        Path.home()/".config/google-chrome",
    ]
    out=[]
    for root in roots:
        if not root.exists():
            continue
        for profile in root.iterdir():
            if not profile.is_dir():
                continue
            p=profile/"Extensions"/KEEPER_EXTENSION_ID
            if p.is_dir(): out.append(p)
    return out

def _keeper_installed():
    return bool(_keeper_extension_paths())

def media_keeper_status():
    print("KEEPER / CHROME")
    print(f"Chrome runtime      {'READY' if _flatpak_installed('com.google.Chrome') else 'MISSING'}")
    print(f"Keeper extension    {'INSTALLED' if _keeper_installed() else 'MISSING'}")
    for p in _keeper_extension_paths(): print(f"  {p}")
    if _keeper_installed():
        print("KeeperFill can autofill browser-backed media tiles when the Keeper vault is signed in/unlocked and the saved record matches the site domain.")
    else:
        print("Install from Keeper's official Chrome Web Store listing with: deckctl media keeper setup")

def media_keeper_setup():
    if not _flatpak_installed("com.google.Chrome"):
        print("Google Chrome is not installed yet. Run the media setup first: deckctl media setup")
        return 2
    cmd=["flatpak","run","com.google.Chrome","--new-window",KEEPER_WEBSTORE_URL]
    try:
        subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception as exc:
        print(f"Could not open Chrome automatically: {exc}")
        print(KEEPER_WEBSTORE_URL)
        return 1
    print("Opened Keeper Security's official Chrome Web Store listing.")
    print("Click Add to Chrome, approve the extension, then sign into/unlock Keeper once in Chrome.")
    print("deckctl never stores your Keeper credentials or browser profile.")
    return 0

def _codex_path():
    candidates=[]
    found=shutil.which("codex")
    if found: candidates.append(Path(found))
    candidates.extend([Path.home()/".local/bin/codex", Path.home()/".codex/bin/codex"])
    for c in candidates:
        try:
            if c.exists() and os.access(c, os.X_OK):
                r=subprocess.run([str(c),"--version"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8)
                if r.returncode==0: return c
        except Exception:
            pass
    return None

def _codex_logged_in():
    c=_codex_path()
    if not c: return False
    try:
        r=subprocess.run([str(c),"login","status"],text=True,capture_output=True,timeout=10)
        return r.returncode==0 and "logged in" in (r.stdout+r.stderr).lower()
    except Exception:
        return False

def setup_steps():
    stage=Path.home()/"Desktop/Deck-Setup-Staged"
    return [
        {
            "id":"heroic",
            "title":"Heroic / Epic Games",
            "description":"Sign into Epic, enable Add games to Steam automatically, then close Heroic. Use Heroic only for install/update management; launch games from Steam Game Mode.",
            "launch":lambda: _launch_flatpak("com.heroicgameslauncher.hgl"),
            "detect":lambda: _flatpak_installed("com.heroicgameslauncher.hgl"),
        },
        {
            "id":"battlenet",
            "title":"Battle.net / WoW",
            "description":"Install Battle.net directly through NonSteamLaunchers' supported command-line launcher selector. Press Yes to install Battle.net only; the full NSL launcher menu is not shown. Complete Battle.net's own installer/login UI, then install WoW/Diablo as desired.",
            "launch":lambda: _launch_terminal_command(shlex.quote(str(ROOT/"modules/gaming/install-battlenet.sh"))),
            "detect":lambda: __import__('deckctl.launchers',fromlist=['battlenet_installed']).battlenet_installed(),
        },
        {
            "id":"decky",
            "title":"Decky Loader",
            "description":"Install the latest stable Decky Loader. Plugin selection and automated plugin reconciliation happen here in Desktop Mode afterward.",
            "launch":lambda: _launch_path(stage/"decky_installer.desktop"),
            "detect":lambda: _decky_loader_present(),
        },
        {
            "id":"decky_plugins",
            "title":"Choose Decky plugins",
            "description":"Choose your managed Decky plugin set using three checkbox sections: Core, Recommended, and Optional. Your choices are saved as desired state.",
            "launch":lambda: decky_select()==0,
            "detect":lambda: _decky_selection_exists(),
        },
        {
            "id":"decky_plugin_install",
            "title":"Install selected Decky plugins",
            "description":"Install the selected plugin set from Decky's official Plugin Store artifacts. Packages are validated before an atomic install. Any plugin that cannot be safely automated is left for guided Store installation.",
            "launch":lambda: __import__('deckctl.decky_installer',fromlist=['install_selected']).install_selected()==0,
            "detect":lambda: _decky_selected_all_installed(),
        },
        {
            "id":"decky_theme",
            "noninteractive":True,
            "title":"Configure CSS Loader components and palette",
            "description":"Install the real Theme Store components and configure their supported Bubble Gum Rave colors automatically in Desktop Mode. Saved settings and the native recovery profile are verified.",
            "launch":lambda: _guided_decky_theme_install(),
            "detect":lambda: _guided_decky_theme_ready(),
        },
        {
            "id":"emudeck",
            "title":"EmuDeck",
            "description":"Run the EmuDeck first-run wizard. If using split storage, choose the DECK-EMU microSD for the Emulation tree. Do not download BIOS/ROM content through deckctl.",
            "launch":lambda: _launch_path(stage/"EmuDeck.desktop"),
            "detect":lambda: __import__('deckctl.setup_cleanup',fromlist=['emudeck_ready']).emudeck_ready(),
        },
        {
            "id":"android",
            "title":"Android / Waydroid / Pokémon Champions",
            "description":"Install the SteamOS-specific Waydroid environment. For Pokémon Champions choose Android 13 with Google Play. Setup opens the bundled launcher when first-run user state is missing. Sign into Google Play if prompted, then close Android to resume provisioning. This is a third-party compatibility path, not an officially supported Pokémon SteamOS build.",
            "launch":lambda: __import__('deckctl.android',fromlist=['retry']).retry()==0,
            "detect":lambda: __import__('deckctl.android',fromlist=['ready']).ready(),
            "noninteractive":True,
        },
        {
            "id":"workspace",
            "title":"Workspace apps: Notion / ChatGPT / Claude",
            "description":"Create clean Chrome app-window shortcuts for Notion, ChatGPT, and Claude. Notion MCP can later authorize ChatGPT/Codex/Claude to read or write your workspace.",
            "launch":lambda: __import__('deckctl.workspace',fromlist=['setup']).setup()==0,
            "detect":lambda: __import__('deckctl.workspace',fromlist=['status']).status()==0,
            "noninteractive":True,
        },
        {
            "id":"media",
            "title":"Optional media apps",
            "description":"Create Netflix, Hulu, Crunchyroll, and Prime Video as real non-Steam shortcuts. The helper installs Chrome if needed and submits all four shortcuts to Steam; sign into each service from Game Mode afterward.",
            "launch":lambda: media_setup()==0,
            "detect":lambda: _media_desktop_provisioned(),
            "noninteractive":True,
        },
        {
            "id":"keeper",
            "title":"Keeper password manager for Chrome",
            "description":"Install KeeperFill from Keeper Security's official Chrome Web Store listing, then sign into/unlock the extension. The Netflix/Hulu/etc. Game Mode tiles use the same normal Chrome profile so Keeper can autofill matching website records. deckctl never stores Keeper credentials.",
            "launch":lambda: media_keeper_setup()==0,
            "detect":lambda: _keeper_installed(),
        },
        {
            "id":"controller_templates",
            "title":"Controller templates",
            "description":"Install our reusable Steam Input template set inline. This copies Valve's desktop/mouse layout when available plus any layouts you have captured with deckctl; it does not overwrite live per-game layouts and does not require a Steam restart during initial Desktop Mode provisioning.",
            "launch":lambda: _guided_controller_templates_install(),
            "detect":lambda: (Path.home()/".local/share/Steam/controller_base/templates/Deck Desktop Mouse.vdf").exists(),
            "noninteractive":True,
        },
        {
            "id":"tailscale",
            "title":"Tailscale",
            "description":"Run the staged SteamOS-specific Tailscale installer. It downloads tailscale-dev/deck-tailscale, prompts for sudo, installs the persistent service, then shows a QR code for tailnet authentication.",
            "launch":lambda: _launch_path(stage/"Install-Tailscale.desktop"),
            "detect":lambda: bool(shutil.which("tailscale") or Path('/opt/tailscale/tailscale').exists() or Path('/opt/tailscale/tailscaled').exists()),
        },
        {
            "id":"moonlight",
            "title":"Moonlight pairing",
            "description":"Pair Moonlight with your Sunshine gaming PC(s). You can skip this now and register/test hosts later with deckctl remote.",
            "launch":lambda: _launch_flatpak("com.moonlight_stream.Moonlight"),
            "detect":lambda: _flatpak_installed("com.moonlight_stream.Moonlight"),
        },
        {
            "id":"chiaki",
            "title":"PlayStation / chiaki-ng",
            "description":"Register your PlayStation locally. Remote PSN testing should be done later from a phone hotspot or another non-home network.",
            "launch":lambda: _launch_flatpak("io.github.streetpea.Chiaki4deck"),
            "detect":lambda: _flatpak_installed("io.github.streetpea.Chiaki4deck"),
        },
        {
            "id":"codex",
            "title":"Codex CLI authentication",
            "description":"Codex is installed directly as a user-level Linux CLI and no longer depends on Distrobox/npm. Complete Sign in with ChatGPT here; deckctl verifies with `codex login status`.",
            "launch":lambda: _launch_terminal_command(f"{shlex.quote(str(_codex_path()))} login" if _codex_path() else f"{shlex.quote(str(ROOT/'modules/dev/install-codex.sh'))} && $HOME/.local/bin/codex login"),
            "detect":lambda: _codex_logged_in(),
        },
    ]

def create_setup_shortcut():
    from . import desktop as desktop_icons
    desktop=desktop_icons.desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut=desktop/"Continue Steam Deck Setup.desktop"
    # Shell-quote the repository path for the inner bash command.
    import shlex
    cmd=f"cd {shlex.quote(str(ROOT))} && ./bin/deckctl setup run; exec bash"
    content="\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=Continue Steam Deck Setup",
        "Comment=Resume guided steamdeck-workstation setup",
        "Exec=" + desktop_icons.exec_line(["konsole", "-e", "bash", "-lc", cmd]),
        f"Icon={desktop_icons.install_icon('setup')}",
        "Terminal=false",
        "StartupNotify=true",
        "",
    ])
    shortcut.write_text(content)
    shortcut.chmod(0o755)
    return shortcut

def setup_open():
    stage=Path.home()/"Desktop/Deck-Setup-Staged"
    stage.mkdir(parents=True, exist_ok=True)
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open",str(stage)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(stage)
    else:
        print(stage)

def setup_status():
    from . import provisioning
    return provisioning.report()

def setup_reset(step_id=None):
    if not step_id:
        save_setup_state({"completed":[],"skipped":[]}); print("Guided setup state reset"); return
    valid={s["id"] for s in setup_steps()}
    if step_id not in valid: raise SystemExit(f"Unknown setup step: {step_id}")
    state=setup_state()
    for k in ("completed","skipped"):
        state[k]=[x for x in state.get(k,[]) if x != step_id]
    state.get("steps",{}).pop(step_id,None)
    save_setup_state(state); print(f"Reset setup step: {step_id}")

def setup_run(step_id=None):
    print("No deckctl terminal commands are required in Game Mode.")
    from . import provisioning
    return provisioning.run(step_id)

def settings():
    return load_json(CONFIG_HOME/"settings.json",{}) or {}

def save_settings(data):
    save_json(CONFIG_HOME/"settings.json",data)

def profile_list():
    active=settings().get("profile")
    for p in sorted((ROOT/"config/profiles").glob("*.json")):
        mark="*" if p.stem==active else " "
        print(f"{mark} {p.stem}")

def profile_show(name):
    p=ROOT/"config/profiles"/f"{name}.json"
    if not p.exists(): raise SystemExit(f"Unknown profile: {name}")
    print(p.read_text(),end='')

def profile_apply(name):
    p=ROOT/"config/profiles"/f"{name}.json"
    if not p.exists(): raise SystemExit(f"Unknown profile: {name}")
    d=settings(); d["profile"]=name; save_settings(d)
    print(f"Active operational profile set to {name}.")
    print("v0.1.2 records desired profile state but intentionally does not force display/TDP settings globally.")

def profile_auto():
    model=detect_hardware().get("model")
    if model in ("oled","lcd"):
        profile_apply(model)
    else:
        print("Hardware model unknown; no OLED/LCD profile selected automatically.")

def launcher_status():
    steam=Path.home()/'.steam/steam'
    hero=False
    try: hero=subprocess.run(['flatpak','info','com.heroicgameslauncher.hgl'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    except FileNotFoundError: pass
    from . import launchers
    battle=launchers.battlenet_path()
    print(f"Steam/Game Mode     {'FOUND' if steam.exists() else 'UNKNOWN'}")
    print(f"Heroic              {'INSTALLED' if hero else 'MISSING'}")
    print(f"Battle.net          {'INSTALLED' if battle else 'MISSING'}")
    if battle: print(f"Battle.net path     {battle}")
    print("Primary frontend    Steam Game Mode")

def channel_show():
    cfg=load_json(ROOT/'config/default.json',{})
    print(settings().get('channel',cfg.get('channel','stable')))

def channel_set(name):
    if name not in ('stable','beta','dev'): raise SystemExit('channel must be stable, beta, or dev')
    d=settings(); d['channel']=name; save_settings(d); print(f"Channel set to {name}")

def update_status():
    cfg=load_json(ROOT/'config/default.json',{})
    repo=cfg.get('release',{}).get('github_repo')
    print(f"Installed version: {(ROOT/'VERSION').read_text().strip()}")
    print(f"Channel: {settings().get('channel',cfg.get('channel','stable'))}")
    if not repo:
        print("GitHub release source is not configured yet. After you publish the repo, set config/default.json release.github_repo to owner/repo.")
        return
    if not shutil.which('curl'):
        print('curl unavailable; cannot query release metadata'); return
    url=f"https://api.github.com/repos/{repo}/releases/latest"
    r=subprocess.run(['curl','-fsSL',url],text=True,capture_output=True)
    if r.returncode:
        print('Unable to query GitHub release metadata'); return
    try: latest=json.loads(r.stdout).get('tag_name','unknown')
    except Exception: latest='unknown'
    print(f"Latest stable release: {latest}")
    print("v0.1.2 reports updates only; it does not self-replace while running.")

def export_state():
    outdir=Path.home()/"DeckExports"; outdir.mkdir(parents=True,exist_ok=True)
    stamp=time.strftime('%Y%m%d-%H%M%S'); out=outdir/f"deck-inventory-{stamp}.json"
    data={"version":(ROOT/'VERSION').read_text().strip(),"hardware":detect_hardware(),"settings":settings(),"modules":{m:module_status(m) for m in topo(enabled_modules())},"storage":storage_health(quiet=True),"games":game_registry(),"hosts":host_registry()}
    save_json(out,data); print(out)

def emulation_bios_audit(source=None):
    roots=[]
    if source: roots=[Path(os.path.expanduser(source))]
    else:
        if (Path.home()/"Emulation/bios").exists(): roots.append(Path.home()/"Emulation/bios")
        if Path('/run/media').exists(): roots += [p for p in Path('/run/media').glob('*/Emulation/bios') if p.exists()]
    files=[]
    for r in roots:
        files += [p for p in r.rglob('*') if p.is_file()]
    names={p.name.lower() for p in files}
    ps1=any(re.fullmatch(r'scph\d+\.bin',n) for n in names)
    print(f"BIOS roots: {', '.join(map(str,roots)) or 'none found'}")
    print(f"PS1 BIOS-style file     {'FOUND' if ps1 else 'NOT FOUND'}")
    print(f"Total BIOS files        {len(files)}")
    print("PS2: validate your legally dumped BIOS with PCSX2/EmuDeck BIOS Checker (filenames vary).")
    print("PS3: firmware is installed through RPCS3, not treated as a generic BIOS-file copy.")
    print("PS Vita: firmware is installed through Vita3K, not treated as a generic BIOS-file copy.")
    print("No copyrighted BIOS/firmware data is downloaded by deckctl.")


def emulation_bios_import(source):
    src=Path(os.path.expanduser(source))
    generic=src/'generic'
    if not generic.is_dir():
        raise SystemExit("Refusing blind BIOS copy: source must contain a generic/ directory. See modules/emulation/private-layout-example/README.txt")
    destinations=[]
    home=Path.home()/"Emulation/bios"
    if home.parent.exists(): destinations.append(home)
    if Path('/run/media').exists():
        destinations += [p for p in Path('/run/media').glob('*/Emulation/bios') if p.parent.exists()]
    if not destinations:
        raise SystemExit("No EmuDeck Emulation/bios destination found. Complete EmuDeck first-run setup first.")
    dest=destinations[0]; dest.mkdir(parents=True,exist_ok=True)
    copied=0
    for f in generic.rglob('*'):
        if not f.is_file(): continue
        rel=f.relative_to(generic); target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(f,target); copied+=1
    print(f"Copied {copied} generic BIOS files to {dest}")
    if (src/'rpcs3').exists(): print("RPCS3 firmware present in private bundle: install it through RPCS3 UI; deckctl did not copy it.")
    if (src/'vita3k').exists(): print("Vita3K firmware present in private bundle: install it through Vita3K UI; deckctl did not copy it.")
    emulation_bios_audit(str(dest))


DECKCTL_ALIASES = load_json(ROOT/"config/aliases.json", {}) or {}

def aliases_show():
    print("DECKCTL ALIASES")
    for name, command in DECKCTL_ALIASES.items():
        print(f"{name:<12} {command}")
    print("\nInstalled from ~/.config/deckctl/shell/aliases.sh. Open a new terminal after first install.")

def _decky_installed_plugins():
    root=Path.home()/"homebrew/plugins"
    found={}
    if not root.is_dir():
        return found
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        name=folder.name
        pj=folder/"plugin.json"
        if pj.exists():
            try:
                d=json.loads(pj.read_text())
                name=d.get("name") or name
            except Exception:
                pass
        valid = all((folder / rel).is_file() for rel in ("plugin.json", "package.json", "dist/index.js"))
        try:
            valid = valid and bool(json.loads(pj.read_text()).get("name")) and isinstance(json.loads((folder/"package.json").read_text()), dict)
        except (OSError, ValueError):
            valid = False
        found[folder.name]={"folder":folder.name,"name":name,"path":str(folder),"valid":valid}
    return found

def _decky_loader_present():
    if os.access(Path.home()/"homebrew/services/PluginLoader", os.X_OK):
        return True
    try:
        r=subprocess.run(["systemctl","is-enabled","plugin_loader.service"],capture_output=True,text=True,timeout=5)
        return r.returncode==0 and r.stdout.strip() in {"enabled", "enabled-runtime", "static"}
    except Exception:
        return False

def _decky_manifest():
    return load_json(ROOT/"modules/decky/plugins.json",{}) or {}

def _decky_selection_path():
    return CONFIG_HOME/"decky-selection.json"

def _decky_default_selection():
    manifest=_decky_manifest()
    selected=[]
    for category in ("core","recommended","optional","avoid_by_default"):
        for item in manifest.get(category,[]):
            if item.get("install_by_default", category in ("core","recommended")):
                selected.append(item.get("folder"))
    return [x for x in selected if x]

def _decky_selected_folders():
    state=load_json(_decky_selection_path(), None)
    if state and isinstance(state.get("selected_folders"), list):
        selected=set(state["selected_folders"])
        revision=state.get("manifest_schema_version",0)
        if not isinstance(revision,int): revision=0
        for upgrade in _decky_manifest().get("selection_upgrades",[]):
            if revision < upgrade["manifest_schema_version"]:
                selected.update(upgrade["add_folders"])
        return selected
    return set(_decky_default_selection())

def _decky_upgrade_selection():
    """Commit explicit release additions only from a mutating install operation.

    Preserve unknown selections and extra metadata. Reading status or cancelling
    installation never writes. Saving a current selection makes later opt-outs
    authoritative, including after an interrupted Store download.
    """
    state=load_json(_decky_selection_path(),None)
    if not isinstance(state,dict) or not isinstance(state.get("selected_folders"),list):
        return
    revision=state.get("manifest_schema_version",0)
    if not isinstance(revision,int): revision=0
    current=_decky_manifest().get("schema_version",0)
    if revision >= current: return
    selected=_decky_selected_folders()
    items=_decky_item_map()
    state.update(manifest_schema_version=current,selected_folders=sorted(selected),
                 selected_plugins=[items.get(x,{}).get("name",x) for x in sorted(selected)])
    save_json(_decky_selection_path(),state)

def _decky_item_map():
    manifest=_decky_manifest(); out={}
    for category in ("core","recommended","optional","avoid_by_default"):
        for item in manifest.get(category,[]):
            row=dict(item); row["category"]=category; out[item.get("folder",item.get("name","?"))]=row
    return out

def _decky_write_selection(selected):
    item_map=_decky_item_map()
    selected=[x for x in selected if x in item_map]
    data={
        "schema_version":1,
        "manifest_schema_version":_decky_manifest().get("schema_version"),
        "updated_at":time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        "selected_folders":sorted(selected),
        "selected_plugins":[item_map[x].get("name",x) for x in sorted(selected)],
    }
    save_json(_decky_selection_path(),data)
    # Desired state lives only in ~/.config/deckctl. Remove obsolete checklist files
    # from older releases so a text file can never be mistaken for install state.
    for stale in (Path.home()/"Desktop/Decky Selected Plugins.txt", Path.home()/"Desktop/Deck-Setup-Staged/DECKY-PLUGINS.txt"):
        try:
            stale.unlink(missing_ok=True)
        except OSError:
            pass
    return data

def _decky_terminal_select(current):
    manifest=_decky_manifest(); selected=set(current)
    print("Decky plugin selector (terminal fallback)")
    print("Enter y/n for each item. Current/default choice is shown in brackets.\n")
    for category in ("core","recommended","optional"):
        print(f"\n=== {category.upper()} ===")
        for item in manifest.get(category,[]):
            folder=item.get("folder"); default=folder in selected
            print(f"\n{item.get('name')}: {item.get('reason','')}")
            ans=input(f"Install? [{'Y' if default else 'N'}] ").strip().lower()
            yes=default if not ans else ans.startswith('y')
            if yes: selected.add(folder)
            else: selected.discard(folder)
    return selected

def _decky_kdialog_select(current):
    manifest=_decky_manifest(); selected=set(current)
    intro=(
        "Choose the Decky plugins this Deck should manage.\n\n"
        "Core and Recommended start checked; Optional starts unchecked. "
        "You can change any checkbox. Your choices become deckctl desired state."
    )
    subprocess.run(["kdialog","--title","Decky Plugin Selection","--msgbox",intro])
    for category in ("core","recommended","optional"):
        items=manifest.get(category,[])
        if not items: continue
        title={"core":"Core plugins","recommended":"Recommended plugins","optional":"Optional plugins"}[category]
        prompt={
            "core":"Core integrations for the managed Deck experience. Checked by default, but you may deselect any you do not want.",
            "recommended":"Recommended polish and convenience integrations. Checked by default.",
            "optional":"Optional extras. Unchecked by default; select only the ones you want.",
        }[category]
        cmd=["kdialog","--title",f"Decky — {title}","--separate-output","--checklist",prompt]
        for item in items:
            folder=item.get("folder") or item.get("name")
            label=f"{item.get('name')} — {item.get('reason','')}"
            cmd += [folder,label,"on" if folder in selected else "off"]
        r=subprocess.run(cmd,text=True,capture_output=True)
        if r.returncode != 0:
            print(f"Decky plugin selection cancelled while editing {category}; previous selection preserved.")
            return None
        chosen={line.strip().strip('"') for line in r.stdout.splitlines() if line.strip()}
        for item in items:
            folder=item.get("folder") or item.get("name")
            if folder in chosen: selected.add(folder)
            else: selected.discard(folder)
    return selected

def decky_select():
    current=_decky_selected_folders()
    if shutil.which("kdialog"):
        selected=_decky_kdialog_select(current)
        if selected is None: return 1
    else:
        selected=_decky_terminal_select(current)
    data=_decky_write_selection(selected)
    print(f"Saved Decky desired state: {_decky_selection_path()}")
    print(f"Selected plugins: {len(data['selected_folders'])}")
    for name in data["selected_plugins"]: print(f"- {name}")
    print("\nNext: guided setup will run `deckctl decky install-selected` here in Desktop Mode.")
    print("Use Game Mode -> QAM -> Decky -> Plugin Store only for any item the automated installer leaves unresolved.")
    if shutil.which("kdialog"):
        subprocess.run(["kdialog","--title","Decky selection saved","--msgbox",
                        "Selection saved.\n\nContinue guided setup in Desktop Mode. deckctl will install the selected plugins automatically from trusted Decky Store artifacts where safe.\n\nGame Mode Plugin Store is only the fallback for unresolved items."])
    return 0

def decky_selected():
    selected=_decky_selected_folders(); item_map=_decky_item_map()
    print("SELECTED DECKY PLUGINS")
    for category in ("core","recommended","optional"):
        rows=[item_map[f] for f in selected if f in item_map and item_map[f].get("category")==category]
        if not rows: continue
        print(f"\n{category.upper()}")
        for item in sorted(rows,key=lambda x:x.get("name","")):
            print(f"- {item.get('name')}: {item.get('reason','')}")
    print(f"\nDesired-state file: {_decky_selection_path()}")

def _decky_selection_exists():
    return _decky_selection_path().exists()

def _decky_selected_all_installed():
    # Plugin folders without a functioning Decky Loader are not a completed install.
    if not _decky_loader_present():
        return False
    selected=_decky_selected_folders(); installed=_decky_installed_plugins()
    return all(folder in installed and installed[folder].get("valid", False) for folder in selected)

def decky_plugins():
    manifest=_decky_manifest()
    policies=load_json(ROOT/"modules/decky/plugin-policies.json",{}) or {}
    policy_map=policies.get("plugins",{})
    installed=_decky_installed_plugins()
    selected=_decky_selected_folders()
    loader_ready=_decky_loader_present()
    selection_source="saved selection" if _decky_selection_exists() else "manifest defaults"
    print("DECKY PLUGIN PLAN")
    print(f"Desired state: {selection_source} ({len(selected)} selected)")
    print(f"Decky loader: {'READY' if loader_ready else 'NOT INSTALLED / NOT DETECTED'}")
    print(f"Installed plugin folders: {len(installed)}")
    for category in ("core","recommended","optional","avoid_by_default"):
        items=manifest.get(category,[])
        if not items:
            continue
        print(f"\n{category.replace('_',' ').upper()}")
        for item in items:
            folder=item.get("folder","")
            present=folder in installed
            desired=folder in selected
            if present and not loader_ready:
                state="ORPHANED"
            elif present and not installed[folder].get("valid", False):
                state="INCOMPLETE"
            elif present and desired:
                state="INSTALLED"
            elif present and not desired:
                state="EXTRA"
            elif desired:
                state="MISSING"
            else:
                state="NOT SELECTED"
            policy=policy_map.get(item.get("name",""),{})
            mode=policy.get("mode","")
            suffix=f" [{mode}]" if mode else ""
            print(f"{state:<10} {item.get('name','?'):<22}{suffix}")
            print(f"           {item.get('reason','')}")
            if policy.get("default"):
                print(f"           Policy: {policy['default']}")
    missing=[]
    for folder in sorted(selected):
        if folder not in installed or not installed[folder].get("valid", False):
            item=_decky_item_map().get(folder,{})
            missing.append(item.get("name",folder))
    print("\nChange selection: deckctl decky select")
    if not loader_ready:
        print("Decky Loader is missing. Plugin folders, if any, are treated as ORPHANED and do not satisfy desired state.")
        print("Resume guided setup or run the official Decky installer from Desktop Mode, then retry: deckctl decky install-selected")
    if missing:
        print("Selected but not installed:")
        for name in missing: print(f"- {name}")
        print("Retry in Desktop Mode with: deckctl decky install-selected")
        print("Use Game Mode -> QAM (...) -> Decky -> Plugin Store only for unresolved fallback items.")
    elif loader_ready:
        print("All selected Decky plugins are detected with Decky Loader present.")
    from . import css_stack
    print("CSS stack: " + css_stack.readiness()[1])
    print("Reconcile in Desktop Mode: deckctl decky css apply")

def _decky_cssloader_desired():
    return "SDH-CssLoader" in _decky_selected_folders()

def _guided_decky_theme_ready():
    if not _decky_cssloader_desired():
        return True
    from . import css_stack
    return css_stack.readiness()[0]

def _guided_decky_theme_install():
    if not _decky_cssloader_desired():
        print("CSS Loader is not selected; palette configuration is not applicable.")
        return True
    return decky_theme_install()==0

def decky_theme_install():
    # Backward-compatible command; Bubble Gum Rave is configuration, never a package.
    from . import css_stack
    return css_stack.apply()

def decky_theme_status():
    from . import css_stack
    return css_stack.status()
