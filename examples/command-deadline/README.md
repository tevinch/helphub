# Give a command a deadline while Gum shows its progress

Put GNU `timeout` **inside** `gum spin` when the command itself must stop after a time limit:

```sh
gum spin --timeout=0s --title "Working..." -- \
  timeout --kill-after=2s 30s ./your-command "argument with spaces"
```

Replace `./your-command` and its arguments with a non-interactive command you want to run. The `30s` limit belongs to that command. If it is still running after 30 seconds, `timeout` sends `TERM`; if it does not stop within two more seconds, it sends `KILL`.

`--timeout=0s` disables Gum's spinner deadline, including a deadline inherited through `GUM_SPIN_TIMEOUT`. Gum then waits for the supervised command to finish. This keeps the spinner's normal terminal behavior: command output is hidden. It does not introduce another command runner or require changing Gum.

In Gum **2.0.2**, [`gum spin --timeout`](https://github.com/charmbracelet/gum/blob/v2.0.2/spin/command.go) limits its UI context; the [wrapped command uses a separate background context](https://github.com/charmbracelet/gum/blob/v2.0.2/spin/spin.go). Ending that UI deadline does not impose a deadline on the wrapped job. GNU [`timeout`](https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html) provides the command supervision in the recipe above.

## Try it without running your own job

This example starts a five-second wait with a one-second deadline. The spinner should finish after about one second:

```sh
if gum spin --timeout=0s --title "Waiting..." -- \
    timeout --kill-after=1s 1s sleep 5; then
  printf 'Command completed\n'
else
  status=$?
  printf 'Command stopped; exit status: %s\n' "$status" >&2
fi
```

The expected exit status reported here is **124**. A command that finishes before its deadline retains its normal exit status, including a nonzero status such as `42`. The `if` form also lets a script inspect failures when `set -e` is enabled.

If escalation kills the `timeout` process, Gum 2.0.2 maps the signaled child status to **1**. Do not assume that every deadline ends with `124`, or that GNU timeout's direct `137` result will pass through Gum unchanged.

## Requirements and limits

- Install [Gum](https://github.com/charmbracelet/gum#installation) and GNU Coreutils. On Linux, the latter normally provides `timeout`. On macOS, `brew install gum coreutils` provides `gtimeout`; replace `timeout` with `gtimeout` in these commands.
- This recipe is for non-interactive jobs. GNU timeout's normal process-group behavior covers ordinary child processes. A job that deliberately detaches into a new process group or session can escape that group; this is not a process sandbox.
- Termination is not transactional: it does not undo files or other work the command has already written. Use a deadline only for jobs that can safely be interrupted.
- The timeout interval starts when `timeout` runs its command. Process startup, load and signal scheduling mean this is not a hard real-time deadline.
- No `--show-output` guarantee is made. In separate checks, Gum 2.0.2 sometimes dropped stdout or stderr from a fast command in a pseudo-terminal, even without GNU timeout. The recipe retains Gum's default hidden terminal output and does not repair that separate behavior.

## Verification

Run the included checks with Python 3 and the two installed commands:

```sh
python3 check.py
# macOS: check.py also discovers gtimeout
```

Paths can be supplied explicitly:

```sh
python3 check.py --gum /path/to/gum --timeout /path/to/timeout
```

On macOS arm64, the checks passed with Gum **2.0.2** and GNU Coreutils **9.12**. They run real commands in redirected and pseudo-terminal modes: repeated deadlines, proof that the job and its ordinary child both started, absence of late completion files, terminated process IDs, normal exit `0` / `42`, and a job that ignores `TERM` and requires escalation. An inherited `GUM_SPIN_TIMEOUT=50ms` is deliberately set during these checks to verify that `--timeout=0s` overrides it. The original spinner-only timeout fails the same job-termination check.

These are scripted native macOS checks. Linux and Windows were not run. The checks use only temporary local jobs and files; no recipient job or human manual validation is claimed.

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
