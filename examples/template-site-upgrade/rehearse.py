#!/usr/bin/env python3
"""A fixed, disposable v1.1 -> v1.2 al-folio example. Never point it at your site."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import urllib.request
import zlib

RELEASES = {
    "v1.1": "e4342b9c748f33d038faff4363329e5aa1f714e4",
    "v1.2": "b95d6d61a1b0663529094b1b5f4fbe8aa41f8a04",
}
FILES = ["Gemfile", "_config.yml", ".github/workflows/deploy.yml",
         ".github/workflows/unit-tests.yml", "LICENSE"]
GEMS = ["al_folio_core", "al_cookie", "al_folio_upgrade", "al_icons"]
commands = []


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def dump(path, value):
    write(path, json.dumps(value, indent=2) + "\n")


def run(root, name, args, cwd=None, exits=(0,)):
    result = subprocess.run(args, cwd=cwd or root / "site", env=environment(root),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    write(root / "logs" / (name + ".log"), result.stdout)
    commands.append({"name": name, "args": args, "exit": result.returncode})
    dump(root / "commands.json", commands)
    if result.returncode not in exits:
        raise RuntimeError(f"{name} failed ({result.returncode}); see {root / 'logs' / (name + '.log')}")
    print(name + ": " + str(result.returncode), flush=True)
    return result.stdout


def environment(root):
    env = os.environ.copy()
    env.setdefault("BUNDLE_PATH", str(root / "gems"))
    env["JEKYLL_ENV"] = "production"
    return env


def bundle(root, name, *args, exits=(0,)):
    return run(root, name, ["bundle", *args], exits=exits)


def config_from(root, tag):
    # Official released YAML, parsed by Ruby's safe loader. JSON is also valid YAML.
    return json.loads(run(root, "read-config-" + tag,
        ["ruby", "-ryaml", "-rjson", "-rdate", "-e",
         "puts JSON.generate(YAML.safe_load_file(ARGV[0], permitted_classes: [Date], aliases: true))",
         str(root / "releases" / tag / "_config.yml")], cwd=root))


def pins(text):
    found = dict(re.findall(r"gem ['\"](al_\w+)['\"], ['\"]= ([^'\"]+)['\"]", text))
    assert all(n in found for n in GEMS), "Released pins could not be read"
    return found


def gemfile(values, rtl=False):
    result = 'source "https://rubygems.org"\ngem "jekyll", "= 4.4.1"\ngem "jekyll-socials", "= 0.0.7"\ngem "jekyll-3rd-party-libraries", "= 0.0.1"\ngem "jekyll-cache-bust", "= 0.0.1"\n'
    for name in GEMS + (["al_rtl"] if rtl else []):
        result += f'gem "{name}", "= {values[name]}"\n'
    return result


def versions(root, name):
    code = 'require "json"; puts JSON.generate(%w[al_folio_core al_cookie al_folio_upgrade al_icons al_rtl].filter_map { |n| s=Gem.loaded_specs[n]; [n,s.version.to_s] if s }.to_h)'
    value = json.loads(bundle(root, name, "exec", "ruby", "-e", code))
    dump(root / (name + ".json"), value)
    return value


def png():
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    pixels = (b"\x00" + b"\x25\x63\x87" * 180) * 180
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 180, 180, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def prepare(root):
    for tag, commit in RELEASES.items():
        for path in FILES:
            dest = root / "releases" / tag / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(f"https://raw.githubusercontent.com/alshedivat/al-folio/{commit}/{path}", timeout=30) as response:
                dest.write_bytes(response.read())
    dump(root / "release-snapshots.json", {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / "releases").rglob("*") if p.is_file()
    })
    site = root / "site"
    site.mkdir()
    old = root / "releases/v1.1"
    write(site / "Gemfile", gemfile(pins((old / "Gemfile").read_text())))
    config = config_from(root, "v1.1")
    config.update(title="Research notes", first_name="Research", last_name="Notes",
                  url="https://example.org", baseurl="/notes", icon="",
                  search_enabled=False, enable_math=False, enable_darkmode=False,
                  enable_cookie_consent=False, related_blog_posts={"enabled": False},
                  plugins=["jekyll-3rd-party-libraries", "jekyll-socials", "jekyll-cache-bust"] + GEMS, include=["_pages"],
                  exclude=["Gemfile", "Gemfile.lock", "vendor", "al-folio-upgrade-report.md"])
    config["repo_trophies"]["enabled"] = False
    config["al_folio"]["compat"]["bootstrap"]["enabled"] = False
    config["al_folio"]["features"]["cv"]["enabled"] = False
    config["al_folio"]["features"]["distill"]["enabled"] = False
    dump(site / "_config.yml", config)
    dump(root / "configuration-before.json", config)
    write(site / "index.md", """---
layout: page
title: Research notes
---
Our existing notes remain here.

[Read the guide]({{ '/guide/' | relative_url }})
""")
    write(site / "_pages/guide.md", """---
layout: page
title: Existing guide
permalink: /guide/
---
Existing guide content

{{ site.data.notes.title }}

![Site icon]({{ '/assets/img/site-icon.png' | relative_url }})
""")
    write(site / "_pages/direction.md", """---
layout: page
title: Direction example
permalink: /direction/
lang: ar
---
The direction example uses the released optional plugin.
""")
    write(site / "_layouts/page.liquid", """---
