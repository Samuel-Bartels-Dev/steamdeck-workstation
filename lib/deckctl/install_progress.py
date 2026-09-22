"""Scoped progress events from providers; no polling thread or background service."""
from contextlib import contextmanager
from contextvars import ContextVar

_listener = ContextVar('install_progress', default=None)


@contextmanager
def listen(callback):
    token = _listener.set(callback)
    try: yield
    finally: _listener.reset(token)


def report(phase, message, downloaded=None, total=None):
    callback = _listener.get()
    if callback:
        callback(phase, message, downloaded, total)
