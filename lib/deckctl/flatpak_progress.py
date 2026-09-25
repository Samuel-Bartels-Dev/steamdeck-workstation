"""Translate Flatpak's human progress into honest installer messages."""
import re
import time
from . import install_progress


class Reporter:
    def __init__(self):
        self.last_phase = None
        self.last_at = 0.0

    def __call__(self, text):
        text = ' '.join(text.split())
        if text.startswith('Looking for updates'):
            phase, message = 'Checking for updates', 'Already installed; checking for available updates.'
        elif text.startswith('Nothing to do'):
            phase, message = 'Up to date', 'Already up to date; no download needed.'
        elif text.startswith(('Updating', 'Installing')):
            phase = 'Updating' if text.startswith('Updating') else 'Installing'
            progress = re.search(r'(?<!\d)(\d{1,3})%\s*(.*)', text)
            message = phase + (' existing installation.' if phase == 'Updating' else ' selected application.')
            if progress and int(progress[1]) <= 100:
                # Percent is provider-reported progress, not invented byte totals.
                message = f'{phase}: {progress[1]}%'
                detail = progress[2].strip()
                if detail: message += ' · '+detail+' (Flatpak progress)'
        else:
            return
        now = time.monotonic()
        if phase == self.last_phase and now-self.last_at < 0.5: return
        self.last_at, self.last_phase = now, phase
        install_progress.report(phase, message)
