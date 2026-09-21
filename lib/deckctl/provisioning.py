"""Resumable setup orchestration; vendor implementations remain in their modules."""
from __future__ import annotations
import contextlib
import io
import json
import time
from . import core

# These detectors prove software presence, not successful personal authentication.
ACCOUNT_STEPS={'heroic','battlenet','keeper','tailscale','moonlight','chiaki'}
AUTO_STEPS={'decky','emudeck','android','decky_plugins','decky_plugin_install',
            'decky_theme','workspace','media','controller_templates','codex'}

def selected(step, enabled):
    from . import gaming_options
    if step.get('module') and step['module'] not in enabled:
        return False
    return step['id'] not in ('heroic', 'battlenet') or gaming_options.selected(step['id'])


def detected(step):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return bool(step['detect']()),None
    except Exception as exc:
        return False,f'{type(exc).__name__}: {exc}'

def record(state,sid,status,message=''):
    state.setdefault('steps',{})[sid]={'status':status,'message':message,'updated_at':time.time()}
    completed=set(state.get('completed',[]));skipped=set(state.get('skipped',[]))
    completed.discard(sid);skipped.discard(sid)
    if status in ('READY','CONFIRMED'):completed.add(sid)
    if status=='DEFERRED':skipped.add(sid)
    state.update(completed=sorted(completed),skipped=sorted(skipped))
    core.save_setup_state(state)

def rows():
    state=core.setup_state();completed=set(state.get('completed',[]));out=[]
    enabled=set(core.topo(core.enabled_modules()))
    for step in core.setup_steps():
        sid=step['id']
        if not selected(step, enabled):
            out.append({'id':sid,'title':step['title'],'status':'NOT_SELECTED','installed':False,
                        'message':'Optional feature is not in the current workstation plan.',
                        'retry':'deckctl setup customize','verification':'feature selection'})
            continue
        found,error=detected(step)
        previous=state.get('steps',{}).get(sid,{})
        if error: status='FAILED'
        elif found and sid in ACCOUNT_STEPS:
            status='CONFIRMED' if sid in completed else 'CONFIG_REQUIRED'
        elif found and (sid in completed or sid in AUTO_STEPS or step.get('noninteractive')):status='READY'
        elif previous.get('status')=='RUNNING':status='INTERRUPTED'
        elif sid in completed:status='STALE'
        elif previous.get('status') in ('FAILED','CONFIG_REQUIRED','DEFERRED'):status=previous['status']
        elif sid in state.get('skipped',[]):status='DEFERRED'
        else:status='PENDING'
        out.append({'id':sid,'title':step['title'],'status':status,'installed':found,
                    'message':error or previous.get('message',''),
                    'retry':('deckctl setup customize' if status=='NOT_SELECTED' else f'deckctl setup run --step {sid}'),
                    'verification':'user-confirmed configuration; software detected' if status=='CONFIRMED' else 'component detector'})
    return out

def report(as_json=False):
    recorded=core.load_json(core.STATE/'provisioning.json',{}).get('modules',{})
    enabled=set(core.topo(core.enabled_modules()))
    live={mid:{**core.module_status(mid),'last_attempt':item} for mid,item in recorded.items() if mid in enabled}
    data={'version':(core.ROOT/'VERSION').read_text().strip(),'steps':rows(),'modules':live}
    bad=[r for r in data['steps'] if r['status'] not in ('READY','CONFIRMED','NOT_SELECTED')]
    module_attention=any(x.get('status') not in ('READY','OPTIONAL') for x in data['modules'].values())
    if as_json:print(json.dumps(data,indent=2))
    else:
        print('\nSETUP COMPLETION REPORT')
        for row in data['steps']:
            print(f"{row['id']:<22} {row['status']:<17} {row['title']}")
            if row['status'] not in ('READY','CONFIRMED'):print('  Retry: '+row['retry'])
            if row['message']:print('  '+row['message'])
        for mid,item in data['modules'].items():
            if item.get('status') not in ('READY','OPTIONAL'):
                print(f"Module {mid}: {item.get('status')} — deckctl apply")
        print('CONFIRMED means you confirmed account/pairing setup; deckctl does not inspect credentials.')
        print('Setup ready.' if not bad and not module_attention else 'Setup needs attention; rerun only the listed steps or use deckctl setup run.')
    if any(x.get('status') in ('FAILED','RUNNING') for x in data['modules'].values()):return 1
    return 2 if bad or module_attention else 0

def run(step_id=None):
    from . import setup_cleanup
    all_steps=core.setup_steps()
    if step_id and step_id not in {s['id'] for s in all_steps}:raise ValueError(f'Unknown setup step: {step_id}')
    enabled=set(core.topo(core.enabled_modules()))
    steps=[s for s in all_steps if selected(s, enabled)]
    if step_id and step_id not in {s['id'] for s in steps}:
        raise ValueError(f'Setup stage {step_id} is not selected; use deckctl setup customize first.')
    if step_id:steps=[s for s in steps if s['id']==step_id]
    setup_cleanup.cleanup();core.create_setup_shortcut()
    state=core.setup_state()
    try:
        for step in steps:
            sid=step['id'];found,error=detected(step)
            completed=sid in state.get('completed',[])
            if found and (completed or sid in AUTO_STEPS or step.get('noninteractive')):
                record(state,sid,'CONFIRMED' if sid in ACCOUNT_STEPS else 'READY')
                print(f"{step['title']}: already verified; skipped")
                continue
            print(f"\n{step['title']}\n{step['description']}")
            while True:
                ans='y' if step.get('noninteractive') else (input('[Y] launch / [s] defer / [m] verify completed / [q] pause: ').strip().lower() or 'y')
                if ans in ('q','quit'):return report()
                if ans in ('s','skip'):
                    record(state,sid,'DEFERRED');break
                if ans not in ('y','yes','m','done'):continue
                launched=True
                if ans in ('y','yes'):
                    record(state,sid,'RUNNING','Operation started; interruption is safe to retry.')
                    try:launched=bool(step['launch']())
                    except Exception as exc:
                        record(state,sid,'FAILED',str(exc));break
                    if launched and not step.get('noninteractive'):
                        follow=input('Complete the visible setup, then ENTER to verify; [s] defer / [q] pause: ').strip().lower()
                        if follow in ('q','quit'):
                            record(state,sid,'CONFIG_REQUIRED','Setup was paused before verification.');return report()
                        if follow in ('s','skip'):
                            record(state,sid,'DEFERRED');break
                found,error=detected(step)
                if launched and found:
                    record(state,sid,'CONFIRMED' if sid in ACCOUNT_STEPS else 'READY')
                else:
                    record(state,sid,'FAILED' if error or not launched else 'CONFIG_REQUIRED',error or 'Verification did not confirm completion; retry the named step.')
                break
            setup_cleanup.cleanup()
    except (KeyboardInterrupt,EOFError):
        print('\nSetup interrupted. Progress retained; deckctl setup run resumes it.')
        return report()
    return report()
