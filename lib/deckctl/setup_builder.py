"""Deck-friendly setup selection UI; selections are desired state, never installs."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from . import apps, core


def catalog():
    data=json.loads((core.ROOT/'config/setup-options.json').read_text())
    modules=core.module_manifests()
    required=data.get('required_modules',[])
    grouped=[item for group in data.get('groups',[]) for item in group.get('modules',[])]
    ids=[item.get('id') for item in grouped]
    if (not required or len(ids)!=len(set(ids)) or set(ids)|set(required)!=set(modules)
            or any(name not in modules for name in required)):
        raise ValueError('Setup selection catalog does not match the module manifests.')
    return data


def _ordered(names):
    order=[item['id'] for group in catalog()['groups'] for item in group['modules']]
    return list(dict.fromkeys(['base']+[name for name in order if name in set(names)]))


def save_modules(names):
    data=catalog(); required=set(data['required_modules']); known=set(core.module_manifests())
    chosen=set(names)|required
    unknown=chosen-known
    if unknown:
        raise ValueError('Unknown module: '+', '.join(sorted(unknown)))
    if len(list(names))!=len(set(names)):
        raise ValueError('Duplicate module selection.')
    # Validate every selected dependency before saving. Dependencies are added
    # during apply, without turning them into extra user-selected roots.
    core.topo(sorted(chosen))
    core.save_json(core.CONFIG_HOME/'modules.json',{'selected':_ordered(chosen)})
    return _ordered(chosen)


def _dialog(title,prompt,items,selected):
    cmd=['kdialog','--title',title,'--geometry','1080x680','--separate-output','--checklist',prompt]
    for item in items:
        key=item['id']
        label=f"{item['name']}  ·  {item.get('summary','')}"
        cmd.extend([key,label,'on' if key in selected else 'off'])
    result=subprocess.run(cmd,text=True,capture_output=True)
    if result.returncode:
        return None
    return {line.strip().strip('"') for line in result.stdout.splitlines() if line.strip()}


def _terminal_checklist(title,description,items,selected):
    print(f'\n{title}\n{description}')
    for item in items:
        key=item['id']; current=key in selected
        answer=input(f"{item['name']} — {item.get('summary','')} [{'Y/n' if current else 'y/N'}] ").strip().lower()
        while answer not in ('','y','yes','n','no'):
            answer=input('Enter y or n: ').strip().lower()
        if (current and answer not in ('n','no')) or (not current and answer in ('y','yes')):
            selected.add(key)
        else:
            selected.discard(key)
    return selected


def _app_items():
    manifests=core.module_manifests()
    return [{'id':key,'name':item['name'],
             'summary':f"{manifests.get(item.get('module'),(None,{'name':'Desktop'}))[1].get('name','Desktop')} · {item['id']}"}
            for key,item in apps.catalog().items()]


def _app_module_roots(module_roots,selected_apps):
    owners={item['id']:item.get('module') for item in apps.catalog().values()}
    roots=set(module_roots)
    for app in selected_apps:
        owner=owners.get(app)
        if owner: roots.add(owner)
    return _ordered(roots)


def _summary(modules,selected_apps,app_added_modules=()):
    full=set(core.topo(modules)); roots=set(modules)
    implicit=sorted(full-roots)
    implicitly_selected=sorted(set(app_added_modules))
    lines=['YOUR STEAM DECK WORKSTATION PLAN','',
           'This saves preferences only. It will not install or remove software.','',
           f"Optional modules selected: {len(roots-set(catalog()['required_modules']))}",
           f"Desktop apps selected: {len(selected_apps)}"]
    if roots-set(catalog()['required_modules']): lines.append('Features: '+', '.join(name.replace('-',' ').title() for name in _ordered(roots) if name!='base'))
    if selected_apps: lines.append('Apps: '+', '.join(selected_apps))
    if implicitly_selected: lines.append('App requirements added: '+', '.join(name.replace('-',' ').title() for name in implicitly_selected))
    if implicit: lines.append('Included automatically for dependencies: '+', '.join(implicit))
    lines += ['', 'NEXT',
              '1  Review with deckctl plan',
              '2  Install selected features with deckctl apply',
              '3  Complete only the sign-in and pairing stages you want with deckctl setup run',
              '', 'Anything you leave out stays out of the setup plan. Existing apps are never removed.']
    return '\n'.join(lines)


def configure_ui():
    data=catalog(); module_roots=set(core.enabled_modules()); app_selection=set(apps.selection())
    graphical=bool(shutil.which('kdialog') and (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')))
    if not graphical and not sys.stdin.isatty():
        print('Setup chooser needs Steam Deck Desktop Mode or an interactive terminal.',file=sys.stderr)
        return 2
    try:
        if graphical:
            intro=('BUILD YOUR STEAM DECK WORKSTATION\n\n'
                   'Choose the features and apps that fit how you use your Deck. Base support stays enabled; '
                   'dependencies are included automatically.\n\n'
                   'This is a plan builder. It does not install or remove anything. You can change these choices later.\n\n'
                   'The current repository defaults are preselected. Clear any stage you do not want, or use '
                   '`deckctl setup customize --minimal` for a base-only setup.')
            if subprocess.run(['kdialog','--title','Steam Deck Workstation · Build your setup',
                               '--geometry','900x520','--msgbox',intro]).returncode:
                return 0
            for index,group in enumerate(data['groups'],start=1):
                chosen=_dialog(f"{index:02d} / {len(data['groups'])}  ·  {group['title']}",
                               group['description']+'\n\nSelect the features you want. Checked items are in your plan.',
                               group['modules'],module_roots)
                if chosen is None:
                    print('Setup choices cancelled; previous settings were kept.')
                    return 0
                module_roots.difference_update(x['id'] for x in group['modules'])
                module_roots.update(chosen)
            selected=_dialog(f"{len(data['groups'])+1:02d}  ·  Desktop apps",
                             'Choose optional desktop apps. Existing installations are kept when deselected.',
                             _app_items(),app_selection)
            if selected is None:
                print('Setup choices cancelled; previous settings were kept.')
                return 0
            app_selection=selected
        else:
            print('Steam Deck Workstation setup builder')
            print('Choose the pieces you want. Choices are saved only after the final review.')
            for group in data['groups']:
                module_roots=_terminal_checklist(group['title'],group['description'],group['modules'],module_roots)
            app_selection=_terminal_checklist('Desktop apps','Optional Flatpak apps; existing installations are kept.',
                                              _app_items(),app_selection)
    except (KeyboardInterrupt,EOFError):
        print('\nSetup choices cancelled; previous settings were kept.')
        return 0
    chosen_roots=set(module_roots)|set(data['required_modules'])
    module_roots=set(_app_module_roots(chosen_roots,app_selection))
    app_added_modules=module_roots-chosen_roots
    normalized=_ordered(module_roots)
    modules_file=core.CONFIG_HOME/'modules.json'; apps_file=core.CONFIG_HOME/'apps.json'
    old_modules=modules_file.read_bytes() if modules_file.exists() else None
    old_apps=apps_file.read_bytes() if apps_file.exists() else None
    if graphical:
        if subprocess.run(['kdialog','--defaultno','--title','Review your workstation plan','--geometry','1080x680',
                           '--yesno',_summary(normalized,sorted(app_selection),app_added_modules)]).returncode:
            print('Setup choices cancelled; previous settings were kept.')
            return 0
    else:
        print('\n'+_summary(normalized,sorted(app_selection),app_added_modules))
        if input('\nSave this setup plan? [Y/n] ').strip().lower() in ('n','no'):
            print('Setup choices cancelled; previous settings were kept.')
            return 0
    try:
        save_modules(normalized)
        apps.save(app_selection)
    except (OSError,ValueError) as exc:
        for path,old in ((modules_file,old_modules),(apps_file,old_apps)):
            if old is None: path.unlink(missing_ok=True)
            else: path.write_bytes(old)
        print(f'Could not save the complete setup plan: {exc}',file=sys.stderr)
        return 1
    print('Setup plan saved. Review with `deckctl plan`, then run `deckctl apply`.')
    print('Selected desktop apps are installed by their modules during `deckctl apply`.')
    print('Use `deckctl setup run` for the selected, individually skippable sign-in and pairing stages.')
    return 0


def configure_defaults(minimal=False,module_names=None,app_names=None):
    if module_names is None:
        defaults=core.load_json(core.ROOT/'config/default.json',{}).get('modules',{})
        modules=['base'] if minimal else [key for key,value in defaults.items() if value]
    else:
        modules=['base',*module_names]
    if app_names is None:
        selected=[] if minimal else apps.selection()
    else:
        selected=apps.known(app_names)
    modules=_app_module_roots(modules,selected)
    save_modules(modules)
    apps.save(selected)
    print(_summary(modules,selected))
    print('Setup plan saved. Review with `deckctl plan`, then run `deckctl apply`.')
    return 0


def dispatch(args):
    try:
        if args.defaults:
            defaults=core.load_json(core.ROOT/'config/default.json',{}).get('modules',{})
            return configure_defaults(module_names=[key for key,value in defaults.items() if value],
                                     app_names=list(apps.catalog()))
        if args.minimal: return configure_defaults(minimal=True)
        if args.module or args.app:
            modules=args.module if args.module else core.enabled_modules()
            selected=args.app if args.app else apps.selection()
            return configure_defaults(module_names=modules,app_names=selected)
        return configure_ui()
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        print(f'Setup chooser: {exc}',file=sys.stderr)
        return 1
