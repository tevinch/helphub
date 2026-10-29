#!/usr/bin/env bash
# Disposable native Docker acceptance; run on a machine with Docker and Node.js.
set -euo pipefail
example_dir=$(cd "$(dirname "$0")/.." && pwd)
check_dir="$example_dir/verification"
export VERIFY_OUTPUT_DIR="${VERIFY_OUTPUT_DIR:-$example_dir/verification-results}"
mkdir -p "$VERIFY_OUTPUT_DIR"
VERIFY_OUTPUT_DIR=$(cd "$VERIFY_OUTPUT_DIR" && pwd)
export VERIFY_OUTPUT_DIR
work=$(mktemp -d)
source_dir="$work/mailflow"
commit=d1bfacfae0f9f858e1a3b7aa4c87545859804c2c
project="mailflow-locale-$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
export MAILFLOW_TEST_URL=http://127.0.0.1:18080
export MAILFLOW_TEST_PASSWORD
MAILFLOW_TEST_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_hex(24))')
builder_image="$project:builder"
raw_compose() {
  local variable
  local -a task_env=("PATH=$PATH")
  for variable in HOME DOCKER_CONFIG DOCKER_HOST DOCKER_CONTEXT DOCKER_TLS_VERIFY DOCKER_CERT_PATH XDG_RUNTIME_DIR; do
    if printenv "$variable" >/dev/null 2>&1; then
      task_env+=("$variable=${!variable}")
    fi
  done
  env -i "${task_env[@]}" docker compose --project-name "$project" --project-directory "$source_dir" \
    --env-file "$work/native.env" -f "$work/compose.yml" "$@"
}
compose() {
  raw_compose config --format json > "$work/compose-model.json"
  python3 "$check_dir/scope.py" --check "$work/compose-model.json" "$project" "$source_dir" "$VERIFY_OUTPUT_DIR/scope.json"
  raw_compose "$@"
}
cleanup() {
  status=$?
  if [[ $status -ne 0 && -f "$source_dir/docker-compose.yml" ]]; then
    compose logs --no-color --tail 80 > "$VERIFY_OUTPUT_DIR/native-failure.log" 2>&1 || true
  fi
  if [[ -f "$source_dir/docker-compose.yml" ]]; then
    compose down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
  docker image rm "$builder_image" >/dev/null 2>&1 || true
  rm -rf "$work"
  exit "$status"
}
trap cleanup EXIT
for command in docker node npm python3 curl; do
  command -v "$command" >/dev/null || { echo "Required command: $command" >&2; exit 1; }
done
docker info >/dev/null
python3 -m unittest discover -s "$example_dir/tests" -v
curl --fail --location --retry 2 --output "$work/source.tar.gz" "https://codeload.github.com/maathimself/mailflow/tar.gz/$commit"
mkdir "$source_dir"
tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$source_dir"
rm "$work/source.tar.gz"
mkdir -p "$source_dir/certs"
python3 - "$work/native.env" <<'PY'
from pathlib import Path
import secrets
import sys
Path(sys.argv[1]).write_text('\n'.join([
    'APP_URL=http://127.0.0.1:18080',
    'APP_HTTP_PORT=127.0.0.1:18080',
    'APP_PORT=127.0.0.1:18443',
    'NGINX_TLS=off',
    'SESSION_SECRET=' + secrets.token_hex(32),
    'DB_PASSWORD=' + secrets.token_hex(24),
    'ENCRYPTION_KEY=' + secrets.token_hex(32),
]) + '\n')
PY
python3 "$check_dir/scope.py" --isolate "$source_dir/docker-compose.yml" "$work/compose.yml"
(cd "$check_dir" && npm ci --ignore-scripts && npx playwright install --with-deps chromium)
expect_failure() {
  mode=$1
  expected=$2
  set +e
  node "$check_dir/browser.mjs" "$mode"
  status=$?
  set -e
  if [[ $status -ne $expected ]]; then
    echo "$mode: expected specific acceptance exit $expected, got $status" >&2
    return 1
  fi
}
rebuild_frontend() {
  compose build frontend
  compose up -d --no-deps --wait --wait-timeout 180 frontend
}
sha256sum "$source_dir/frontend/src/locales/en.json" > "$work/english.sha256"
# Baseline must reach working native English settings before failing on the missing option.
compose up -d --build --wait --wait-timeout 240 postgres redis backend frontend
expect_failure baseline 42
python3 "$check_dir/create-fixture.py" "$source_dir/frontend/src/locales/en.json" "$work/da.json"
python3 "$example_dir/prepare.py" "$source_dir" "$work/da.json"
sha256sum -c "$work/english.sha256"
rebuild_frontend
node "$check_dir/browser.mjs" green
# Independent omission: menu exists and da is saved, but the native loader is absent.
python3 - "$source_dir/frontend/src/i18n.js" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
line = "  da: () => import('./locales/da.json'),\n"
assert s.count(line) == 1
p.write_text(s.replace(line, '', 1))
PY
rebuild_frontend
expect_failure missing-loader 43
# Independent omission: loader exists but the native menu registration is absent.
python3 "$example_dir/prepare.py" "$source_dir" "$work/da.json"
python3 - "$source_dir/frontend/src/components/AdminPanel.jsx" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
line = "  { code: 'da', nativeName: 'Danish' },\n"
assert s.count(line) == 1
p.write_text(s.replace(line, '', 1))
PY
rebuild_frontend
expect_failure missing-menu 42
# Finish with the complete source and complete actual image, then check restart persistence.
python3 "$example_dir/prepare.py" "$source_dir" "$work/da.json"
sha256sum -c "$work/english.sha256"
rebuild_frontend
node "$check_dir/browser.mjs" green
compose restart frontend
compose up -d --no-deps --wait --wait-timeout 180 frontend
node "$check_dir/browser.mjs" resume
# Use the native builder's installed dependencies for the frontend's full test command.
docker build --target builder --tag "$builder_image" --file "$source_dir/frontend/Dockerfile" "$source_dir"
docker run --rm --network none "$builder_image" npm test > "$VERIFY_OUTPUT_DIR/native-frontend-tests.log" 2>&1
python3 - "$VERIFY_OUTPUT_DIR" "$commit" <<'PY'
from pathlib import Path
import hashlib
import json
import sys
p = Path(sys.argv[1])
expected = {'baseline': 'danish-selector-missing', 'missing-loader': 'danish-strings-not-loaded', 'missing-menu': 'danish-selector-missing'}
for mode, stage in expected.items():
    report = json.loads((p / f'{mode}.json').read_text())
    assert report['status'] == 'failed' and report['failureStage'] == stage
    assert 'native-language-settings-open' in report['checks']
for mode in ['green', 'resume']:
    report = json.loads((p / f'{mode}.json').read_text())
    assert report['status'] == 'passed'
summary = {'sourceCommit': sys.argv[2], 'version': '4.1.0', 'nativeDocker': True,
           'mode': 'software-operated Chromium with real local backend/database',
           'fixture': 'complete English test markers under da; not a Danish translation',
           'mailAccounts': 0,
           'evidenceSha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in p.glob('*.json') if f.name != 'summary.json'}}
(p / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print('Native locale build, both omission checks, switching, server persistence, restart, and frontend tests passed.')
PY
