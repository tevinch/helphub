# Customize Listmonk’s confirmation email on YunoHost

The subscription confirmation email uses **`email-templates/subscriber-optin.html`** inside Listmonk’s static directory. It is a system template, separate from the campaign templates in the admin UI. The default is embedded in the binary, so there may be no installed HTML file to edit.

This example changes its wording while retaining the confirmation link, preference link, subscriber name and private-list handling. It uses the bundled header and footer. To change those too, override the matching version’s `email-templates/base.html`.

These instructions target **Listmonk 6.2.0**, currently packaged as `6.2.0~ynh1` by YunoHost. Check your installed version first. Version 7 is currently a beta with changed template translation keys; use templates matching your binary.

## Find the installation

Identify the application ID with `sudo yunohost app list`. It is usually `listmonk`; another installation may have an ID such as `listmonk__2`.

```sh
app_id=listmonk  # Replace with the actual application ID.
systemctl cat "$app_id.service"
systemctl show "$app_id.service" --property=WorkingDirectory --value
```

The current package starts the binary in that working directory and reads `config.toml` there. Use the displayed path as `install_dir`, then check the binary:

```sh
install_dir=/your/displayed/installation/path
sudo "$install_dir/listmonk" --version
```

Check the existing service and configuration for a `static-dir` setting, a `--static-dir` flag or `LISTMONK_static_dir` environment variable. If an override directory is already configured, edit its `email-templates/subscriber-optin.html` and keep the existing configuration.

## Add the override

For an installation without an existing override, choose a separate directory such as `/etc/listmonk-custom/listmonk/static`. The package’s upgrade script replaces the installation directory, keeping only `config.toml` and `uploads`; putting your custom template elsewhere avoids that deletion.

With this example’s files in your current directory:

```sh
custom_static="/etc/listmonk-custom/$app_id/static"
sudo install -d -m 0755 "$custom_static/email-templates"
```

Back up `config.toml` before editing it. Keep a separate copy of any existing custom template before replacing it. Then copy [subscriber-optin.html](subscriber-optin.html) into the new directory:

```sh
sudo install -m 0644 ./subscriber-optin.html \
  "$custom_static/email-templates/subscriber-optin.html"
```

Edit the text in that file to suit your newsletter. Keep `{{ define "subscriber-optin" }}`, the header/footer calls, `{{ .OptinURL }}`, `{{ .UnsubURL }}` and the public/private list condition. Ordinary template expressions preserve HTML escaping; keep subscriber values as expressions rather than inserting them as trusted HTML.

Add **one top-level line before the first `[app]` or other table header** in the existing `config.toml`:

```toml
static-dir = "/etc/listmonk-custom/listmonk/static"

[app]
# Keep your existing app and database settings below.
```

Use your actual `custom_static` path, including the correct application ID. This snippet shows placement; do not replace your complete configuration with it. Putting the setting inside `[app]` or `[db]` will not configure the override.

Make sure the service account can read the template and traverse its parent directories. Restart Listmonk to load the file:

```sh
sudo systemctl restart "$app_id.service"
sudo systemctl status "$app_id.service" --no-pager
sudo journalctl -u "$app_id.service" -n 30 --no-pager
```

The startup log should include `loading static files from:` followed by your directory. A template syntax error should be corrected before restarting again. To revert this new override, remove only the `static-dir` line you added and restart; retain your template and backups.

## Check the completed subscription

Use a test address you control and a public **double opt-in** list. Submit the subscription form and check that the received confirmation email contains your edited wording and the correct list. Follow its confirmation link and, if the confirmation page is enabled, submit that page’s confirmation button. Check that the subscriber’s list membership is now **confirmed**. Merely seeing the confirmation page does not complete the operation.

The native template/configuration flow was checked with the official Listmonk 6.2.0 macOS arm64 binary, PostgreSQL 18.6 and a local SMTP capture service. The checks received real MIME emails, completed confirmation through the native form, independently checked membership in the database, and repeated after a restart. They also checked escaped subscriber names, concealed private-list names, and unchanged campaign templates/settings. Omitting the override, customization, confirmation link or final confirmation caused the corresponding acceptance check to fail.

YunoHost’s package files were reviewed; an actual YunoHost service, upgrade or backup was not run. Keep a separate backup of the external template directory: the current package backup script does not include it. After an upgrade, compare your override with the matching upstream template, especially when changing major versions. A retained configuration file does not guarantee that an old template remains compatible.

## References and license

- [Official system template documentation](https://listmonk.app/docs/templating/#system-templates)
- [Listmonk 6.2.0 original confirmation template](https://github.com/knadh/listmonk/blob/v6.2.0/static/email-templates/subscriber-optin.html)
- [YunoHost package launcher](https://github.com/YunoHost-Apps/listmonk_ynh/blob/d5cd83460e7beb1074d43d366403e20943c9b256/conf/systemd.service), [upgrade](https://github.com/YunoHost-Apps/listmonk_ynh/blob/d5cd83460e7beb1074d43d366403e20943c9b256/scripts/upgrade) and [backup](https://github.com/YunoHost-Apps/listmonk_ynh/blob/d5cd83460e7beb1074d43d366403e20943c9b256/scripts/backup)

The example template is adapted from Listmonk 6.2.0 and distributed under the [GNU Affero General Public License v3](LICENSE), preserving its upstream license.

## Optional coffee

If this helped, you can optionally buy me a coffee. The example and guide are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
