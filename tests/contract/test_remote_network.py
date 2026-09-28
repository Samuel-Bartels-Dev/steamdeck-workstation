#!/usr/bin/env python3
"""Remote streaming diagnostics must report the measured route truthfully."""
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lib'))
from deckctl import network


class RemoteNetworkTests(unittest.TestCase):
    def test_route_parsing_and_preset(self):
        output = '\n'.join([
            'pong from desktop (100.1.2.3) via DERP(fra) in 95ms',
            'pong from desktop (100.1.2.3) via 198.51.100.1:41641 in 24ms',
            'pong from desktop (100.1.2.3) via 198.51.100.1:41641 in 25ms',
            'pong from desktop (100.1.2.3) via 198.51.100.1:41641 in 24ms',
            'pong from desktop (100.1.2.3) via 198.51.100.1:41641 in 26ms',
        ])
        self.assertEqual(network._tailscale_samples(output)[-1], (26.0, 'direct'))

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *_): return False

        stdout = io.StringIO()
        with patch.object(network.shutil, 'which', return_value='/opt/tailscale/tailscale'), \
             patch.object(network, '_run', return_value=(0, output)), \
             patch.object(network.socket, 'create_connection', return_value=Connection()), \
             contextlib.redirect_stdout(stdout):
            self.assertEqual(network.remote_test({'target': 'desktop'}), 0)
        self.assertIn('DIRECT | replies 5/5', stdout.getvalue())
        self.assertIn('720p60 at 8 Mbps', stdout.getvalue())  # High spread.

    def test_missing_replies_does_not_claim_bandwidth(self):
        stdout = io.StringIO()
        with patch.object(network.shutil, 'which', return_value=None), \
             patch.object(network.socket, 'create_connection', side_effect=OSError('offline')), \
             contextlib.redirect_stdout(stdout):
            self.assertEqual(network.remote_test({'target': 'desktop'}), 1)
        self.assertIn('Preset: unavailable', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
