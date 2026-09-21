"""Individual optional tools inside setup categories; legacy defaults remain readable."""
from . import core

CATALOG = {
    'terminal': [('ghostty', 'Ghostty', 'Terminal emulator'), ('tmux', 'tmux', 'Persistent terminal sessions'),
                 ('nvim', 'Neovim', 'Terminal text editor'), ('opencode', 'OpenCode', 'AI coding client'),
                 ('oh-my-posh', 'Oh My Posh', 'Configurable shell prompt'), ('starship', 'Starship', 'Alternative shell prompt'),
                 ('zoxide', 'zoxide', 'Jump to frequently used directories'), ('fzf', 'fzf', 'Fuzzy search for files and history'),
                 ('eza', 'eza', 'Directory listings'), ('bat', 'bat', 'File viewer with syntax highlighting'),
                 ('fastfetch', 'fastfetch', 'System information'), ('fonts', 'JetBrains Mono Nerd Font', 'Font with terminal icons'),
                 ('shell', 'Shell helpers', 'Bash aliases and selected tool integrations'),
                 ('konsole', 'Konsole appearance', 'Bubble Gum Rave profile and colors')],
    'ai-workspace': [('ollama', 'Ollama', 'Local AI engine; no background service'),
                     ('model', 'Qwen 2.5 Coder 1.5B', 'Pre-download local model; requires Ollama')],
    'dev': [('codex', 'Codex CLI', 'Standalone coding agent; sign-in is separate'),
            ('distrobox', 'Development container', 'Create deck-dev using existing Distrobox and Podman')],
    'remote': [('moonlight', 'Moonlight', 'Stream from a Sunshine PC'), ('chiaki', 'chiaki-ng', 'PlayStation Remote Play'),
               ('tailscale', 'Tailscale', 'Private network access; installs a persistent service')],
    'workspace': [('notion', 'Notion', 'Workspace web app; requires Chrome'), ('chatgpt', 'ChatGPT', 'Chat web app; requires Chrome'),
                  ('claude', 'Claude', 'Chat web app; requires Chrome')],
    'media': [('netflix', 'Netflix', 'Game Mode web shortcut; requires Chrome'), ('hulu', 'Hulu', 'Game Mode web shortcut; requires Chrome'),
              ('crunchyroll', 'Crunchyroll', 'Game Mode web shortcut; requires Chrome'), ('prime-video', 'Prime Video', 'Game Mode web shortcut; requires Chrome'),
              ('keeper', 'KeeperFill', 'Browser extension; requires Chrome and sign-in')],
}


def catalog():
    return {group: [{'id': key, 'name': name, 'summary': description} for key, name, description in items]
            for group, items in CATALOG.items()}


def defaults():
    return {group: [item[0] for item in items] for group, items in CATALOG.items()}


def validate(value):
    known = defaults()
    if not isinstance(value, dict) or set(value) - set(known):
        raise ValueError('Invalid component selection')
    for group, names in value.items():
        if not isinstance(names, (list, tuple, set)) or any(not isinstance(x, str) or x not in known[group] for x in names):
            raise ValueError('Invalid component selection for ' + group)
    return {group: sorted(set(names)) for group, names in value.items()}


def selection():
    saved = core.load_json(core.CONFIG_HOME/'components.json', {})
    return {**defaults(), **validate(saved)}


def effective(group):
    names=set(selection()[group])
    if group == 'terminal' and 'ai-workspace' in core.enabled_modules():
        names.add('opencode')
    if group == 'ai-workspace' and 'model' in names:
        names.add('ollama')
    return names


def selected(group, name):
    return name in effective(group)


if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'list':
        print('\n'.join(selection()[sys.argv[2]]))
    else:
        sys.exit(0 if selected(sys.argv[1], sys.argv[2]) else 1)
