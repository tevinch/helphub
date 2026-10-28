# Keep a fixed Stanza model snapshot

A Stanza package version and a model tag identify different things. If you need to rerun an experiment with exactly the same model files, retain the model bytes and the matching `resources.json`, rather than relying on a tag staying unchanged. This example addresses the [model-versioning question](https://github.com/stanfordnlp/stanza/issues/1710) with existing Stanza parameters.

The native configuration is:

```python
stanza.download(
    "en", model_dir="models", package=None,
    processors={"tokenize": "ewt_nocharlm", "mwt": "ewt"},
    resources_version="1.15.0",
    resources_url="https://raw.githubusercontent.com/stanfordnlp/stanza-resources/e11a9e67718a00f3256b065879d5bbadfc000647",
    model_url="https://huggingface.co/stanfordnlp/stanza-en/resolve/810dca30ddb25c30582c019dbaeb3a3e040fb958/models/{filename}",
)
```

Both URLs use complete immutable commit IDs. The resources commit pins package selection and expected model MD5s; the separate Hugging Face commit pins the model files. Stanza normally adds the matching MWT processor for the English EWT tokenizer. Both small models are explicit here.

## Prepare and run

Use Python 3.12 and a CPU-capable PyTorch installation. Install into a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python snapshot.py prepare models
.venv/bin/python snapshot.py verify models
.venv/bin/python snapshot.py run models --text "A small test. Another sentence!"
.venv/bin/python check.py models
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. PyTorch is a substantial dependency; use its [official installation instructions](https://pytorch.org/get-started/locally/) for your platform if you need a CPU-specific wheel.

`prepare` requires a new destination under an existing parent directory. It downloads into a temporary directory, checks the returned processor list, verifies all three files against the fixed SHA256/size manifest in `snapshot.json`, checks each model against the downloaded resources MD5, and then places the verified directory at the destination. An already existing destination is refused.

The three assets total 1,666,245 bytes: `resources.json`, the English EWT tokenizer without CharLM, and its MWT model. Their model SHA256 values come from the [immutable model repository's LFS metadata](https://huggingface.co/api/models/stanfordnlp/stanza-en/revision/810dca30ddb25c30582c019dbaeb3a3e040fb958?blobs=true). The resources hash was checked against the [pinned resources file](https://raw.githubusercontent.com/stanfordnlp/stanza-resources/e11a9e67718a00f3256b065879d5bbadfc000647/resources_1.15.0.json).

`run` verifies the files before constructing a real CPU pipeline with:

```python
stanza.Pipeline(
    "en", dir="models", package=None,
    processors={"tokenize": "ewt_nocharlm", "mwt": "ewt"},
    download_method=None, use_gpu=False,
)
```

The sample result is:

```json
[["A", "small", "test", "."], ["Another", "sentence", "!"]]
```

The official [offline FAQ](https://stanfordnlp.github.io/stanza/faq.html#stanza-is-trying-to-download-models-andor-its-resources-file-when-offline-how-can-i-stop-that) documents `download_method=None`. `reuse_resources` still permits model downloads. These download parameters are implemented in [Stanza 1.15.0's resource utilities](https://github.com/stanfordnlp/stanza/blob/v1.15.0/stanza/resources/common.py); local pipeline options are described in the [pipeline guide](https://stanfordnlp.github.io/stanza/pipeline.html).

## Verify what you retain

`check.py` runs real inference twice while blocking socket `connect` and `connect_ex`, independently probes that both restrictions work, and checks the expected tokens and unchanged file bytes. It also checks the independent resources MD5s, missing and same-size modified assets, refusal before pipeline construction, and preservation of an existing destination. The checks were run with Python 3.12.4, Stanza 1.15.0, PyTorch 2.12.0, NumPy 2.3.4 and huggingface-hub 2.3.0. These are scripted checks; original-user adoption is unknown.

Retain this trusted `snapshot.json` with the three assets. A checksum manifest detects differences against that retained copy; it is not an authenticity guarantee if someone can replace both the files and the manifest. Do not load models from untrusted sources.

This is a fixed English tokenizer/MWT example, not the project's official model-versioning policy. It does not pin every processor in an arbitrary pipeline or guarantee identical predictions across hardware and software environments. For a larger experiment, retain every selected model and dependent model (including embeddings, CharLM or transformer assets), matching resources, pipeline options, inputs, full dependency lock, Python/PyTorch versions and relevant platform settings. `requirements.txt` pins the four principal packages used here, not the complete transitive environment. Save the resolved environment as well, for example with `python -m pip freeze > environment.txt`.

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It's entirely optional; the example remains free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
