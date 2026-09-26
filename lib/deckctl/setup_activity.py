"""Read-only whole-device activity; never presented as installer-only traffic."""
from pathlib import Path
import shutil
import time


def network_status(root=Path('/sys/class/net')):
    """Local carrier evidence only: a live link does not prove Internet access."""
    links = []
    try:
        for device in root.iterdir():
            if not (device/'device').exists(): continue
            try: links.append((device/'carrier').read_text().strip())
            except OSError: links.append(None)
    except OSError: pass
    status = 'LINK_UP' if '1' in links else 'OFFLINE' if links and all(value == '0' for value in links) else 'UNKNOWN'
    return {'status':status, 'checkedAt':time.time(), 'message':{
        'LINK_UP':'Link available · Internet access not checked',
        'OFFLINE':'Offline · no active physical network link',
        'UNKNOWN':'Network state unknown · link information unavailable'}[status]}


def storage_status(row):
    """Cheap local free-space evidence for the active item's existing allowance."""
    if not row: return None
    from . import setup_plan
    try: destination, allowance, label = setup_plan.storage_budget(row, False)
    except (KeyError, ValueError, TypeError):
        return {'path':'Destination unavailable', 'status':'UNKNOWN', 'freeBytes':None,
                'allowanceBytes':None, 'reserveBytes':setup_plan.GIB}
    try:
        anchor = destination.resolve()
        while not anchor.exists(): anchor = anchor.parent
        free = shutil.disk_usage(anchor).free
        return {'path':str(destination), 'freeBytes':free, 'allowanceBytes':allowance,
                'reserveBytes':setup_plan.GIB, 'estimateLabel':label,
                'status':'UNKNOWN' if allowance is None else 'INSUFFICIENT' if free < allowance+setup_plan.GIB else 'AVAILABLE'}
    except OSError:
        return {'path':str(destination), 'status':'UNKNOWN', 'freeBytes':None,
                'allowanceBytes':allowance, 'reserveBytes':setup_plan.GIB}


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
