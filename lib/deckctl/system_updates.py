"""On-demand read-only SteamOS and Decky Loader update availability."""
import configparser
import json
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from . import setup_plan, terminal

RELEASES = 'https://github.com/SteamDeckHomebrew/decky-loader/releases'
VALVE_HOST = 'steamdeck-atomupd.steamos.cloud'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Metadata redirects are not accepted')


def metadata(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in (VALVE_HOST, 'api.github.com') or parsed.username or parsed.password or parsed.port:
        raise ValueError('Unapproved metadata endpoint')
    req = urllib.request.Request(url, headers={'User-Agent':'deckctl-system-updates', 'Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=8) as response:
        payload = response.read(1024*1024+1)
        if len(payload) > 1024*1024: raise ValueError('Metadata exceeds size limit')
        data = json.loads(payload)
        if not isinstance(data, dict): raise ValueError('Invalid metadata object')
        return data


def local():
    values = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=',1); values[key] = value.strip('\"\'')
    prefs = configparser.ConfigParser(interpolation=None)
    prefs.read('/etc/steamos-atomupd/preferences.conf')
    branch = prefs.get('Choices','Branch',fallback=values.get('STEAMOS_DEFAULT_UPDATE_BRANCH','unknown'))
    loader = Path.home()/'homebrew/services/.loader.version'
    version = loader.read_text().strip() if loader.is_file() else 'unknown'
    if not re.fullmatch(r'v?\d+(?:\.\d+){1,3}(?:-[A-Za-z0-9.-]+)?',version): version = 'unknown'
    package = Path.home()/'.steam/steam/package'
    client_channel = (package/'beta').read_text().strip() if (package/'beta').is_file() else 'unknown'
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',client_channel): client_channel = 'unknown'
    return {'os':values.get('ID','unknown'), 'version':values.get('VERSION_ID','unknown'),
            'build':values.get('BUILD_ID','unknown'), 'channel':branch, 'deckyVersion':version,
            'clientChannel':client_channel}


def os_update(host):
    if host['os'] != 'steamos': return {'status':'UNAVAILABLE','label':'SteamOS updater unavailable on this system'}
    # Use Valve's installed path generator, not the CLI: even --query-only
    # requires root and can create runtime directories before its query.
    from steamosatomupd.image import Image
    prefs = configparser.ConfigParser(interpolation=None); prefs.read('/etc/steamos-atomupd/preferences.conf')
    config = configparser.ConfigParser(interpolation=None); config.read('/etc/steamos-atomupd/client.conf')
    origin = config.get('Server','MetaUrl').rstrip('/')
    parsed = urllib.parse.urlsplit(origin)
    if parsed.scheme != 'https' or parsed.netloc != VALVE_HOST or parsed.path != '/meta' or parsed.query or parsed.fragment:
        raise ValueError('Unsupported SteamOS metadata source')
    image = Image.from_dict(json.loads(Path('/etc/steamos-atomupd/manifest.json').read_text()))
    variant = prefs.get('Choices','Variant',fallback='steamdeck')
    try: data = metadata(origin+'/'+image.get_update_path(host['channel'],variant))
    except urllib.error.HTTPError as exc:
        if exc.code != 404: raise
        data = metadata(origin+'/'+image.get_update_path(host['channel'],variant,fallback=True))
    if not data: return {'status':'CURRENT','label':'Up to date on '+host['channel']}
    data = data.get('minor',data)
    if not isinstance(data,dict): raise ValueError('Invalid update path')
    candidates = data.get('candidates')
    if not isinstance(candidates,list) or not candidates or len(candidates)>20: raise ValueError('Invalid update candidates')
    target = candidates[0].get('image') if isinstance(candidates[0],dict) else None
    if not isinstance(target,dict) or target.get('product') != 'steamos' or target.get('arch') != image.arch or target.get('variant') != variant:
        raise ValueError('Unexpected update image')
    version, build = target.get('version'), target.get('buildid')
    if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?',version) or not isinstance(build,str) or not re.fullmatch(r'\d{8}(?:\.\d+)?',build):
        raise ValueError('Invalid offered version/build')
    if version == host['version'] and build == host['build']: return {'status':'CURRENT','label':'Up to date on '+host['channel']}
    newer = terminal.newer_version(version,host['version'])
    newer_build = tuple(map(int,build.split('.'))) > tuple(map(int,host['build'].split('.'))) if re.fullmatch(r'\d{8}(?:\.\d+)?',host['build']) else False
    status = 'UPDATE' if newer is True or newer is False and version == host['version'] and newer_build else 'DIFFERENT'
    return {'status':status,'label':('Update available: ' if status=='UPDATE' else 'Different build offered: ')+version,
            'version':version,'build':build,'channel':host['channel'],'steps':len(candidates)}


def report():
    host = local(); result = {'running':False,'system':host,'checkedAt':time.time()}
    try: result['steamOS'] = os_update(host)
    except (OSError,ValueError,ImportError,configparser.Error,AttributeError,KeyError) as exc:
        reason = {}; setup_plan.update_failure(reason,exc)
        result['steamOS'] = {'status':'UNKNOWN','label':'Couldn’t check SteamOS updates','note':reason['updateReason']}
    try:
        release = metadata('https://api.github.com/repos/SteamDeckHomebrew/decky-loader/releases/latest')
        latest = release.get('tag_name')
        if not isinstance(latest,str) or not re.fullmatch(r'v?\d+(?:\.\d+){1,3}',latest) or release.get('draft') is not False or release.get('prerelease') is not False:
            raise ValueError('Invalid stable Loader release')
        newer = terminal.newer_version(latest,host['deckyVersion'])
        result['decky'] = {'latestVersion':latest,'label':'Update available: '+latest if newer is True else 'Latest stable: '+latest,'source':RELEASES+'/tag/'+latest}
    except (OSError,ValueError) as exc:
        reason = {}; setup_plan.update_failure(reason,exc)
        result['decky'] = {'label':'Couldn’t check Decky releases','note':reason['updateReason'],'nextAction':reason['updateNextAction'],'source':RELEASES}
    return result


class Check:
    def __init__(self):
        self.guard = threading.Lock()
        self.result = {'running':True,'steamOS':{'label':'Checking SteamOS updates…'},'decky':{'label':'Checking Decky releases…'}}
        threading.Thread(target=self.work,daemon=True).start()

    def work(self):
        try: result = report()
        except Exception: result = {'running':False,'checkedAt':time.time(),'steamOS':{'label':'System check unavailable','note':'Local update information could not be read.'}}
        with self.guard: self.result = result

    def snapshot(self):
        with self.guard: return dict(self.result)
