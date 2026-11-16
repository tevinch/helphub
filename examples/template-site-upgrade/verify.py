#!/usr/bin/env python3
"""Acceptance checks for the synthetic site, not a validator for arbitrary sites."""
import hashlib
import json
from pathlib import Path
import re
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root):
    site = root / "site"
    before = json.loads((root / "preserved.json").read_text())
    for name, digest in before.items():
        assert sha(site / name) == digest, f"Site-owned file changed: {name}"
    config = json.loads((site / "_config.yml").read_text())
    previous_config = json.loads((root / "configuration-before.json").read_text())
    for key, value in previous_config.items():
        if key != "plugins":
            assert config[key] == value, f"Existing configuration changed: {key}"
    assert config["plugins"] == previous_config["plugins"] + ["al_rtl"]
    assert config["url"] == "https://example.org" and config["baseurl"] == "/notes"
    for key in ["search_enabled", "enable_math", "enable_cookie_consent", "enable_darkmode"]:
        assert config[key] is False, f"Explicit disabled setting lost: {key}"
    assert config["repo_trophies"]["enabled"] is False
    assert config["protect_email"] is False
    assert config.get("apple_touch_icon") == "site-icon.png", "Starter config change omitted"
    assert "al_rtl" in config["plugins"], "New plugin activation omitted"
    versions = json.loads((root / "target-versions.json").read_text())
    assert versions["al_folio_core"] == "1.0.15", "Target core was not loaded"
    assert versions["al_cookie"] == "1.0.1", "Target cookie was not loaded"
    assert versions["al_rtl"] == "1.0.0"
    baseline = json.loads((site / ".starter-source.json").read_text())
    assert baseline.get("known_source") == {"tag": "v1.1", "commit": "e4342b9c748f33d038faff4363329e5aa1f714e4"}, "Known source evidence missing or changed"
    assert baseline["reviewed_target"]["tag"] == "v1.2"
    assert baseline["reviewed_target"]["commit"] == "b95d6d61a1b0663529094b1b5f4fbe8aa41f8a04"
    assert baseline["decisions"][".github/workflows/deploy.yml"] == "Keep site customization; review manually"
    assert baseline["deferred"], "Do not claim the complete target starter was installed"
    commands = json.loads((root / "commands.json").read_text())
    names = {x["name"] for x in commands if x["exit"] == 0 or (x["name"] in {"old-overrides-diff", "target-overrides-diff"} and x["exit"] == 1)}
    required = {"plain-update", "old-versions", "old-audit", "old-overrides-audit",
                "old-overrides-diff", "old-overrides-accept", "target-install",
                "target-versions", "target-audit", "target-overrides-audit",
                "target-overrides-diff", "target-overrides-accept", "target-overrides-clean",
                "target-report", "target-build"}
    assert required <= names, f"Missing native operations: {sorted(required - names)}"
    ack = (site / ".al-folio-overrides.yml").read_text()
    assert "_layouts/page.liquid" in ack and "1.0.15" in ack
    report = (site / "al-folio-upgrade-report.md").read_text()
    assert "Blocking" in report
    home = (site / "_site/index.html").read_text()
    guide = (site / "_site/guide/index.html").read_text()
    rtl = (site / "_site/direction/index.html").read_text()
    assert "{{version}}" not in home, "Third-party URL processing did not run"
    assert "Site-owned layout" in home and "Research notes" in home
    assert "Existing guide content" in guide and "Sample dataset" in guide
    assert 'href="/notes/guide/' in home and 'src="/notes/assets/img/site-icon.png"' in guide
    assert re.search(r'<html[^>]*dir="rtl"', rtl), "New plugin is not executing"
    assert 'rel="apple-touch-icon" href="/notes/assets/img/site-icon.png' in home
    assert "al_cookie/js/" not in home and "ninja-keys" not in home
    for asset in ["assets/css/tailwind.css", "assets/css/main.css", "assets/img/site-icon.png"]:
        assert (site / "_site" / asset).is_file(), f"Built asset missing: {asset}"
    assert not (site / "_site/blog").exists(), "Upstream demo content copied into site"
    print("PASS: installed versions, native operations, source decisions and customized built site")


if __name__ == "__main__":
    check(Path(sys.argv[1]).resolve())