layout: default
---
<aside data-site-layout="custom">Site-owned layout</aside>
<h1>{{ page.title }}</h1>
<article>{{ content }}</article>
""")
    dump(site / "_data/notes.json", {"title": "Sample dataset"})
    write(site / "_bibliography/papers.bib", "@book{notes, title={Site-owned references}, author={Example}, year={2026}}\n")
    image = site / "assets/img/site-icon.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(png())
    # Site-local jobs are fixtures only. Nothing is sent to GitHub or executed as CI.
    deploy = (old / ".github/workflows/deploy.yml").read_text().replace(
        "runs-on: ubuntu-latest", "runs-on: ubuntu-24.04\n    timeout-minutes: 12")
    write(site / ".github/workflows/deploy.yml", deploy)
    write(site / ".github/workflows/site-check.yml", "name: Site check\non: workflow_dispatch\njobs:\n  check:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo site-owned-check\n")
    write(site / ".gitignore", "_site/\n.jekyll-cache/\n.bundle/\n")
    dump(site / ".starter-source.json", {"known_source": {"tag": "v1.1", "commit": RELEASES["v1.1"]}})
    run(root, "git-init", ["git", "init", "-b", "example"])
    run(root, "git-add", ["git", "add", "--", "."])
    run(root, "git-initial", ["git", "-c", "user.name=Tevinch", "-c",
                            "user.email=tevin.chang@live.com", "commit", "-m", "Create synthetic notes site"])
    # The synthetic site starts with its own history and has no remote.
    owned = ["index.md", "_pages/guide.md", "_pages/direction.md",
             "_layouts/page.liquid", "_data/notes.json", "_bibliography/papers.bib",
             "assets/img/site-icon.png", ".github/workflows/deploy.yml",
             ".github/workflows/site-check.yml"]
    dump(root / "preserved.json", {n: hashlib.sha256((site / n).read_bytes()).hexdigest() for n in owned})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new disposable directory; must not exist")
    options = parser.parse_args()
    root = options.output.resolve()
    if root.exists():
        parser.error("output already exists; choose a new empty location")
    if shutil.disk_usage(root.parent).free < 2 * 1024**3:
        parser.error("at least 2 GiB free is required before installing dependencies")
    root.mkdir(parents=True)
    prepare(root)
    site = root / "site"
    bundle(root, "old-install", "install", "--jobs", "2")
    bundle(root, "plain-update", "update")
    old = versions(root, "old-versions")
    assert old["al_folio_core"] == "1.0.12" and old["al_cookie"] == "1.0.0", "The original negative changed"
    # This assertion is deliberately expected to fail before the source/pin update.
    try:
        assert old["al_folio_core"] == "1.0.15", "Plain bundle update leaves the exact old pin"
    except AssertionError as error:
        write(root / "expected-old-pin-failure.txt", str(error) + "\n")
    else:
        raise AssertionError("Missing old-pin negative control")
    bundle(root, "old-audit", "exec", "al-folio", "upgrade", "audit")
    bundle(root, "old-overrides-audit", "exec", "al-folio", "upgrade", "overrides", "audit")
    bundle(root, "old-overrides-diff", "exec", "al-folio", "upgrade", "overrides", "diff", "_layouts/page.liquid", exits=(1,))
    # The only override is intentionally ours; the diff is saved for review.
    bundle(root, "old-overrides-accept", "exec", "al-folio", "upgrade", "overrides", "accept", "_layouts/page.liquid")
    for path in FILES[:-1]:
        run(root, "starter-diff-" + path.replace("/", "_"),
            ["git", "diff", "--no-index", "--", str(root / "releases/v1.1" / path),
             str(root / "releases/v1.2" / path)], cwd=root, exits=(0, 1))
    new_pins = pins((root / "releases/v1.2/Gemfile").read_text())
    write(site / "Gemfile", gemfile(new_pins, rtl=True))
    config = json.loads((site / "_config.yml").read_text())
    config["apple_touch_icon"] = "site-icon.png"
    config["protect_email"] = False
    config["plugins"].append("al_rtl")
    dump(site / "_config.yml", config)
    dump(site / ".starter-source.json", {
        "known_source": {"tag": "v1.1", "commit": RELEASES["v1.1"]},
        "reviewed_target": {"tag": "v1.2", "commit": RELEASES["v1.2"]},
        "decisions": {
            "Gemfile": "Update selected released pins; opt into al_rtl; retain minimal site dependencies",
            "_config.yml": "Add apple_touch_icon, protect_email and al_rtl; retain site values",
            ".github/workflows/deploy.yml": "Keep site customization; review manually",
            ".github/workflows/unit-tests.yml": "Skip upstream demo tests",
        },
        "deferred": ["Unselected optional gems", "Upstream demo content/assets", "Upstream demo and maintenance workflows"],
    })
    bundle(root, "target-install", "install", "--jobs", "2")
    target = versions(root, "target-versions")
    assert target["al_folio_core"] == "1.0.15" and target["al_cookie"] == "1.0.1"
    bundle(root, "target-audit", "exec", "al-folio", "upgrade", "audit")
    bundle(root, "target-overrides-audit", "exec", "al-folio", "upgrade", "overrides", "audit")
    bundle(root, "target-overrides-diff", "exec", "al-folio", "upgrade", "overrides", "diff", "_layouts/page.liquid", exits=(1,))
    # page.liquid is unchanged between these two core releases. Our intentional
    # replacement is reviewed again; do not generalize this into accepting all files.
    bundle(root, "target-overrides-accept", "exec", "al-folio", "upgrade", "overrides", "accept", "_layouts/page.liquid")
    bundle(root, "target-overrides-clean", "exec", "al-folio", "upgrade", "overrides", "audit", "--fail-on-stale")
    bundle(root, "target-report", "exec", "al-folio", "upgrade", "report")
    bundle(root, "target-build", "exec", "jekyll", "build", "--trace")
    from verify import check
    check(root)
    print(f"Built example: {site / '_site'}")
    print(f"Commands and review diffs: {root / 'logs'}")


if __name__ == "__main__":
    main()
