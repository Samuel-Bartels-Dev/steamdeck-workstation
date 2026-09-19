from __future__ import annotations
import argparse, json, subprocess, sys
from . import apps, containers, core, controller, storage_ops, library, lifecycle, network, hostkit, decky_installer, css_stack, reliability, terminal, launchers, android, workspace, desktop, provisioning, upgrade_plan, shortcut_ops

def repo_validate():
    return subprocess.run([sys.executable,str(core.ROOT/'tests/contract/test_repo.py')],cwd=core.ROOT).returncode

def build_parser():
    p=argparse.ArgumentParser(
        prog='deckctl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Steam Deck workstation control plane

Common workflows:
  deckctl setup run              Resume first-run guided setup
  deckctl health                 One-page health summary
  deckctl doctor [module]        Diagnose a module
  deckctl android retry          Retry Android install/repair
  deckctl decky plugins          Audit selected Decky plugins
  deckctl media status           Check media shortcuts
  deckctl terminal status        Check terminal/tmux stack

Command groups:
  Setup & health      setup, detect, plan, apply, verify, doctor, health, inventory
  Gaming & UI        launcher, controller, decky, media, android, workspace, desktop, provisioning, upgrade_plan, shortcut_ops, library
  Storage/emulation  storage, emulation, backup, restore
  Remote/network     remote, network, travel
  Reliability        post-update, ui, update, profile, support-bundle
  Developer          terminal, ai, repo, aliases, channel, export

Tip: run `deckctl <command> -h` for command-specific help.
""")
    sp=p.add_subparsers(dest='cmd',required=True)
    apps.add_parser(sp)
    containers.add_parser(sp)
    sp.add_parser('detect'); sp.add_parser('plan'); sp.add_parser('apply')
    v=sp.add_parser('verify'); v.add_argument('--json',action='store_true')
    d=sp.add_parser('doctor'); d.add_argument('module',nargs='?')
    inv=sp.add_parser('inventory'); inv.add_argument('--json',action='store_true')
    sp.add_parser('support-bundle')
    pu=sp.add_parser('post-update')
    ui=sp.add_parser('ui'); uisp=ui.add_subparsers(dest='sub',required=True); us=uisp.add_parser('safe'); us.add_argument('--minimal',action='store_true'); uisp.add_parser('restore')
    st=sp.add_parser('storage'); ssp=st.add_subparsers(dest='sub',required=True); sh=ssp.add_parser('health'); sh.add_argument('--json',action='store_true'); sr=ssp.add_parser('recommend'); sr.add_argument('game'); sr.add_argument('--system'); ssp.add_parser('migration-status'); smv=ssp.add_parser('verify-migration'); smv.add_argument('--json',action='store_true'); ssp.add_parser('migrate-emulation'); sf=ssp.add_parser('finalize-emulation-migration'); sf.add_argument('--yes',action='store_true')
    gm=sp.add_parser('game'); gsp=gm.add_subparsers(dest='sub',required=True); gr=gsp.add_parser('register'); gr.add_argument('name'); gr.add_argument('--launcher',required=True); gr.add_argument('--path',required=True); gr.add_argument('--storage-role',choices=['internal','pc_games','emulation'],required=True); grd=gsp.add_parser('ready'); grd.add_argument('name'); gd=gsp.add_parser('doctor'); gd.add_argument('name')
    rm=sp.add_parser('remote'); rsp=rm.add_subparsers(dest='sub',required=True); rr=rsp.add_parser('register'); rr.add_argument('name'); rr.add_argument('--target',required=True); rr.add_argument('--mac'); rr.add_argument('--relay'); rr.add_argument('--sunshine-port',type=int,default=47984); rt=rsp.add_parser('test'); rt.add_argument('name'); rw=rsp.add_parser('wake'); rw.add_argument('name'); rwait=rsp.add_parser('wait'); rwait.add_argument('name'); rwait.add_argument('--timeout',type=int,default=90); rh=rsp.add_parser('host-kit'); rh.add_argument('name'); rh.add_argument('--out')
    bk=sp.add_parser('backup'); bksp=bk.add_subparsers(dest='sub',required=True); bksp.add_parser('saves'); rst=sp.add_parser('restore'); rst.add_argument('archive',nargs='?'); rst.add_argument('--dry-run',action='store_true'); rst.add_argument('--category',action='append',help='Restore only this category; repeat to select several.'); rst.add_argument('--yes',action='store_true')
    tr=sp.add_parser('travel'); tsp=tr.add_subparsers(dest='sub',required=True); tsp.add_parser('check'); tsp.add_parser('lock'); tsp.add_parser('unlock')
    ai=sp.add_parser('ai'); asp=ai.add_subparsers(dest='sub',required=True); ac=asp.add_parser('context'); ac.add_argument('module'); at=asp.add_parser('task'); at.add_argument('module'); at.add_argument('description')
    repo=sp.add_parser('repo'); rsp2=repo.add_subparsers(dest='sub',required=True); rsp2.add_parser('validate')
    pf=sp.add_parser('profile'); psp=pf.add_subparsers(dest='sub',required=True); psp.add_parser('list'); pshow=psp.add_parser('show'); pshow.add_argument('name'); papply=psp.add_parser('apply'); papply.add_argument('name'); psp.add_parser('auto'); pexp=psp.add_parser('export'); pexp.add_argument('--out'); pimp=psp.add_parser('import'); pimp.add_argument('archive')
    la=sp.add_parser('launcher'); lasp=la.add_subparsers(dest='sub',required=True); lasp.add_parser('status'); linst=lasp.add_parser('install'); linst.add_argument('name',choices=['battlenet'])
    ch=sp.add_parser('channel'); ch.add_argument('name',nargs='?')
    up=sp.add_parser('update'); upsp=up.add_subparsers(dest='update_sub',required=False); upsp.add_parser('check'); ua=upsp.add_parser('apply'); ua.add_argument('--archive'); upsp.add_parser('rollback'); upr=upsp.add_parser('preview'); upg=upr.add_mutually_exclusive_group(required=True); upg.add_argument('--archive'); upg.add_argument('--source',help='Candidate release directory to inspect without execution.'); upr.add_argument('--json',action='store_true')
    sp.add_parser('export')
    em=sp.add_parser('emulation'); emsp=em.add_subparsers(dest='sub',required=True); eb=emsp.add_parser('bios-audit'); eb.add_argument('--source'); ebi=emsp.add_parser('bios-import'); ebi.add_argument('--source',required=True)
    media=sp.add_parser('media'); mediasp=media.add_subparsers(dest='sub',required=True); mediasp.add_parser('setup'); mediasp.add_parser('status'); keeper=mediasp.add_parser('keeper'); ksp=keeper.add_subparsers(dest='keeper_sub',required=True); ksp.add_parser('setup'); ksp.add_parser('status')
    net=sp.add_parser('network'); netsp=net.add_subparsers(dest='sub',required=True); nt=netsp.add_parser('test'); nt.add_argument('--host'); nt.add_argument('--json',action='store_true')
    hl=sp.add_parser('health'); hl.add_argument('--json',action='store_true')
    term=sp.add_parser('terminal'); termsp=term.add_subparsers(dest='sub',required=True); ts=termsp.add_parser('status'); ts.add_argument('--json',action='store_true'); ta=termsp.add_parser('apply'); ta.add_argument('--config-only',action='store_true'); ta.add_argument('--refresh',action='store_true'); trst=termsp.add_parser('reset'); trst.add_argument('--keep-tools',action='store_true'); termsp.add_parser('font-check'); prompt=termsp.add_parser('prompt'); promptsp=prompt.add_subparsers(dest='prompt_sub',required=True); promptsp.add_parser('status'); puse=promptsp.add_parser('use'); puse.add_argument('engine',choices=['posh','starship']); tmx=termsp.add_parser('tmux'); tmxsp=tmx.add_subparsers(dest='tmux_sub',required=True); tmxsp.add_parser('status'); tmxsp.add_parser('apply')
    ctl=sp.add_parser('controller'); csp=ctl.add_subparsers(dest='sub',required=True); csp.add_parser('status'); cr=csp.add_parser('recommend'); cr.add_argument('target'); cr.add_argument('--system'); csp.add_parser('discover'); cc=csp.add_parser('capture'); cc.add_argument('name'); cc.add_argument('--source',required=True); csp.add_parser('install-templates'); co=csp.add_parser('open'); co.add_argument('appid')
    lib=sp.add_parser('library'); lsp=lib.add_subparsers(dest='sub',required=True); laudit=lsp.add_parser('audit'); laudit.add_argument('--json',action='store_true'); lrep=lsp.add_parser('repair'); lrep.add_argument('--yes',action='store_true'); lrep.add_argument('--duplicates',action='store_true',help='Include exact duplicate Steam records in the repair plan.'); lrep.add_argument('--user',help='Limit Steam duplicate repairs to this userdata account ID.')
    sp.add_parser('aliases')
    desk=sp.add_parser('desktop'); desksp=desk.add_subparsers(dest='sub',required=True); desksp.add_parser('apply'); desksp.add_parser('status')
    decky=sp.add_parser('decky'); dkysp=decky.add_subparsers(dest='sub',required=True); dkysp.add_parser('plugins'); dkysp.add_parser('select'); dkysp.add_parser('selected'); di=dkysp.add_parser('install-selected'); di.add_argument('--reinstall',action='store_true'); di.add_argument('--dry-run',action='store_true'); di.add_argument('--yes',action='store_true'); dkysp.add_parser('receipts'); theme=dkysp.add_parser('theme'); thsp=theme.add_subparsers(dest='theme_sub',required=True); thsp.add_parser('install'); thsp.add_parser('status'); css=dkysp.add_parser('css'); csssp=css.add_subparsers(dest='css_sub',required=True); csssp.add_parser('status'); csssp.add_parser('apply'); csssp.add_parser('guide'); csssp.add_parser('profiles'); ccap=csssp.add_parser('capture'); ccap.add_argument('name',nargs='?'); crest=csssp.add_parser('restore'); crest.add_argument('name',nargs='?')
    ad=sp.add_parser('android',help='Install, retry, repair, or deliberately reinstall Waydroid'); adsp=ad.add_subparsers(dest='sub',required=True); ast=adsp.add_parser('status',help='Show real Android readiness'); ast.add_argument('--json',action='store_true'); adsp.add_parser('install',help='Fresh install; choose Android 13 with Google Play'); adsp.add_parser('retry',help='Fresh install if absent; protected repair if an image exists'); adsp.add_parser('repair',help='Protected host repair preserving Android state'); adsp.add_parser('reinstall',help='Deliberately recreate Android using upstream protected archive flow')
    ws=sp.add_parser('workspace',help='Notion/ChatGPT/Claude desktop-style Chrome apps'); wssp=ws.add_subparsers(dest='sub',required=True); wst=wssp.add_parser('status'); wst.add_argument('--json',action='store_true'); wssp.add_parser('setup'); wssp.add_parser('notion-mcp',help='Show Notion MCP agent-connection guidance')
    setup=sp.add_parser('setup'); setupsp=setup.add_subparsers(dest='sub',required=True); srun=setupsp.add_parser('run'); srun.add_argument('--step'); setupsp.add_parser('status'); sreport=setupsp.add_parser('report'); sreport.add_argument('--json',action='store_true'); setupsp.add_parser('open'); sclean=setupsp.add_parser('cleanup'); sclean.add_argument('--dry-run',action='store_true'); srst=setupsp.add_parser('reset'); srst.add_argument('step',nargs='?')
    hp=sp.add_parser('help'); hp.add_argument('command',nargs='*')
    p.add_argument('--version', action='version', version=(core.ROOT/'VERSION').read_text().strip())
    from .helptext import decorate
    decorate(p)
    return p


def main(argv=None):
    p=build_parser()
    args=p.parse_args(argv)
    if args.cmd=='help':
        parser=p
        for word in args.command:
            children=next((a.choices for a in parser._actions if isinstance(a,argparse._SubParsersAction)), {})
            if word not in children:
                p.error(f'unknown help command: {word}')
            parser=children[word]
        parser.print_help()
        return 0
    if args.cmd=='apps': return apps.dispatch(args)
    if args.cmd=='containers': return containers.dispatch(args)
    if args.cmd=='detect': print(json.dumps(core.detect_hardware(),indent=2)); return 0
    if args.cmd=='plan': core.plan(); return 0
    if args.cmd=='apply': return core.apply()
    if args.cmd=='verify': return core.status_exit(core.verify(args.json))
    if args.cmd=='doctor': return core.doctor(args.module)
    if args.cmd=='inventory': core.inventory(args.json); return 0
    if args.cmd=='support-bundle': reliability.support_bundle(); return 0
    if args.cmd=='post-update': return reliability.post_update()
    if args.cmd=='ui' and args.sub=='safe': return reliability.ui_safe(args.minimal)
    if args.cmd=='ui' and args.sub=='restore': return reliability.ui_restore()
    if args.cmd=='storage' and args.sub=='health': core.storage_health(args.json); return 0
    if args.cmd=='storage' and args.sub=='recommend': core.storage_recommend(args.game,args.system); return 0
    if args.cmd=='storage' and args.sub=='verify-migration': return 0 if storage_ops.verify_migration(args.json)['status']=='VERIFIED' else 2
    if args.cmd=='storage' and args.sub=='migration-status': storage_ops.migration_status(); return 0
    if args.cmd=='storage' and args.sub=='migrate-emulation': return storage_ops.migrate_emulation()
    if args.cmd=='storage' and args.sub=='finalize-emulation-migration': return storage_ops.finalize_emulation(args.yes)
    if args.cmd=='game' and args.sub=='register': core.game_register(args.name,args.launcher,args.path,args.storage_role); return 0
    if args.cmd=='game' and args.sub=='ready': return core.game_ready(args.name,False)
    if args.cmd=='game' and args.sub=='doctor': return core.game_ready(args.name,True)
    if args.cmd=='remote' and args.sub=='register': core.remote_register(args.name,args.target,args.mac,args.relay,args.sunshine_port); return 0
    if args.cmd=='remote' and args.sub=='test': core.remote_test(args.name); return 0
    if args.cmd=='remote' and args.sub=='wake': core.remote_wake(args.name); return 0
    if args.cmd=='remote' and args.sub=='wait': return core.remote_wait(args.name,args.timeout)
    if args.cmd=='remote' and args.sub=='host-kit': hostkit.build(args.name,args.out); return 0
    if args.cmd=='backup' and args.sub=='saves': lifecycle.backup_saves(); return 0
    if args.cmd=='restore': return lifecycle.restore(args.archive,args.dry_run,args.category,args.yes)
    if args.cmd=='travel' and args.sub=='check': return core.travel_check()
    if args.cmd=='travel' and args.sub=='lock': core.travel_lock(True); return 0
    if args.cmd=='travel' and args.sub=='unlock': core.travel_lock(False); return 0
    if args.cmd=='ai' and args.sub=='context': core.ai_context(args.module); return 0
    if args.cmd=='ai' and args.sub=='task': core.ai_task(args.module,args.description); return 0
    if args.cmd=='repo' and args.sub=='validate': return repo_validate()
    if args.cmd=='profile' and args.sub=='list': core.profile_list(); return 0
    if args.cmd=='profile' and args.sub=='show': core.profile_show(args.name); return 0
    if args.cmd=='profile' and args.sub=='apply': core.profile_apply(args.name); return 0
    if args.cmd=='profile' and args.sub=='auto': core.profile_auto(); return 0
    if args.cmd=='profile' and args.sub=='export': reliability.profile_export(args.out); return 0
    if args.cmd=='profile' and args.sub=='import': return reliability.profile_import(args.archive)
    if args.cmd=='launcher' and args.sub=='status': core.launcher_status(); return 0
    if args.cmd=='launcher' and args.sub=='install' and args.name=='battlenet': return launchers.install_battlenet()
    if args.cmd=='channel':
        if args.name: core.channel_set(args.name)
        else: core.channel_show()
        return 0
    if args.cmd=='update' and args.update_sub in (None,'check'): return reliability.update_check()
    if args.cmd=='update' and args.update_sub=='preview': return upgrade_plan.preview(args.archive,args.source,args.json)
    if args.cmd=='update' and args.update_sub=='apply': return reliability.update_apply(args.archive)
    if args.cmd=='update' and args.update_sub=='rollback': return reliability.update_rollback()
    if args.cmd=='export': core.export_state(); return 0
    if args.cmd=='emulation' and args.sub=='bios-audit': core.emulation_bios_audit(args.source); return 0
    if args.cmd=='emulation' and args.sub=='bios-import': core.emulation_bios_import(args.source); return 0
    if args.cmd=='aliases': core.aliases_show(); return 0
    if args.cmd=='desktop': return desktop.apply() if args.sub=='apply' else desktop.status()
    if args.cmd=='decky' and args.sub=='plugins': core.decky_plugins(); return 0
    if args.cmd=='decky' and args.sub=='select': return core.decky_select()
    if args.cmd=='decky' and args.sub=='selected': core.decky_selected(); return 0
    if args.cmd=='decky' and args.sub=='install-selected': return decky_installer.install_selected(reinstall=args.reinstall,dry_run=args.dry_run,assume_yes=args.yes)
    if args.cmd=='decky' and args.sub=='receipts': decky_installer.receipts(); return 0
    if args.cmd=='decky' and args.sub=='theme' and args.theme_sub=='install': return core.decky_theme_install()
    if args.cmd=='decky' and args.sub=='theme' and args.theme_sub=='status': return core.decky_theme_status()
    if args.cmd=='decky' and args.sub=='css' and args.css_sub=='apply': return css_stack.apply()
    if args.cmd=='decky' and args.sub=='css' and args.css_sub=='status': return css_stack.status()
    if args.cmd=='decky' and args.sub=='css' and args.css_sub=='guide': return css_stack.guide()
    if args.cmd=='decky' and args.sub=='css' and args.css_sub=='profiles': return reliability.css_profiles_list()
    if args.cmd=='decky' and args.sub=='css' and args.css_sub=='capture': return reliability.css_profile_capture(args.name)
    if args.cmd=='decky' and args.sub=='css' and args.css_sub=='restore': return reliability.css_profile_restore(args.name)
    if args.cmd=='media' and args.sub=='setup': return core.media_setup()
    if args.cmd=='media' and args.sub=='status': core.media_status(); return 0
    if args.cmd=='media' and args.sub=='keeper' and args.keeper_sub=='setup': return core.media_keeper_setup()
    if args.cmd=='media' and args.sub=='keeper' and args.keeper_sub=='status': core.media_keeper_status(); return 0
    if args.cmd=='network' and args.sub=='test': network.test(args.host,args.json); return 0
    if args.cmd=='health': lifecycle.health(args.json); return 0
    if args.cmd=='terminal' and args.sub=='status': return terminal.status(args.json)
    if args.cmd=='terminal' and args.sub=='apply': return terminal.apply(args.config_only,args.refresh)
    if args.cmd=='terminal' and args.sub=='reset': return terminal.reset(args.keep_tools)
    if args.cmd=='terminal' and args.sub=='font-check': return terminal.font_check()
    if args.cmd=='terminal' and args.sub=='prompt' and args.prompt_sub=='status': return terminal.prompt_status()
    if args.cmd=='terminal' and args.sub=='prompt' and args.prompt_sub=='use': return terminal.prompt_use(args.engine)
    if args.cmd=='terminal' and args.sub=='tmux' and args.tmux_sub=='status': return terminal.tmux_status()
    if args.cmd=='terminal' and args.sub=='tmux' and args.tmux_sub=='apply': return terminal.tmux_apply()
    if args.cmd=='controller' and args.sub=='status': controller.status(); return 0
    if args.cmd=='controller' and args.sub=='recommend': controller.recommend(args.target,args.system); return 0
    if args.cmd=='controller' and args.sub=='discover': controller.discover(); return 0
    if args.cmd=='controller' and args.sub=='capture': controller.capture(args.name,args.source); return 0
    if args.cmd=='controller' and args.sub=='install-templates': return controller.install_templates()
    if args.cmd=='controller' and args.sub=='open': return controller.open_controller(args.appid)
    if args.cmd=='library' and args.sub=='audit': shortcut_ops.audit(args.json); return 0
    if args.cmd=='library' and args.sub=='repair': return shortcut_ops.repair(args.yes,args.duplicates,args.user)
    if args.cmd=='android' and args.sub=='status': return android.status(args.json)
    if args.cmd=='android' and args.sub=='install': return android.install()
    if args.cmd=='android' and args.sub=='retry': return android.retry()
    if args.cmd=='android' and args.sub=='repair': return android.repair()
    if args.cmd=='android' and args.sub=='reinstall': return android.reinstall()
    if args.cmd=='workspace' and args.sub=='status': return workspace.status(args.json)
    if args.cmd=='workspace' and args.sub=='setup': return workspace.setup()
    if args.cmd=='workspace' and args.sub=='notion-mcp': return workspace.notion_mcp()
    if args.cmd=='setup' and args.sub=='run': return core.setup_run(args.step)
    if args.cmd=='setup' and args.sub=='report': return provisioning.report(args.json)
    if args.cmd=='setup' and args.sub=='status': core.setup_status(); return 0
    if args.cmd=='setup' and args.sub=='open': core.setup_open(); return 0
    if args.cmd=='setup' and args.sub=='cleanup':
        from . import setup_cleanup
        return setup_cleanup.cleanup(args.dry_run)
    if args.cmd=='setup' and args.sub=='reset': core.setup_reset(args.step); return 0
    return 1
