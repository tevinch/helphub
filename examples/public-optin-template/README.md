# Customize Listmonk’s public confirmation page

Reuse the **same `static-dir`** that already contains your custom confirmation email. Add `public/templates/optin.html` beneath that root; no additional configuration key is needed.

```text
your-existing-static-root/
├── email-templates/
│   └── subscriber-optin.html  ← keep your working email template
└── public/
    └── templates/
        └── optin.html        ← add this page template
```

For example, if your existing setting is:

```toml
static-dir = "/etc/listmonk-custom/listmonk/static"
```

the new file belongs at `/etc/listmonk-custom/listmonk/static/public/templates/optin.html`. Keep that setting and all other configuration unchanged. The root is the directory containing `email-templates` and `public`; `public/optin.html` is not the template’s path.

This example targets **Listmonk 6.2.0**, currently packaged by YunoHost as `6.2.0~ynh1`. Check your installed version before copying it. Version 7 is currently a beta with changed template translation keys; use the original template matching your binary when adapting another version.

## Add the page override

Find the effective static directory in your existing configuration, service flags or `LISTMONK_static_dir` environment setting. If you already customized the email successfully, use that same directory. Back up any existing `public/templates/optin.html` before replacing it, and retain your other custom files.

With this example’s files in your current directory, substitute your actual existing root:

```sh
custom_static=/etc/listmonk-custom/listmonk/static
sudo install -d -m 0755 "$custom_static/public/templates"
sudo install -m 0644 ./optin.html "$custom_static/public/templates/optin.html"
```

[optin.html](optin.html) changes only the heading and explanatory sentence. Edit those two English strings to suit your newsletter; they replace the corresponding translated strings. Keep `{{ define "optin" }}`, the header/footer calls, the public/private list condition, the list UUID inputs, `method="post"` and the hidden `confirm=true` input. Keep list values as ordinary template expressions so HTML escaping and private-list handling remain intact. Files you do not override continue to use the bundled defaults.

Listmonk loads templates at startup, so restart after editing. On YunoHost, identify the application ID with `sudo yunohost app list`; use that actual ID below, including a suffix such as `__2` if present:

```sh
app_id=listmonk
sudo systemctl restart "$app_id.service"
sudo systemctl status "$app_id.service" --no-pager
sudo journalctl -u "$app_id.service" -n 30 --no-pager
```

Check for `loading static files from:` followed by your existing root. If a template syntax error prevents startup, restore the backed-up file and restart.

## Check the completed confirmation

`optin.html` is the page opened from a confirmation-email link. The initial signup page uses `subscription-form.html` instead.

With the confirmation page enabled, submit the public form for a double opt-in list using a test address you control. Check that your custom email still appears, follow its confirmation link, verify the new page wording and submit the confirmation button. Then check that the subscriber’s membership in the intended list is **confirmed**. Repeat with another test subscriber after a restart. Existing unrelated memberships should retain their prior statuses.

If `app.show_optin_page` is false, Listmonk confirms directly when the email link is opened, so this intermediate page will not appear. Preserve that setting unless you intentionally want to change the subscription flow; the template override does not enable it.

Scripted native checks used Listmonk 6.2.0 on macOS arm64, PostgreSQL 18.6 and a loopback SMTP capture with no relay. They captured the real MIME email, opened its confirmation URL, submitted the native form and independently checked database membership, including private-list concealment, escaped list names and a repeat after restart. The existing custom email, CSS, settings, configuration and campaign templates remained unchanged. A separate disabled-page baseline and override both confirmed directly with that setting preserved. Wrong-path, unchanged-copy, missing-confirm-field and skipped-final-POST controls failed the corresponding acceptance checks.

These were native HTTP checks, not visual browser checks. YunoHost package files were reviewed; an actual YunoHost service, upgrade or backup was not run.

## Rollback and upgrades

Restore your previous `optin.html`, or remove only the new `public/templates/optin.html` to return to the bundled page, then restart. **Keep the existing `static-dir` setting**: removing it would also disable your working email override.

Keep a separate backup of your external static directory. The current YunoHost upgrade replaces installation files except configuration and uploads, and its backup script does not include an external custom directory. After upgrades, compare your override with the matching upstream template before retaining it.

## Source and license

- [Official system-template documentation](https://listmonk.app/docs/templating/#system-templates)
- [Listmonk 6.2.0 original public opt-in template](https://github.com/knadh/listmonk/blob/v6.2.0/static/public/templates/optin.html)
- [YunoHost package service](https://github.com/YunoHost-Apps/listmonk_ynh/blob/d5cd83460e7beb1074d43d366403e20943c9b256/conf/systemd.service), [upgrade](https://github.com/YunoHost-Apps/listmonk_ynh/blob/d5cd83460e7beb1074d43d366403e20943c9b256/scripts/upgrade) and [backup](https://github.com/YunoHost-Apps/listmonk_ynh/blob/d5cd83460e7beb1074d43d366403e20943c9b256/scripts/backup)

This example is licensed under the [GNU Affero General Public License v3](LICENSE). The template is adapted from Listmonk 6.2.0 by the Listmonk contributors. Modified by Tevinch on 2026-11-03: the heading and explanatory sentence were changed; the template’s behavior remains unchanged.

## Optional coffee

If this helped, you can optionally buy me a coffee. The example and guide are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
