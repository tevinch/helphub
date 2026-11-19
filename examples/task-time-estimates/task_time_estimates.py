#!/usr/bin/env python3
"""Preview and conditionally fill missing Mindwtr task estimates."""
import re
from urllib.parse import urlsplit

PRESETS = ("5min", "10min", "15min", "30min", "1hr", "2hr", "3hr", "4hr", "4hr+")
STATUSES = ("inbox", "next", "waiting", "someday", "done", "archived")
FORMAT = "task-time-estimates/v1"
VERSION = re.compile(r"sha256-[0-9a-f]{64}\Z")


class ClientError(Exception):
    """Invalid input or an unsupported API response."""


def loopback_url(value):
    if not isinstance(value, str):
        raise ClientError("The Local API origin must be text.")
    try:
        parsed = urlsplit(value)
        port = parsed.port if parsed.port is not None else 80
        valid = (parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
                 and parsed.username is None and parsed.password is None
                 and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
                 and 1 <= port <= 65535)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ClientError("Use an http://127.0.0.1:PORT origin without a path or credentials.")
    return "http://127.0.0.1:" + str(port)


def task_map(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("tasks"), list):
        raise ClientError("The API did not return a task snapshot.")
    tasks = {}
    for task in snapshot["tasks"]:
        if (not isinstance(task, dict) or not isinstance(task.get("id"), str)
                or not task["id"] or task["id"] in tasks):
            raise ClientError("The task snapshot has an invalid or duplicate ID.")
        tasks[task["id"]] = task
    return tasks


def missing_estimate(task):
    return task.get("timeEstimate") is None


def eligible(task):
    return (task.get("status") in STATUSES and not task.get("deletedAt")
            and not task.get("purgedAt") and missing_estimate(task))


def validate_plan(plan):
    if (not isinstance(plan, dict) or set(plan) != {"format", "baseUrl", "estimate", "tasks"}
            or plan.get("format") != FORMAT or plan.get("estimate") not in PRESETS
            or not isinstance(plan.get("tasks"), list)):
        raise ClientError("Invalid estimate plan.")
    if loopback_url(plan["baseUrl"]) != plan["baseUrl"]:
        raise ClientError("The plan needs a canonical loopback origin.")
    seen = set()
    for task in plan["tasks"]:
        if (not isinstance(task, dict) or set(task) != {
                "id", "title", "status", "version", "priorEstimate", "estimateFieldPresent"}
                or not isinstance(task["id"], str) or not task["id"] or task["id"] in seen
                or not isinstance(task["title"], str) or task["status"] not in STATUSES
                or not isinstance(task["version"], str) or not VERSION.fullmatch(task["version"])
                or type(task["estimateFieldPresent"]) is not bool
                or task["priorEstimate"] is not None
                or (not task["estimateFieldPresent"] and task["priorEstimate"] is not None)):
            raise ClientError("Invalid or duplicate task in the estimate plan.")
        seen.add(task["id"])
    return plan


def make_plan(snapshot, base_url, estimate, *, statuses=(), contexts=(), tags=(),
              project=None, energy=None, ids=()):
    tasks = task_map(snapshot)
    versions = snapshot.get("versions")
    if not isinstance(versions, dict):
        raise ClientError("The API did not return task versions.")
    if any(status not in STATUSES for status in statuses):
        raise ClientError("Only estimate-bearing task statuses can be selected.")
    if set(ids) - tasks.keys():
        raise ClientError("A requested task ID is absent from this workspace snapshot.")
    selected = []
    for task in tasks.values():
        if not eligible(task):
            continue
        if ((statuses and task.get("status") not in statuses)
                or (ids and task["id"] not in ids)
                or (project is not None and task.get("projectId") != project)
                or (energy is not None and task.get("energyLevel") != energy)
                or (contexts and (not isinstance(task.get("contexts"), list)
                                  or any(value not in task["contexts"] for value in contexts)))
                or (tags and (not isinstance(task.get("tags"), list)
                              or any(value not in task["tags"] for value in tags)))):
            continue
        selected.append({
            "id": task["id"], "title": task.get("title"), "status": task["status"],
            "version": versions.get(task["id"]), "priorEstimate": task.get("timeEstimate"),
            "estimateFieldPresent": "timeEstimate" in task,
        })
    return validate_plan({"format": FORMAT, "baseUrl": loopback_url(base_url),
                          "estimate": estimate, "tasks": selected})


class HttpFailure(ClientError):
    def __init__(self, status):
        self.status = status
        super().__init__("Local API returned HTTP " + str(status) + ".")


class ConnectionFailure(ClientError):
    pass


