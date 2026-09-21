"""Individual launcher preferences; absent preferences retain legacy defaults."""
from . import core

ITEMS = [
    {'id': 'heroic', 'name': 'Heroic', 'summary': 'Epic, GOG and Amazon games in one launcher'},
    {'id': 'battlenet', 'name': 'Battle.net', 'summary': 'Blizzard games · guided installation and sign-in'},
    {'id': 'protonplus', 'name': 'ProtonPlus', 'summary': 'Optional compatibility-tool manager'},
    {'id': 'nonsteamlaunchers', 'name': 'Other launchers helper', 'summary': 'Stage NonSteamLaunchers for manual vendor choices'},
]


def selection():
    value = core.load_json(core.CONFIG_HOME/'gaming-selection.json', None)
    return validate(value['selected']) if value is not None else [item['id'] for item in ITEMS]


def validate(values):
    known = {item['id'] for item in ITEMS}
    if not isinstance(values, (list, set, tuple)) or any(not isinstance(x, str) or x not in known for x in values):
        raise ValueError('Invalid launcher selection')
    return sorted(set(values))


def selected(key):
    return key in selection()


if __name__ == '__main__':
    import sys
    sys.exit(0 if selected(sys.argv[1]) else 1)
