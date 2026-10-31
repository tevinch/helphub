# Portable local paths for Deployer

Share one checked-in configuration across different checkout locations while giving Deployer absolute deployment paths.

For an existing `.paas/deploy.maml`, add `.paas/deploy.php` beside it:

```php
<?php

namespace Deployer;

set('checkout_root', dirname(__DIR__));
import(__DIR__ . '/deploy.maml');
```

Set the anchor **before** importing the MAML file. With this directory layout, `dirname(__DIR__)` is the checkout root, regardless of the command's working directory.

Merge these fields into your existing local `testdeploy` host:

```maml
hosts: {
  testdeploy: {
    local: true
    deploy_path: "{{checkout_root}}/testdeploy"
    current_path: "{{deploy_path}}/public_html"
  }
}
```

Keep its other fields, your `recipe/magento2.php` import, and existing tasks and hooks. From the checkout root, use `-f .paas/deploy.php` in place of the MAML entry point. From another working directory, pass the actual path to that PHP file. This change applies to the local test host; retain the configuration for remote production hosts.

PHP documents [`__DIR__`](https://www.php.net/manual/en/language.constants.magic.php) as the directory of the containing file. Deployer documents [anchored project imports](https://deployer.org/docs/8.x/api#import) and [mixing PHP with MAML](https://deployer.org/docs/8.x/maml).

## Run the example

On Linux, use PHP 8.3 or later in the PHP 8 series, Python 3.9+, Bash, GNU tar, rsync and `sha256sum`. From this example directory, download the pinned official Deployer 8.0.5 release and verify it before execution:

```sh
curl --disable --fail --location --proto '=https' --proto-redir '=https' \
  --output deployer.phar \
  https://github.com/deployphp/deployer/releases/download/v8.0.5/deployer.phar
printf '%s  %s\n' \
  0026dfa73626a8ccde06222fe5fccf03e6d4a19e765914bb87d7d2cc21f3e57d \
  deployer.phar | sha256sum --check -
RUNNER_TEMP=/tmp python3 verify.py "$PWD/deployer.phar"
```

The check creates and removes its own temporary directories. It publishes an inert artifact twice through the common recipe, physically relocates the checkout, and verifies the current link, new content and preserved previous release. Missing-anchor, missing-artifact and omitted-recipe controls must also fail as expected.

The [Magento fixture](magento-paths/.paas/deploy.php) imports the actual Magento recipe and runs only its own path-inspection task:

```sh
DO_NOT_TRACK=true DO_NOT_SHOW_BANNER=true \
  php deployer.phar -f magento-paths/.paas/deploy.php paths:show testdeploy
```

The [filesystem fixture](fixture/.paas/deploy.maml) uses the common recipe. Magento application, Docker and cron hooks are outside this check. Native Windows, macOS, PHP 8.5 and paths containing spaces have no validation claim here.

**Verified:** the included check passed on Ubuntu 24.04 with PHP 8.3.6 and Deployer 8.0.5 in [this run](https://github.com/tevinch/helphub/actions/runs/41192075944), using [these exact source files](https://github.com/tevinch/helphub/tree/e64fc2efcddd20db8a7b6a30df1faf187081e1d5/.github/checks/portable-local-paths). Both artifact publications, physical relocation, preserved earlier content and all three omission controls completed, ending with `NATIVE_PORTABLE_PATHS_VERIFIED`.

Source is available under the [MIT license](LICENSE).

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
