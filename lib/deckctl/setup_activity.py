"""Read-only whole-device activity; never presented as installer-only traffic."""
from pathlib import Path
import time


def counters(root=Path('/sys')):
    result = {}
    for category, directory, indices, multiplier in (
            ('network', root/'class/net', (0,), 1),
            ('disk', root/'block', (2,6), 512)):
        devices = {}
        try:
            for device in directory.iterdir():
                if not (device/'device').exists(): continue  # Exclude virtual devices and partitions.
                try:
                    raw = (device/'statistics/rx_bytes' if category == 'network' else device/'stat').read_text().split()
                    devices[device.name] = tuple(int(raw[i])*multiplier for i in indices)
                except (OSError, ValueError, IndexError): continue
        except OSError: pass
        result[category] = devices
    return result


class Sampler:
    def __init__(self): self.previous = None; self.history = []

    def sample(self):
        now = time.monotonic()
        if self.previous and now-self.previous[0] < .8: return self.history
        current = counters()
        rates = {'network':None,'read':None,'write':None}
        if self.previous:
            then, old = self.previous; elapsed = now-then
            for group, keys in (('network',('network',)), ('disk',('read','write'))):
                if not current[group] or current[group].keys() != old[group].keys(): continue
                for index,key in enumerate(keys):
                    deltas = [value[index]-old[group][name][index] for name,value in current[group].items()]
                    if all(value >= 0 for value in deltas): rates[key] = sum(deltas)/elapsed
        self.previous = (now,current)
        self.history = (self.history + [{'time':time.time(), **rates}])[-60:]
        return self.history
