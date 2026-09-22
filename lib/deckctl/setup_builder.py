"""Deck-friendly setup selection UI; selections are desired state, never installs."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from . import apps, core, gaming_options, css_stack, component_options


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
    owners={key:item.get('module') for key,item in apps.catalog().items()}
    roots=set(module_roots)
    unknown=roots-set(core.module_manifests())
    if unknown:
        raise ValueError('Unknown module: '+', '.join(sorted(unknown)))
    for app in apps.known(selected_apps):
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


def plugin_items():
    items=core._decky_item_map()
    for key in core._decky_selected_folders():
        items.setdefault(key, {'name': key, 'reason': 'Existing custom plugin selection'})
    return [{'id': key, 'name': item['name'], 'summary': item.get('reason', '')}
            for key, item in items.items()]


def save_plan(modules, selected_apps, launchers=None, plugins=None, css=None, components=None, palette=None, appearance_choices=None):
    from . import appearance
    if appearance_choices is not None: appearance_choices = appearance.validate(appearance_choices)
    if palette is not None: palette=css_stack.validate_palette(palette)
    if components is not None: components=component_options.validate(components)
    if css is not None: css=css_stack.validate_selection(css)
    if launchers is not None: launchers=gaming_options.validate(launchers)
    if plugins is not None:
        known={item['id'] for item in plugin_items()}
        if not isinstance(plugins, (list, set, tuple)) or any(not isinstance(x,str) or x not in known for x in plugins):
            raise ValueError('Invalid Decky plugin selection')
    # Normalize required owners for all frontends. An individual selection must
    # not depend on a hidden category checkbox having been clicked first.
    if len(modules) != len(set(modules)):
        raise ValueError('Duplicate module selection.')
    roots = set(modules)
    if launchers: roots.add('gaming')
    if css:
        plugins = sorted(set(plugins or []) | {'SDH-CssLoader'})
    if plugins: roots.add('decky')
    if components is not None:
        roots.update(group for group, names in components.items() if names)
    modules = _app_module_roots(roots, selected_apps)
    files=[core.CONFIG_HOME/'modules.json', core.CONFIG_HOME/'apps.json']
    if launchers is not None: files.append(core.CONFIG_HOME/'gaming-selection.json')
    if plugins is not None: files.append(core._decky_selection_path())
    if css is not None or palette is not None: files.append(core.CONFIG_HOME/'css-selection.json')
    if components is not None: files.append(core.CONFIG_HOME/'components.json')
    if appearance_choices is not None: files.append(core.CONFIG_HOME/'appearance.json')
    previous=[p.read_bytes() if p.exists() else None for p in files]
    try:
        save_modules(modules)
        apps.save(apps.known(selected_apps))
        if launchers is not None:
            core.save_json(core.CONFIG_HOME/'gaming-selection.json', {'selected': launchers})
        if plugins is not None:
            state=core.load_json(core._decky_selection_path(), {})
            items=core._decky_item_map()
            state.update(schema_version=1, explicit_selection=True,
                         manifest_schema_version=core._decky_manifest()['schema_version'],
                         selected_folders=sorted(set(plugins)),
                         selected_plugins=[items.get(x,{}).get('name',x) for x in sorted(set(plugins))])
            core.save_json(core._decky_selection_path(), state)
        if css is not None or palette is not None:
            css_state = core.load_json(core.CONFIG_HOME/'css-selection.json', {})
            css_state['selected'] = css if css is not None else css_stack.selection()
            if palette is not None: css_state['palette'] = palette
            core.save_json(core.CONFIG_HOME/'css-selection.json', css_state)
        if components is not None:
            core.save_json(core.CONFIG_HOME/'components.json', components)
        if appearance_choices is not None:
            core.save_json(core.CONFIG_HOME/'appearance.json', appearance_choices)
    except (OSError,ValueError):
        for path,old in zip(files,previous):
            if old is None: path.unlink(missing_ok=True)
            else: path.write_bytes(old)
        raise


def configure_ui():
    if (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')) and (shutil.which('qml6') or shutil.which('qml')):
        from . import setup_window
        return setup_window.launch(os.environ.get('DECKCTL_SETUP_PLAN_ONLY')=='1')
    if not sys.stdin.isatty():
        print('Open setup in Desktop Mode or an interactive terminal.',file=sys.stderr)
        return 2
    data=catalog(); roots=set(core.enabled_modules()); selected=set(apps.selection())
    try:
        for group in data['groups']:
            roots=_terminal_checklist(group['title'],group['description'],group['modules'],roots)
        selected=_terminal_checklist('Desktop apps','Optional apps; existing installations are kept.',_app_items(),selected)
        launchers=set(gaming_options.selection()); plugins=set(core._decky_selected_folders()); css=set(css_stack.selection())
        if 'gaming' in roots:
            launchers=_terminal_checklist('Launchers and tools','Choose each item independently.',gaming_options.ITEMS,launchers)
        if 'decky' in roots:
            plugins=_terminal_checklist('Decky plugins','Every plugin is optional.',plugin_items(),plugins)
        if 'decky' in roots and 'SDH-CssLoader' in plugins:
            css=_terminal_checklist('CSS Loader components','Every component is optional.',css_stack.selection_items(),css)
        components=component_options.selection()
        for group, items in component_options.catalog().items():
            if group in roots:
                components[group]=sorted(_terminal_checklist(group.title()+' tools','Choose each item independently.',items,set(components[group])))
        normalized=_app_module_roots(roots,selected)
        print(_summary(normalized,sorted(selected),set(normalized)-roots-{'base'}))
        if input('Save this plan? [y/N] ').strip().lower() not in ('y','yes'):
            return 0
        save_plan(normalized,selected,launchers,plugins,css,components)
        print('Plan saved. Run deckctl apply, then deckctl setup run.')
        return 0
    except (KeyboardInterrupt,EOFError):
        print('Cancelled. Your previous plan is unchanged.')
        return 0


def configure_defaults(minimal=False,module_names=None,app_names=None,component_names=None):
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
    components={key: [] for key in component_options.CATALOG} if minimal else component_names
    save_plan(modules, selected, components=components)
    print(_summary(modules,selected))
    print('Setup plan saved. Review with `deckctl plan`, then run `deckctl apply`.')
    return 0


def dispatch(args):
    try:
        if args.defaults:
            defaults=core.load_json(core.ROOT/'config/default.json',{}).get('modules',{})
            return configure_defaults(module_names=[key for key,value in defaults.items() if value],
                                     app_names=list(apps.catalog()), component_names=component_options.defaults())
        if args.minimal: return configure_defaults(minimal=True)
        if args.module or args.app:
            modules=args.module if args.module else core.enabled_modules()
            selected=args.app if args.app else apps.selection()
            return configure_defaults(module_names=modules,app_names=selected)
        return configure_ui()
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        print(f'Setup chooser: {exc}',file=sys.stderr)
        return 1
