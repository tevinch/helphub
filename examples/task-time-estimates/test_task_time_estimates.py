"""Client selection and protocol checks; native integration is tested separately."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from contextlib import contextmanager

try:
    import task_time_estimates as client
except ModuleNotFoundError:
    client = None

URL = "http://127.0.0.1:3456"
VERSION = "sha256-" + "a" * 64


def snapshot():
    rows = [
        {"id": status, "title": status.title(), "status": status,
         "contexts": ["@work"], "tags": ["#review"], "projectId": "p1", "energyLevel": "low"}
        for status in ("inbox", "next", "waiting", "someday", "done", "archived")
    ]
    rows += [
        {"id": "reference", "title": "Notes", "status": "reference"},
        {"id": "deleted", "title": "Trash", "status": "next", "deletedAt": "2026-11-01"},
        {"id": "estimated", "title": "Known", "status": "next", "timeEstimate": "15min"},
        {"id": "custom", "title": "Custom", "status": "next", "timeEstimate": "custom:42.5"},
        {"id": "unknown", "title": "Future value", "status": "next", "timeEstimate": "future:90"},
        {"id": "null", "title": "Null", "status": "next", "timeEstimate": None},
        {"id": "empty", "title": "Empty", "status": "next", "timeEstimate": ""},
    ]
    return {"tasks": rows, "versions": {row["id"]: VERSION for row in rows}}


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(client, "The client has not been implemented")

    def test_missing_estimates_include_finished_tasks_but_preserve_non_tasks_and_existing_values(self):
        data = snapshot()
        before = copy.deepcopy(data)
        plan = client.make_plan(data, URL, "30min")
        self.assertEqual([row["id"] for row in plan["tasks"]],
                         ["inbox", "next", "waiting", "someday", "done", "archived", "null"])
        self.assertEqual(data, before)
        self.assertEqual(plan["tasks"][0]["priorEstimate"], None)
        self.assertFalse(plan["tasks"][0]["estimateFieldPresent"])
        self.assertTrue(plan["tasks"][-1]["estimateFieldPresent"])
        self.assertEqual(plan["tasks"][-1]["priorEstimate"], None)

    def test_exact_filters_intersect_and_repeated_statuses_select_a_union(self):
        plan = client.make_plan(snapshot(), URL, "1hr", statuses=["done", "next"],
                                contexts=["@work"], tags=["#review"], project="p1", energy="low")
        self.assertEqual([row["id"] for row in plan["tasks"]], ["next", "done"])
        self.assertEqual(client.make_plan(snapshot(), URL, "1hr", contexts=["work"])["tasks"], [])
        self.assertEqual(client.make_plan(snapshot(), URL, "1hr", ids=["archived"])["tasks"][0]["id"], "archived")

    def test_context_and_tag_filters_do_not_match_null_or_scalar_token_fields(self):
        data = snapshot()
        data["tasks"] += [
            {"id": "no-context", "title": "No context", "status": "next", "contexts": None, "tags": ["#review"]},
            {"id": "scalar-tag", "title": "Invalid tag field", "status": "next", "contexts": ["@work"], "tags": "#review"},
        ]
        data["versions"].update({"no-context": VERSION, "scalar-tag": VERSION})
        plan = client.make_plan(data, URL, "30min", contexts=["@work"], tags=["#review"])
        self.assertEqual([row["id"] for row in plan["tasks"]],
                         ["inbox", "next", "waiting", "someday", "done", "archived"])

    def test_missing_versions_fail_instead_of_silently_dropping_an_eligible_task(self):
        data = snapshot()
        del data["versions"]["done"]
        with self.assertRaises(client.ClientError):
            client.make_plan(data, URL, "30min")

    def test_plan_validation_rejects_invalid_later_entries_before_any_apply(self):
        plan = client.make_plan(snapshot(), URL, "30min", ids=["inbox", "done"])
        for change in (lambda p: p["tasks"][1].update(version="*"),
                       lambda p: p["tasks"][1].update(status="reference"),
                       lambda p: p["tasks"].append(copy.deepcopy(p["tasks"][0])),
                       lambda p: p["tasks"][1].update(priorEstimate="15min"),
                       lambda p: p["tasks"][1].update(priorEstimate="", estimateFieldPresent=True),
                       lambda p: p.update(estimate="45min"),
                       lambda p: p.update(baseUrl="http://example.com:3456")):
            invalid = copy.deepcopy(plan)
            change(invalid)
            with self.assertRaises(client.ClientError):
                client.validate_plan(invalid)

    def test_only_literal_loopback_origin_is_accepted(self):
        for url in ("https://127.0.0.1:3456", "http://localhost:3456", "http://127.0.0.1:3456/x",
                    "http://user@127.0.0.1:3456", "http://127.0.0.1:3456?x=1", "http://127.0.0.1:3456#x",
                    "http://127.0.0.1:0", {"origin": URL}, 42):
            with self.subTest(url=url), self.assertRaises(client.ClientError):
                client.make_plan(snapshot(), url, "30min")


@contextmanager
def protocol_server(*, health=True, conflict=None, redirect=None, reject=None):
    """Protocol fixture, not a substitute for native storage integration."""
    state = {"snapshot": snapshot(), "requests": [], "patches": [], "conflict": conflict}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, body):
            encoded = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            if redirect:
                self.send_header("Location", redirect)
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            state["requests"].append(("GET", self.path))
            if redirect:
                return self.reply(302, {})
            if self.path == "/health":
                return self.reply(200, {"ok": True, "capabilities": {
                    "taskListVersions": health, "conditionalTaskPatch": health}})
            if self.path == "/tasks?all=1":
                return self.reply(200, state["snapshot"])
            if self.path.startswith("/tasks/"):
                task_id = self.path.split("/")[-1]
                task = next(task for task in state["snapshot"]["tasks"] if task["id"] == task_id)
                return self.reply(200, {"task": task, "version": VERSION})
            return self.reply(404, {})

        def do_PATCH(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            task_id = self.path.split("/")[-1]
            state["requests"].append(("PATCH", self.path))
            state["patches"].append((self.path, self.headers.get("If-Match"), body,
                                     self.headers.get("Authorization")))
            if reject:
                return self.reply(reject, {"error": "do not repeat the bearer token"})
            if task_id == state["conflict"]:
                return self.reply(412, {"code": "task_version_conflict"})
            task = next(task for task in state["snapshot"]["tasks"] if task["id"] == task_id)
            task.update(body)
            return self.reply(200, {"task": task, "version": VERSION})

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class CommandTests(unittest.TestCase):
    def invoke(self, *arguments, **extra_env):
        env = dict(os.environ, MINDWTR_API_TOKEN="test-private-token", **extra_env)
        return subprocess.run([sys.executable, str(Path(__file__).with_name("task_time_estimates.py")),
                               *map(str, arguments)], capture_output=True, text=True, env=env)

    def test_default_preview_saves_reviewed_ids_and_versions_without_writes(self):
        with protocol_server() as (url, state), tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            result = self.invoke("--url", url, "--estimate", "30min", "--plan", path, "--status", "done")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(path.exists(), "Preview must save a plan when requested")
            plan = json.loads(path.read_text())
            self.assertEqual([task["id"] for task in plan["tasks"]], ["done"])
            self.assertEqual(plan["tasks"][0]["version"], VERSION)
            self.assertEqual(plan["baseUrl"], url)
            self.assertEqual(state["requests"], [("GET", "/health"), ("GET", "/tasks?all=1")])
            self.assertNotIn("test-private-token", path.read_text() + result.stdout + result.stderr)

    def test_apply_uses_original_conditions_and_reports_partial_conflict_without_retry(self):
        with protocol_server(conflict="done") as (url, state), tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            original = client.make_plan(state["snapshot"], url, "30min", ids=["inbox", "done", "archived"])
            path.write_text(json.dumps(original))
            state["snapshot"]["versions"]["done"] = "sha256-" + "b" * 64
            result = self.invoke("--apply", path)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["applied"], ["inbox"])
            self.assertEqual(report["conflicts"], ["done"])
            self.assertEqual(report["notAttempted"], ["archived"])
            self.assertEqual(state["patches"], [
                ("/v1/tasks/inbox", '"' + VERSION + '"', {"timeEstimate": "30min"}, "Bearer test-private-token"),
                ("/v1/tasks/done", '"' + VERSION + '"', {"timeEstimate": "30min"}, "Bearer test-private-token"),
            ])
            self.assertIn(("GET", "/tasks/inbox"), state["requests"])
            self.assertNotIn("test-private-token", result.stdout + result.stderr)
            preview = self.invoke("--url", url, "--estimate", "30min", "--id", "inbox")
            self.assertEqual(json.loads(preview.stdout)["tasks"], [])

    def test_apply_rechecks_estimated_reference_and_deleted_tasks_without_replacing_the_plan(self):
        with protocol_server() as (url, state), tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            plan = client.make_plan(state["snapshot"], url, "30min", ids=["inbox", "next", "done"])
            path.write_text(json.dumps(plan))
            state["snapshot"]["tasks"][0]["timeEstimate"] = "2hr"
            state["snapshot"]["tasks"][1]["status"] = "reference"
            state["snapshot"]["tasks"][4]["deletedAt"] = "2026-11-19"
            result = self.invoke("--apply", path)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)["applied"], [])
            self.assertEqual(len(json.loads(result.stdout)["skipped"]), 3)
            self.assertEqual(state["patches"], [])
            self.assertEqual(json.loads(path.read_text()), plan)

    def test_invalid_plan_is_rejected_before_any_network_or_partial_write(self):
        with protocol_server() as (url, state), tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            plan = client.make_plan(state["snapshot"], url, "30min", ids=["inbox", "done"])
            plan["tasks"][1]["version"] = "*"
            path.write_text(json.dumps(plan))
            result = self.invoke("--apply", path)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(state["requests"], [])

    def test_legacy_capability_response_never_writes_or_falls_back(self):
        with protocol_server(health=False) as (url, state), tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(client.make_plan(state["snapshot"], url, "30min")))
            result = self.invoke("--apply", path)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(state["requests"], [("GET", "/health")])

    def test_redirect_is_not_followed_and_environment_proxy_is_ignored(self):
        with protocol_server() as (target, received), protocol_server(redirect=target) as (url, origin):
            result = self.invoke("--url", url, "--estimate", "30min", HTTP_PROXY=target,
                                 http_proxy=target, NO_PROXY="", no_proxy="")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(origin["requests"], [("GET", "/health")])
            self.assertEqual(received["requests"], [])

    def test_permission_failure_stops_later_writes_and_reports_not_attempted(self):
        with protocol_server(reject=403) as (url, state), tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(client.make_plan(state["snapshot"], url, "30min", ids=["inbox", "done"])))
            result = self.invoke("--apply", path)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["failed"], [{"id": "inbox", "status": 403}])
            self.assertEqual(report["notAttempted"], ["done"])
            self.assertEqual(len(state["patches"]), 1)


if __name__ == "__main__":
    unittest.main()
