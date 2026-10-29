#!/usr/bin/env python3
"""Keep disposable verification resources inside one unique Compose project."""
import argparse
import json
from pathlib import Path
import re

ACTIVE = {'frontend', 'backend', 'postgres', 'redis'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def isolate(text):
    pattern = r'^[ \t]+container_name:[ \t]+mailflow-(frontend|backend|postgres|redis|caddy)[ \t]*\n'
    names = re.findall(pattern, text, re.MULTILINE)
    require(len(names) == 5 and set(names) == ACTIVE | {'caddy'},
            'expected exactly five native fixed container names')
    result = re.sub(pattern, '', text, flags=re.MULTILINE)
    require(not re.search(r'^\s*container_name:', result, re.MULTILINE),
            'unrecognized container name remains')
    return result


def validate(model, project, source):
    source = Path(source).resolve()
    require(re.fullmatch(r'mailflow-locale-[a-f0-9]{12}', project) is not None,
            'expected a unique verification project name')
    require(model.get('name') == project, 'rendered project name differs')
    services = model.get('services', {})
    require(ACTIVE <= set(services) <= ACTIVE | {'caddy'}, 'unexpected service set')
    if 'caddy' in services:
        require(services['caddy'].get('profiles') == ['https'], 'Caddy must remain an inactive optional profile')
    for service in services.values():
        require('container_name' not in service, 'fixed container name is not permitted')
        require('network_mode' not in service, 'unexpected network mode')
    for kind in ['volumes', 'networks']:
        for name, resource in model.get(kind, {}).items():
            require(not resource.get('external'), f'external {kind} are not permitted')
            require(resource.get('name') == f'{project}_{name}', f'{kind} must belong to this project')
    require('mailflow' in model.get('networks', {}), 'native project network is missing')
    expected_volumes = {
        'frontend': {('bind', str(source / 'certs'), '/etc/nginx/ssl')},
        'backend': {('volume', 'image_cache', '/var/cache/mailflow/images')},
        'postgres': {('volume', 'postgres_data', '/var/lib/postgresql/data')},
        'redis': {('volume', 'redis_data', '/data')},
    }
    for name in ACTIVE:
        service = services[name]
        require(set(service.get('networks', {})) == {'mailflow'}, 'unexpected service network')
        volumes = {(entry.get('type'), entry.get('source'), entry.get('target'))
                   for entry in service.get('volumes', [])}
        require(volumes == expected_volumes[name], 'unexpected service volume or bind mount')
        for kind, volume, _ in volumes:
            if kind == 'volume':
                require(volume in model.get('volumes', {}), 'named test volume is missing')
        if name != 'frontend':
            require(not service.get('ports'), 'only frontend may publish a port')
        if name in {'frontend', 'backend'}:
            require(service.get('build', {}).get('context') == str(source), 'build context is outside the private source')
    ports = services['frontend'].get('ports', [])
    require(len(ports) == 2, 'expected only the two native frontend ports')
    require({(entry.get('target'), str(entry.get('published'))) for entry in ports}
            == {(80, '18080'), (443, '18443')}, 'unexpected frontend port mapping')
    require(all(entry.get('host_ip') == '127.0.0.1' for entry in ports), 'frontend ports must bind to localhost')
    env = services['backend'].get('environment', {})
    expected = {'DB_HOST': 'postgres', 'DB_NAME': 'mailflow', 'DB_USER': 'mailflow',
                'DB_PORT': '5432', 'REDIS_URL': 'redis://redis:6379'}
    require(all(str(env.get(key)) == value for key, value in expected.items()),
            'backend must use the private native database and cache')
    return {'project': project, 'activeServices': sorted(ACTIVE), 'publishedHost': '127.0.0.1',
            'volumes': sorted(resource['name'] for resource in model.get('volumes', {}).values()),
            'networks': sorted(resource['name'] for resource in model.get('networks', {}).values()),
            'fixedContainerNamesRemoved': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--isolate', nargs=2, metavar=('NATIVE', 'COPY'))
    modes.add_argument('--check', nargs=4, metavar=('RENDERED', 'PROJECT', 'SOURCE', 'REPORT'))
    args = parser.parse_args()
    try:
        if args.isolate:
            native, target = map(Path, args.isolate)
            target.write_text(isolate(native.read_bytes().decode('utf8')), encoding='utf8')
        else:
            rendered, project, source, report = args.check
            summary = validate(json.loads(Path(rendered).read_text()), project, Path(source))
            Path(report).write_text(json.dumps(summary, indent=2) + '\n')
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
