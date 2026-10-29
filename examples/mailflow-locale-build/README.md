# Add a language to a MailFlow source build

A JSON file alone does not make a new language available in MailFlow. In **v4.1.0**, the frontend also needs a lazy-loader entry and an entry in its language menu. This example registers your Danish translation as `da` and keeps English as the fallback.

Target: [MailFlow v4.1.0](https://github.com/maathimself/mailflow/releases/tag/v4.1.0), source commit `d1bfacfae0f9f858e1a3b7aa4c87545859804c2c`. This is consumer build guidance, not a change submitted to MailFlow.

## Use your translation

Start with the `frontend/src/locales/en.json` from the version you are building. Keep its JSON keys and `{{placeholders}}`, and translate its values. Save your file outside the checkout, for example as `/path/to/da.json`.

From this example directory, run:

```sh
python3 prepare.py /path/to/mailflow /path/to/da.json --check
python3 prepare.py /path/to/mailflow /path/to/da.json
```

The helper validates every key and placeholder, copies your file to `frontend/src/locales/da.json`, and adds these two native registrations:

- `frontend/src/i18n.js`: a `da` import in `LOCALES`.
- `frontend/src/components/AdminPanel.jsx`: a `da` choice labelled **Danish** in `LANGUAGES`.

It preserves `en.json`, refuses to overwrite a different existing `da.json`, and can be run again with the same file. It stops if the expected registration layout differs. Review the resulting three-file diff before rebuilding; keep your translation and changes when updating MailFlow.

## Put it in your own container

For an **existing source-build installation**, keep its current configuration and data. From that MailFlow checkout, rebuild and replace only its frontend service:

```sh
docker compose build frontend
docker compose up -d --no-deps frontend
```

The native Dockerfile builds the frontend and copies the resulting `dist` into its nginx image. The existing backend, PostgreSQL and Redis services keep running. Editing a file on the host does not change an already built image; pulling a prebuilt image also does not include your local translation.

For a new installation, follow MailFlow's [build-from-source setup](https://github.com/maathimself/mailflow/tree/v4.1.0#option-b--build-from-source), with the three locale changes in place before its build command. This guide does not replace its environment or server setup.

Open **Settings → Appearance → Language & Font → Danish**. Check a translated label, reload, then switch English → Danish again. A browser preferring `da-DK` can also choose `da` on a first visit. A saved account language takes precedence after sign-in.

To offer the translation for future official releases, follow MailFlow's [contribution guide](https://github.com/maathimself/mailflow/blob/main/CONTRIBUTING.md). Building your own image does not submit the translation upstream.

## Reproduce the checks

```sh
python3 -m unittest discover -s tests -v
bash verification/verify.sh
```

The second command needs Linux, Docker Compose, Python 3 and Node.js 20 or later. Run it in a disposable development or CI environment: it creates the native local app and removes its test containers and volumes on exit. It does not publish an image or connect a mail account. Its temporary Compose copy removes only fixed container names, uses a unique project and builder tag, clears ambient Compose/application overrides, and validates localhost ports and project-owned resources before each Compose command.

The checks use the exact pinned source, real frontend/backend/PostgreSQL/Redis images and Chromium. They cover the missing-language baseline, separate omitted-loader/menu controls, native selection, locale chunk HTTP loading, English/Danish switching, server preference persistence after clearing browser storage, container restart, and the frontend's native test command. JSON reports and screenshots go to `verification-results/`.

The generated `da` fixture is a complete set of **English test markers**, not a Danish translation. It checks locale integration; your translated file and language quality remain yours to review. Desktop/mobile packages, mail-provider setup and the original requester's application are outside these checks. MailFlow's source and images retain their upstream licenses; this repository contains only the helper, guide and checks.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
