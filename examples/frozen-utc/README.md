# Freeze repeated UTC reads

Set `tick=False` to keep successive reads at the exact destination:

```python
@time_machine.travel("2025-12-11T12:01:02Z", tick=False)
```

`travel()` defaults to `tick=True`. Its first clock read returns the destination exactly; subsequent reads include real elapsed time. This explains why the first exact assertion passes and the second fails when replacing freezegun's default frozen decorator. The [usage documentation](https://time-machine.readthedocs.io/en/latest/usage.html) describes this behavior.

[test_frozen_utc.py](test_frozen_utc.py) preserves the [original question's](https://github.com/adamchainz/time-machine/issues/705) explicit `Z` destination, `datetime.now(UTC)`, `NaiveMode.ERROR`, both exact assertions, and freezegun comparison. The only change is adding `tick=False` to the time-machine decorator.

## Run

Use Python 3.11 or newer in a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install 'time-machine[cli]==3.6.0' 'freezegun==1.5.5' 'pytest==9.2.0'
python -m pytest -q test_frozen_utc.py
python check.py
```

The direct pytest run reports `2 passed`. `check.py` runs that pair twice in separate processes, then checks a controlled negative: omitting `tick=False` and pausing between reads fails the second assertion while the freezegun comparison still passes. That pause belongs only to the negative control.

The check also gives the [official migration CLI](https://time-machine.readthedocs.io/en/latest/migration.html) a disposable copy of the original freezegun test. It verifies the rewritten native decorator has `tick=False`, preserves both assertions, and actually runs the migrated test. The CLI edits files in place and exits **1 when it rewrites a file**; its unchanged second run exits 0. It supports partial migrations, so inspect changes and run your tests when using it on your own files.

## Verified scope

On macOS arm64 / Python 3.12.4, the unmodified original failed its second time-machine assertion with versions **3.5.1 and 3.6.0**. Adding `tick=False` passed both tests on repeated runs in each version, using freezegun 1.5.5 and pytest 9.2.0. The migration and controlled negative checks also passed in both versions.

Python 3.14.9 from the original report was not tested. These are serial tests in fresh processes; time-machine changes the interpreter's shared clock functions. This example preserves exact frozen-time assertions and does not change the library's default behavior.

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
