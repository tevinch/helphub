#!/usr/bin/env python3
"""Create an isolated local repository and receiver for trying a push option."""
import json
import os
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 setup_demo.py NEW_DIRECTORY")
root = Path(sys.argv[1]).expanduser().resolve()
if root.exists():
    raise SystemExit("Choose a new directory; existing paths are never changed.")
root.mkdir(parents=True)
repository, receiver = root / "work", root / "receiver.git"
env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

def git(*args, cwd=root):
    return subprocess.check_output(["git", *args], cwd=cwd, env=env, text=True, stderr=subprocess.STDOUT).strip()

git("init", "--bare", str(receiver))
git("init", "-b", "main", str(repository))
git("config", "user.name", "Tevinch", cwd=repository)
git("config", "user.email", "tevin.chang@live.com", cwd=repository)
git("config", "commit.gpgSign", "false", cwd=repository)
git("config", "core.hooksPath", os.devnull, cwd=repository)
git("config", "push.default", "simple", cwd=repository)
git("config", "receive.advertisePushOptions", "true", cwd=receiver)
git("remote", "add", "origin", str(receiver), cwd=repository)
(repository / "note.txt").write_text("Initial content.\n")
(repository / "kept.txt").write_text("Keep this existing content unchanged.\n")
git("add", ".", cwd=repository)
git("commit", "-m", "Initial example", cwd=repository)
git("push", "-u", "origin", "main", cwd=repository)
git("branch", "kept", cwd=repository)
git("push", "origin", "kept", cwd=repository)
hook = receiver / "hooks" / "post-receive"
hook.write_text("""#!/bin/sh
{
  printf 'count=%s\\n' "${GIT_PUSH_OPTION_COUNT:-unset}"
  printf 'option0=%s\\n' "${GIT_PUSH_OPTION_0:-}"
  cat
} >> push-receipts.txt
""")
hook.chmod(0o755)
(repository / "note.txt").write_text("A change to push from Lazygit.\n")
git("add", "note.txt", cwd=repository)
git("commit", "-m", "Update example content", cwd=repository)
metadata = {
    "repository": str(repository),
    "receiver": str(receiver),
    "expectedCommit": git("rev-parse", "HEAD", cwd=repository),
    "previousCommit": git("rev-parse", "origin/main", cwd=repository),
    "keptCommit": git("rev-parse", "kept", cwd=repository)
}
(root / "demo.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2))
