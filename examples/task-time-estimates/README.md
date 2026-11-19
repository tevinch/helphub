# Fill missing task time estimates

Find Mindwtr tasks whose estimate is not set (absent or `null`), review a saved list, then assign a duration you choose. Existing estimates stay untouched, including custom or unrecognized values. Inbox, Next, Waiting, Someday, Done and Archived tasks are included. Reference notes are N/A and remain unchanged; deleted tasks are excluded.

This is a small desktop API client for the task cleanup discussed in [Mindwtr #1507](https://github.com/dongdongbh/Mindwtr/discussions/1507). It does not add a bulk field to Mindwtr's interface or provide a combined task/project/area organizer. It uses the [documented Local API](https://docs.mindwtr.app/power-users/local-api) in Mindwtr 1.3.9. Mobile apps do not expose this API.

## Setup

Use Mindwtr desktop 1.3.9 and Python 3. Download this folder; no additional Python packages are needed. The included checks run with Python 3.12.4.

In the desktop app:

1. Open **Settings → Advanced**, enable **Local API server**, and note its port and token. The default address is `http://127.0.0.1:3456`.
2. Keep that app and workspace open throughout preview and apply.

For display in the app, **Time Estimates** and task-editor layout settings control field visibility. Enable/show the field if you want to see it there. This client cannot inspect or change those UI settings; it confirms estimates through the API.

The Local REST API is a separate integration with write access when enabled; it does not inherit the separate MCP server's read-only setting. Use it only when you intend to allow this task update.

## Preview, review, apply

From this folder, choose a duration and save a plan:

```sh
python3 task_time_estimates.py --estimate 30min --plan task-estimates.plan.json
```

Enter the Local API token at the private prompt. For noninteractive use, the client also accepts the `MINDWTR_API_TOKEN` environment variable. It has no token command-line option and never saves the token in the plan or prints it.

The command only reads Mindwtr. It prints and saves the exact selected task IDs, titles, statuses, previous unset values and original versions, together with the chosen estimate and local address. Review the JSON file before applying it. Plan files contain task titles; keep them private. Existing plan files are never overwritten.

To narrow the list, add exact filters when creating the plan:

```sh
python3 task_time_estimates.py --estimate 1hr --context '@work' --tag '#review' --plan work.plan.json
python3 task_time_estimates.py --estimate 15min --status next --status waiting --plan active.plan.json
python3 task_time_estimates.py --estimate 30min --id TASK_ID --id ANOTHER_TASK_ID --plan selected.plan.json
```

`--project PROJECT_ID` and `--energy low|medium|high` are also available. Filters combine with AND; repeated statuses or IDs match any listed value, while repeated contexts/tags require every listed value. Include the `@` or `#` used in your stored context or tag. Project filters use IDs, not names. Use `--url http://127.0.0.1:PORT` when the app uses another port.

After reviewing the saved plan:

```sh
python3 task_time_estimates.py --apply task-estimates.plan.json
```

Apply uses only that plan's address, selected IDs, duration and original versions. It never adds newly matching tasks or changes selection options. Keep the original workspace open: the plan binds the address and task versions, not a universal workspace identity.

Each task receives a separate PATCH containing only `timeEstimate`. The client sends the original strong `If-Match` version and checks both the response and a fresh task read. A changed task can return a conflict; the client stops, lists earlier confirmed updates and marks later tasks as not attempted. It never refreshes a version to force an update or falls back to an unprotected request. The `/v1/` path alone does not enforce a version condition—the supplied header is essential.

Tasks that now have an estimate, changed status, became Reference, or were deleted are skipped. These state changes do not expand the saved batch. There is no multi-task transaction or automatic rollback. If a connection fails after a write, the result is **unconfirmed**; inspect the task in Mindwtr before preparing another plan.

To see what still needs an estimate, preview again without a plan filename:

```sh
python3 task_time_estimates.py --estimate 30min
```

Successfully updated tasks no longer appear. Use a new filename for any revised plan. Empty strings, whitespace and other existing malformed values are left untouched rather than repaired.

## Results and limits

Apply prints JSON lists named `applied`, `conflicts`, `skipped`, `failed`, `unconfirmed` and `notAttempted`. Exit status is `0` for a successful preview or fully confirmed batch, `1` for an incomplete batch, and `2` for invalid input or a failure before applying. A skipped record makes the batch incomplete; review the result instead of assuming every selected task changed.

The app retains its normal revision and lifecycle rules. An estimate update can advance `rev`, `revBy` and `updatedAt`, and native lifecycle normalization can adjust bookkeeping such as terminal Focus fields. The client sends no status, title, description, project, date, checklist or settings changes. It does not promise byte-for-byte preservation of arbitrary legacy metadata or change how estimates appear in individual app views.

Only a literal HTTP `127.0.0.1` origin is accepted. Redirects and environment proxies are disabled. The client requires the API's task-version and conditional-update capabilities; older or incompatible servers are rejected.

Run the included selection and HTTP contract checks:

```sh
python3 -m unittest discover -v
```

These checks use a local protocol fixture and do not require Mindwtr. They are separate from native app/storage verification.

The client was also checked against Mindwtr 1.3.9's native HTTP handling and file-backed SQLite storage in an isolated integration test. That check created synthetic tasks in all six statuses, applied the saved plan, reopened the database, and checked content/settings preservation, conflicts and operation-omission controls. It did not run the packaged desktop interface or a user workspace.

## License

The original client and tests are available under the [MIT License](LICENSE). Mindwtr has its own license.

## Optional coffee

The example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
