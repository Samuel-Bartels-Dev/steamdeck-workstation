#!/usr/bin/env python3
"""Exercise native installer boundaries using fake vendor commands only."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lib'))
from deckctl import component_options, core


class ClaudeCode(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / '.local/bin'
        self.bin.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin) + ':' + os.environ['PATH'])

    def command(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/bash\nset -eu\n' + body)
        path.chmod(0o755)

    def run_installer(self):
        return subprocess.run(['bash', str(core.ROOT / 'modules/dev/install-claude.sh')],
                              env=self.env, capture_output=True, text=True)

    def test_existing_cli_updates_without_downloading_installer(self):
        self.command('claude', 'printf "%s\\n" "$*" >> "$HOME/calls"\n')
        self.command('curl', 'exit 99\n')
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / 'calls').read_text().splitlines(), ['--version', 'update', '--version'])
        self.assertFalse(list(self.home.glob('.claude-install.*')))

    def test_download_failure_cleans_temporary_files(self):
        self.command('curl', 'exit 42\n')
        result = self.run_installer()
        self.assertEqual(result.returncode, 42)
        self.assertFalse(list(self.home.glob('.claude-install.*')))
        self.assertFalse((self.bin / 'claude').exists())

    def test_successful_native_install_is_verified_and_script_removed(self):
        self.command('curl', '''while [[ "$1" != -o ]]; do shift; done
cat > "$2" <<'INSTALL'
#!/bin/bash
printf '#!/bin/sh\\necho "1.0.0 (Claude Code)"\\n' > "$HOME/.local/bin/claude"
chmod +x "$HOME/.local/bin/claude"
INSTALL
''')
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1.0.0 (Claude Code)', result.stdout)
        self.assertIn('Run: claude', result.stdout)
        self.assertFalse(list(self.home.glob('.claude-install.*')))

    def test_authentication_probe_is_read_only_and_reports_failure(self):
        self.command('claude', 'printf "%s\n" "$*" >> "$HOME/calls"\nexit 1\n')
        with patch.object(Path, 'home', return_value=self.home), patch.dict(os.environ, self.env):
            self.assertFalse(core._claude_logged_in())
        self.assertEqual((self.home / 'calls').read_text().splitlines(), ['auth status'])

    def test_low_space_stops_before_network_or_update(self):
        self.command('python3', 'exit 1\n')
        self.command('curl', 'touch "$HOME/network"\nexit 99\n')
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse((self.home / 'network').exists())

    def test_legacy_does_not_install_new_cli_and_explicit_selection_is_independent(self):
        with patch.object(core, 'CONFIG_HOME', self.home):
            self.assertNotIn('claude-code', component_options.selection()['dev'])
            core.save_json(self.home / 'components.json', {'dev': ['claude-code'], 'workspace': []})
            self.assertEqual(component_options.effective('dev'), {'claude-code'})
            self.assertEqual(component_options.effective('workspace'), set())


if __name__ == '__main__':
    unittest.main(verbosity=2)
