# Use an existing Python with PDM

If your CI image already provides Python, create the project virtual environment with that executable and tell PDM which interpreter to use. PDM's [interpreter selection guide](https://pdm-project.org/en/latest/usage/project/#choose-a-python-interpreter) documents `PDM_PYTHON` as the override for the saved interpreter path.

Use an absolute path to a virtualenv's Python that satisfies `[project].requires-python`. If the interpreter path is invalid or the version is incompatible, an ordinary PDM command can search for another interpreter. The launcher here checks the path and the version before starting PDM.

## Try the example

From this directory, set `LOCAL_PYTHON` to an existing Python 3.12 executable. Use fresh directories for the two environments. The first holds PDM and the second holds the example project.

```sh
LOCAL_PYTHON=/absolute/path/to/python3.12
"$LOCAL_PYTHON" -m venv .pdm-tools &&
  ./.pdm-tools/bin/python -m pip install "pdm==2.29.7" &&
  "$LOCAL_PYTHON" -m venv --without-pip .venv-local
```

```sh
./.pdm-tools/bin/python local-python.py ./.venv-local/bin/python install
./.pdm-tools/bin/python local-python.py ./.venv-local/bin/python sync
./.pdm-tools/bin/python local-python.py ./.venv-local/bin/python run python -c 'import sys; print(sys.executable)'
```

The first command creates `pdm.lock`. The last prints the absolute path ending in `.venv-local/bin/python`. On Windows, use the corresponding `Scripts\python.exe` paths. Run the launcher from the directory containing your project's `pyproject.toml`.

Try `./.pdm-tools/bin/python local-python.py ./missing/python install` to see the guard exit before it calls PDM. An existing environment running a version outside `requires-python` is also rejected.

## Where this applies

Run the launcher with the same Python where you installed PDM. It sets `PDM_PYTHON` to the checked path for that call and enables virtualenv use and saved-interpreter lookup for PDM. It leaves the original project interpreter selection available for other commands.

PDM 2.29.7 can still attempt an interpreter download when `pdm use --first 3.13` has no compatible local match, despite the wording in its help. The launcher covers the `install`, `sync`, and `run` calls shown here. PDM can still fetch project packages, and installing PDM itself normally contacts a package index.

Tested with PDM 2.29.7 and an existing CPython 3.12 virtualenv on macOS. With network access blocked in the PDM process, install and sync completed and two runs used the specified virtualenv. The missing, non-virtualenv, and incompatible interpreter checks exited before starting PDM.

## Optional coffee

If this example saved you some time, you're welcome to buy me a coffee. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