class Api:
    def __init__(self, base_url, token):
        from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *_args, **_kwargs):
                return None

        self.base_url = loopback_url(base_url)
        if not token or any(ord(char) < 33 or ord(char) > 126 for char in token):
            raise ClientError("A valid Local API bearer token is required.")
        self.token = token
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, method, path, body=None, version=None):
        import json
        from http.client import HTTPException
        from urllib.error import HTTPError, URLError
        from urllib.request import Request

        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        if version is not None:
            headers["If-Match"] = '"' + version + '"'
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            status = error.code
            error.close()
            raise HttpFailure(status) from None
        except (URLError, OSError, HTTPException):
            raise ConnectionFailure("The Local API connection failed; no request was retried.") from None
        except (UnicodeError, ValueError):
            raise ClientError("The Local API returned invalid JSON.") from None
        if not isinstance(result, dict):
            raise ClientError("The Local API returned an unexpected response.")
        return result

    def check(self):
        health = self.request("GET", "/health")
        capabilities = health.get("capabilities", {})
        if (not isinstance(capabilities, dict)
                or capabilities.get("taskListVersions") is not True
                or capabilities.get("conditionalTaskPatch") is not True):
            raise ClientError("This server does not advertise protected task updates. No fallback was used.")


def apply_plan(plan, api):
    from urllib.parse import quote

    validate_plan(plan)
    api.check()
    current = task_map(api.request("GET", "/tasks?all=1"))
    result = {key: [] for key in ("applied", "conflicts", "skipped", "failed", "unconfirmed", "notAttempted")}
    for index, task in enumerate(plan["tasks"]):
        task_id = task["id"]
        now = current.get(task_id)
        if not now or not eligible(now) or now.get("status") != task["status"]:
            result["skipped"].append({"id": task_id, "reason": "no_longer_eligible"})
            continue
        encoded_id = quote(task_id, safe="")
        stop = False
        try:
            response = api.request("PATCH", "/v1/tasks/" + encoded_id,
                                   {"timeEstimate": plan["estimate"]}, task["version"])
        except HttpFailure as error:
            if error.status == 412:
                result["conflicts"].append(task_id)
                stop = True
            elif error.status >= 500:
                result["unconfirmed"].append(task_id)
                stop = True
            else:
                result["failed"].append({"id": task_id, "status": error.status})
                stop = True
        except ClientError:
            result["unconfirmed"].append(task_id)
            stop = True
        else:
            try:
                for observed in (response, api.request("GET", "/tasks/" + encoded_id)):
                    saved = observed.get("task")
                    version = observed.get("version")
                    if (not isinstance(saved, dict) or saved.get("id") != task_id
                            or saved.get("status") != task["status"]
                            or saved.get("timeEstimate") != plan["estimate"]
                            or not isinstance(version, str) or not VERSION.fullmatch(version)):
                        raise ClientError("The saved estimate could not be confirmed.")
            except ClientError:
                result["unconfirmed"].append(task_id)
                stop = True
            else:
                result["applied"].append(task_id)
        if stop:
            result["notAttempted"] = [row["id"] for row in plan["tasks"][index + 1:]]
            break
    return result


def main(argv=None):
    import argparse
    import getpass
    import json
    import os
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", type=Path, help="Save a new preview plan; never overwrite an existing file")
    mode.add_argument("--apply", type=Path, help="Apply exactly a previously reviewed plan")
    parser.add_argument("--url", help="Local API origin (default http://127.0.0.1:3456)")
    parser.add_argument("--estimate", choices=PRESETS, help="Preset to assign; required for preview")
    parser.add_argument("--status", action="append", choices=STATUSES, default=[])
    parser.add_argument("--context", action="append", default=[], help="Exact context, including @")
    parser.add_argument("--tag", action="append", default=[], help="Exact tag, including #")
    parser.add_argument("--project", help="Exact project ID")
    parser.add_argument("--energy", choices=("low", "medium", "high"))
    parser.add_argument("--id", action="append", default=[], help="Exact task ID")
    args = parser.parse_args(argv)
    try:
        if args.apply:
            if any((args.url, args.estimate, args.status, args.context, args.tag, args.project, args.energy, args.id)):
                raise ClientError("Apply uses the saved origin, estimate and task selection; omit preview options.")
            plan = validate_plan(json.loads(args.apply.read_text(encoding="utf-8")))
        else:
            if args.estimate is None:
                raise ClientError("Choose --estimate for a read-only preview.")
            base_url = loopback_url(args.url or "http://127.0.0.1:3456")
            if args.plan and args.plan.exists():
                raise ClientError("The plan file already exists; choose a new filename.")
        token = os.environ.get("MINDWTR_API_TOKEN")
        if not token:
            if not sys.stdin.isatty():
                raise ClientError("Set MINDWTR_API_TOKEN or run in a terminal to enter the token privately.")
            token = getpass.getpass("Local API token: ")
        api = Api(plan["baseUrl"] if args.apply else base_url, token)
        if args.apply:
            output = apply_plan(plan, api)
            code = int(any(output[key] for key in output if key != "applied"))
        else:
            api.check()
            plan = make_plan(api.request("GET", "/tasks?all=1"), api.base_url, args.estimate,
                             statuses=args.status, contexts=args.context, tags=args.tag,
                             project=args.project, energy=args.energy, ids=args.id)
            output = plan
            if args.plan:
                descriptor = os.open(args.plan, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                    json.dump(plan, file, indent=2, ensure_ascii=False)
                    file.write("\n")
            code = 0
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return code
    except (ClientError, OSError, ValueError) as error:
        message = str(error) if isinstance(error, ClientError) else "Cannot read or write the plan as valid JSON."
        print(json.dumps({"error": message}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
