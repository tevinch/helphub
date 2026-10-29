#!/usr/bin/env python3
"""Compile and run native Rust/JVM logging, including runtime omission controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

REVISION = '67e89c1b1e6ace5837da7d0a818ecde0c0660638'
ARTIFACTS = {
    'slf4j-api': '7e1446499b359675d8aabe6af2de86b85e72ae8a2a932c0b40d0e5ba57097439',
    'slf4j-simple': '8e701404786a4f87219d39d4853c86dfe4e86ae99376a39749df6c08e75022e0',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backend', type=Path, help='built upstream checkout at the pinned revision')
    parser.add_argument('--output', type=Path, default=Path('check-results'))
    args = parser.parse_args()
    backend = args.backend.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parent
    executable = backend / 'cargo-jvm/target/release' / ('cargo-jvm.exe' if os.name == 'nt' else 'cargo-jvm')
    assert executable.is_file(), 'first build the pinned backend with python3 build.py ci'
    java = os.environ.get('JAVA', 'java')
    actual_revision = subprocess.check_output(['git', '-C', str(backend), 'rev-parse', 'HEAD'], text=True).strip()
    assert actual_revision == REVISION, f'backend revision mismatch: {actual_revision}'
    report = {'backend_revision': actual_revision, 'checks': [], 'results': {}}
    env = os.environ.copy()
    env['CARGO_JVM_BACKEND_PATH'] = str(backend)

    def run(label, command, cwd):
        result = subprocess.run([str(p) for p in command], cwd=cwd, env=env, text=True, capture_output=True)
        (output / (label + '.log')).write_text(result.stdout + result.stderr, encoding='utf8')
        report['results'][label] = {'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        return result

    def class_name(jar):
        with zipfile.ZipFile(jar) as archive:
            manifest = archive.read('META-INF/MANIFEST.MF').decode('utf8')
        return next(line.split(':', 1)[1].strip() for line in manifest.splitlines() if line.startswith('Main-Class:'))

    try:
        with tempfile.TemporaryDirectory(prefix='jvm-logger-') as temporary:
            work = Path(temporary)
            project = work / 'project'
            shutil.copytree(source, project, ignore=shutil.ignore_patterns('target', '.venv', 'check-results', '__pycache__'))
            jars = work / 'jars'
            jars.mkdir()
            for name, expected in ARTIFACTS.items():
                url = f'https://repo.maven.apache.org/maven2/org/slf4j/{name}/2.0.20/{name}-2.0.20.jar'
                data = urllib.request.urlopen(url, timeout=60).read()
                assert hashlib.sha256(data).hexdigest() == expected, f'checksum mismatch: {name}'
                (jars / (name + '-2.0.20.jar')).write_bytes(data)
            api = jars / 'slf4j-api-2.0.20.jar'
            provider = jars / 'slf4j-simple-2.0.20.jar'

            def package(label, features=()):
                jar = work / (label + '.jar')
                command = [executable, 'package', '--bin', 'jvm_logger_demo', '--output', jar]
                if features:
                    command += ['--features', ','.join(features)]
                command += ['--locked']
                result = run(label + '-build', command, project)
                assert result.returncode == 0 and jar.is_file(), result.stderr
                return jar

            def launch(label, jar, libraries):
                cp = os.pathsep.join(str(path) for path in [jar, *libraries])
                return run(label, [java, '-Xss16m', '-cp', cp, class_name(jar)], project)

            # Original failure must be an actual compiled program's JVM error.
            wrong_constructor = package('wrong-constructor', ['wrong-constructor'])
            result = launch('wrong-constructor', wrong_constructor, [api, provider])
            assert result.returncode != 0
            assert 'NoSuchMethodError' in result.stderr and 'java.lang.String.<init>' in result.stderr
            assert 'LOGGING_DONE' not in result.stdout
            report['checks'].append('original String(Utf8View) constructor compiles then fails at JVM linkage')

            jar = package('normal')
            expected = ['local.example - Hello β 🌍', 'local.example - second message']
            for label in ['normal-first', 'normal-repeat']:
                result = launch(label, jar, [api, provider])
                assert result.returncode == 0, result.stderr
                assert 'JAVA_STRING_LENGTH=10' in result.stdout and 'LOGGING_DONE' in result.stdout
                assert all(message in result.stderr for message in expected), result.stderr
                assert 'SLF4J:' not in result.stderr, result.stderr
            report['checks'].append('real Rust-owned UTF-8 string converts to Java String and actual external Logger emits both messages twice')

            result = launch('missing-api', jar, [provider])
            assert result.returncode != 0 and 'NoClassDefFoundError' in result.stderr and 'org/slf4j/' in result.stderr
            report['checks'].append('omitted SLF4J API fails runtime class loading')

            result = launch('missing-provider', jar, [api])
            assert result.returncode == 0 and 'No SLF4J providers were found' in result.stderr
            assert not any(message in result.stderr for message in expected)
            assert 'LOGGING_DONE' in result.stdout
            report['checks'].append('omitted provider reaches NOP fallback but fails the required visible logging result')

            cp = os.pathsep.join(str(path) for path in [api, provider])
            result = run('jar-ignores-classpath', [java, '-Xss16m', '-cp', cp, '-jar', jar], project)
            assert result.returncode != 0 and 'NoClassDefFoundError' in result.stderr
            report['checks'].append('java -jar ignores an external -cp as documented')

            wrong_dispatch = package('wrong-dispatch', ['wrong-dispatch'])
            result = launch('wrong-dispatch', wrong_dispatch, [api, provider])
            assert result.returncode != 0 and 'IncompatibleClassChangeError' in result.stderr
            report['checks'].append('declaring Logger as a class fails actual interface dispatch')
            report['result'] = 'PASS'
    finally:
        (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
