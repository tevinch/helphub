import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1] / 'verification/scope.py'
spec = importlib.util.spec_from_file_location('compose_scope', FILE)
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


class ComposeScope(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name).resolve()
        self.project = 'mailflow-locale-123456789abc'
        self.model = {
            'name': self.project,
            'services': {
                'frontend': {'build': {'context': str(self.source)}, 'networks': {'mailflow': None},
                             'ports': [{'host_ip': '127.0.0.1', 'published': '18080', 'target': 80},
                                       {'host_ip': '127.0.0.1', 'published': '18443', 'target': 443}],
                             'volumes': [{'type': 'bind', 'source': str(self.source / 'certs'), 'target': '/etc/nginx/ssl'}]},
                'backend': {'build': {'context': str(self.source)}, 'networks': {'mailflow': None},
                            'environment': {'DB_HOST': 'postgres', 'DB_NAME': 'mailflow', 'DB_USER': 'mailflow', 'DB_PORT': '5432', 'REDIS_URL': 'redis://redis:6379'},
                            'volumes': [{'type': 'volume', 'source': 'image_cache', 'target': '/var/cache/mailflow/images'}]},
                'postgres': {'networks': {'mailflow': None}, 'volumes': [{'type': 'volume', 'source': 'postgres_data', 'target': '/var/lib/postgresql/data'}]},
                'redis': {'networks': {'mailflow': None}, 'volumes': [{'type': 'volume', 'source': 'redis_data', 'target': '/data'}]},
            },
            'volumes': {key: {'name': self.project + '_' + key} for key in ['image_cache', 'postgres_data', 'redis_data']},
            'networks': {'mailflow': {'name': self.project + '_mailflow'}},
        }

    def tearDown(self):
        self.temp.cleanup()

    def check(self, model=None):
        return scope.validate(self.model if model is None else model, self.project, self.source)

    def test_accepts_private_local_native_services(self):
        self.assertEqual(self.check()['project'], self.project)

    def test_rejects_public_port_before_any_lifecycle_command(self):
        self.model['services']['frontend']['ports'][0]['host_ip'] = '0.0.0.0'
        with self.assertRaises(ValueError):
            self.check()

    def test_rejects_shared_volume_even_under_unique_project(self):
        self.model['volumes']['postgres_data']['name'] = 'existing_database'
        with self.assertRaises(ValueError):
            self.check()

    def test_rejects_fixed_container_and_external_network(self):
        one = copy.deepcopy(self.model)
        one['services']['frontend']['container_name'] = 'mailflow-frontend'
        two = copy.deepcopy(self.model)
        two['networks']['mailflow']['external'] = True
        for model in [one, two]:
            with self.subTest(model=model):
                with self.assertRaises(ValueError):
                    self.check(model)

    def test_rejects_ambient_external_database_and_bind_mount(self):
        one = copy.deepcopy(self.model)
        one['services']['backend']['environment']['DB_HOST'] = 'outside.example.invalid'
        two = copy.deepcopy(self.model)
        two['services']['frontend']['volumes'][0]['source'] = '/existing/certificates'
        for model in [one, two]:
            with self.subTest(model=model):
                with self.assertRaises(ValueError):
                    self.check(model)

    def test_removes_only_five_native_container_names(self):
        text = '\n'.join(f'  {name}:\n    container_name: mailflow-{name}\n    keep: unchanged' for name in ['frontend', 'backend', 'postgres', 'redis', 'caddy']) + '\n'
        result = scope.isolate(text)
        self.assertEqual(result, ''.join(line for line in text.splitlines(keepends=True) if 'container_name:' not in line))
        with self.assertRaises(ValueError):
            scope.isolate(text.replace('mailflow-caddy', 'different-name'))


if __name__ == '__main__':
    unittest.main()
