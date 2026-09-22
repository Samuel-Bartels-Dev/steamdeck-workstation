"""Shared palette selection for opt-in, repository-managed appearance files."""
import re
from . import core

TARGETS = [
    {'id': 'ghostty', 'name': 'Ghostty', 'summary': 'Terminal background, cursor, selection and ANSI colors'},
    {'id': 'fastfetch', 'name': 'Fastfetch', 'summary': 'The ff artwork, headings and system information'},
    {'id': 'oh-my-posh', 'name': 'Oh My Posh', 'summary': 'Your shell prompt, path and Git status'},
    {'id': 'starship', 'name': 'Starship', 'summary': 'Colors for the alternative shell prompt'},
    {'id': 'konsole', 'name': 'Konsole', 'summary': 'The managed terminal profile and color scheme'},
    {'id': 'tmux', 'name': 'tmux', 'summary': 'Session status and pane borders'},
    {'id': 'css', 'name': 'Supported Decky themes', 'summary': 'Color controls in your selected CSS Loader themes'},
]


def validate(value):
    keys = {item['id'] for item in TARGETS}
    if not isinstance(value, dict) or set(value) - keys or any(type(v) is not bool for v in value.values()):
        raise ValueError('Invalid appearance choices')
    return {key: value.get(key, True) for key in sorted(keys)}


def selection():
    return validate(core.load_json(core.CONFIG_HOME/'appearance.json', {}))


def enabled(target):
    return selection()[target]


def render(text):
    from . import css_stack
    palette = next(p for p in css_stack.palette_catalog() if p['id'] == css_stack.palette_id())
    if palette['id'] == 'bubblegum': return text
    colors = dict(palette['colors'])
    roles = palette['css_palette']
    colors.update({'#ff2fb3': roles['hot'], '#100a1d': roles['panel'], '#fff7ff': roles['text'],
                   '#c9b9d8': roles['muted'], '#e9f7ff': roles['text'], '#d9c8ff': roles['text'],
                   '#180e20': roles['panel'], '#180d26': roles['panel'], '#9b87ad': roles['muted'],
                   '#241332': palette['colors']['#1a1128']})
    # Hex colors in Ghostty, JSON, TOML and tmux configuration.
    text = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: colors.get(m[0].lower(), m[0]), text)
    # Konsole uses decimal RGB triplets instead of hex colors.
    def rgb(match):
        values = [int(x) for x in match[1].split(',')]
        original = '#' + ''.join(f'{x:02x}' for x in values)
        target = colors.get(original, original)
        return 'Color=' + ','.join(str(int(target[i:i+2], 16)) for i in (1, 3, 5))
    text = re.sub(r'^Color=(\d+,\d+,\d+)$', rgb, text, flags=re.M)
    return text.replace('BUBBLE GUM RAVE', palette['name'].upper()).replace('Bubble Gum Rave', palette['name'])


def write(source, destination):
    if destination.is_symlink():
        raise ValueError('Refusing to replace a symlink: '+str(destination))
    text = render(source.read_text())
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.read_text() != text:
        destination.write_text(text)
