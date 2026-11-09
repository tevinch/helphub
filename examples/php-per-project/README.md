# A PHP version for each nginx project

Run one `php-cgi.exe` process per PHP version, give each a different loopback port, and point each project's nginx virtual host at the corresponding port. Both projects can then run at the same time.

This guide uses an existing Laragon installation with nginx and two PHP folders. It uses PHP 8.4 and 8.5, both supported branches as checked on 2026-11-09. Download the current patch releases for your projects from [PHP's official Windows downloads](https://www.php.net/downloads.php?os=windows). Choose **x64 Non Thread Safe (NTS)** for FastCGI and extract each version to its own directory under `C:\laragon\bin\php`. The official builds require the matching Microsoft Visual C++ runtime, which an existing working Laragon installation may already have.

## Start the two backends

The folder names below match the official archives available when this guide was checked. Substitute your actual folders. Each must have its own `php.ini`; if a newly extracted version has no file yet, copy that version's `php.ini-development` to `php.ini` once. Keep existing settings and use extensions built for that PHP version.

Open one PowerShell window for PHP 8.4:

```powershell
Set-Location 'C:\laragon\bin\php\php-8.4.27-1-nts-Win32-vs17-x64'
& .\php-cgi.exe -c .\php.ini -b 127.0.0.1:9084
```

Open another PowerShell window for PHP 8.5:

```powershell
Set-Location 'C:\laragon\bin\php\php-8.5.12-1-nts-Win32-vs17-x64'
& .\php-cgi.exe -c .\php.ini -b 127.0.0.1:9085
```

Keep both windows open. An otherwise quiet window is normal: these processes are serving FastCGI requests. Press **Ctrl+C in the corresponding window** to stop that backend. If a port is already occupied, choose another unused loopback port and use the same number in the project's configuration below.

The explicit `-c` selects each version's configuration. If you have set `PHP_INI_SCAN_DIR`, that environment variable also controls additional INI files; ensure those files are appropriate for the version being started.

## Set each project's upstream

Laragon generates per-project nginx files under:

```text
C:\laragon\etc\nginx\sites-enabled\
```

For a generated file such as `auto.project84.test.conf`, remove the `auto.` prefix so Laragon preserves your changes. If a custom `project84.test.conf` already exists, edit it instead. Keep a backup outside `sites-enabled`.

In **project84.test.conf**, find the existing PHP location and change just its upstream line:

```nginx
fastcgi_pass 127.0.0.1:9084;
```

In **project85.test.conf**, use:

```nginx
fastcgi_pass 127.0.0.1:9085;
```

Replace the existing `fastcgi_pass php_upstream;` line rather than adding a second `fastcgi_pass`. Keep the site's existing `root`, FastCGI include, rewrites, access controls and other settings. Apply the mapping to each relevant HTTP/HTTPS PHP handler if the project has separate handlers. Keep Laragon's shared `php_upstream.conf` for other projects that use its selected default version.

Use Laragon's **Reload** control to reload nginx after editing. These commands start terminal-owned CGI processes; check that both are still running after stopping or restarting services. Laragon's PHP version menu and a terminal's `php` command may select a different default than these explicit web backends.

## Verify through nginx

Temporarily add a new PHP file, for example `runtime-version-check.php`, to each project's public document root:

```php
<?php
header('Content-Type: application/json');
echo json_encode([
    'version' => PHP_VERSION,
    'sapi' => PHP_SAPI,
    'ini' => php_ini_loaded_file(),
]);
```

Open the file through each project's existing nginx URL. One response must report `8.4.x`, the other `8.5.x`, both with `cgi-fcgi` and their respective INI paths. Refresh both without switching Laragon's PHP version. Then use the normal pages in both projects and remove the temporary check files.

An HTTP **502** normally means that nginx cannot reach the selected backend; check its terminal and port. If both projects report the same version, check their actual PHP handler's `fastcgi_pass`. The CGI ports use the FastCGI protocol, so open the nginx project URL in the browser, not port 9084 or 9085 directly.

## Native integration check

The included `verify.ps1` requires PowerShell 7 on Windows and extracted official PHP/nginx binaries. It creates disposable projects and configurations; supply paths to the binary directories:

```powershell
pwsh -File .\verify.ps1 `
    -Php84 'C:\tools\php84' `
    -Php85 'C:\tools\php85' `
    -Nginx 'C:\tools\nginx-1.31.8'
```

It uses real Windows `php-cgi.exe` processes and nginx HTTP requests to check concurrent versions, separate INI settings, preserved project content, an edit and reload, missing-file rejection, and independent backend failure/recovery. It keeps `cgi.force_redirect=1` and uses nginx's supplied FastCGI parameters. Ports 9084, 9085, 18084 and 18085 must be free. It stops only its own processes and prints the temporary evidence-directory path.

`ci.ps1` downloads the pinned PHP 8.4.27-1/8.5.12-1 NTS x64 and nginx 1.31.8 archives from their official hosts, checks their recorded SHA-256 hashes, and invokes the same check on a Windows runner. PHP hashes were obtained from the official release index; the nginx hash records the downloaded official archive. nginx's Windows guide recommends the mainline build; its Windows implementation is documented as beta.

This check validates the PHP/nginx configuration independently. Laragon's GUI and service lifecycle are not exercised by it. Use the documented Laragon file locations and verify the actual project URLs as described above.

References: [original usage question](https://github.com/leokhoa/laragon/issues/1625), [Laragon per-project configuration persistence](https://laragon.org/docs/pretty-urls), [Laragon multi-version folders](https://laragon.org/docs/multi-version), [PHP CGI command options](https://www.php.net/manual/en/features.commandline.options.php), [PHP Windows build types](https://www.php.net/manual/en/install.windows.manual.php), [nginx FastCGI upstream](https://nginx.org/en/docs/http/ngx_http_fastcgi_module.html#fastcgi_pass), [nginx on Windows](https://nginx.org/en/docs/windows.html).

## Optional coffee

This guide and check are free to use. If they save you time, buying me a coffee is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
