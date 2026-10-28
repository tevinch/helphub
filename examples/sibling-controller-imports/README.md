# Cross-package controller imports with AssetMapper

A module in one UX bundle can import a controller from another bundle. The bare import name needs an exact importmap entry, and the target file needs a registered AssetMapper logical path.

This small application contains two local Composer packages. `guide/api-grid-bundle` requires `guide/grid-bundle` and extends its Stimulus controller. The page includes both controllers so you can exercise the cross-package import and an owner-provided alias.

## The cross-package entry

The API bundle's `assets/package.json` contains:

```json
{
  "symfony": {
    "importmap": {
      "@guide/grid-bundle/src/controllers/grid_controller.js":
        "path:@guide/grid-bundle/src/controllers/grid_controller.js"
    }
  }
}
```

The `path:` value is a **logical path**. It can refer to another package's assets; `%PACKAGE%` is optional. Flex substitutes `%PACKAGE%` with the directory containing the current package's `package.json` when that placeholder is present. Without it, Flex passes the path through to `importmap:require --path=...`.

The key must match the JavaScript import exactly:

```js
import GridController from '@guide/grid-bundle/src/controllers/grid_controller.js';
```

The provider bundle also needs to expose its files. In `GridBundle.php`:

```php
$container->prependExtensionConfig('framework', [
    'asset_mapper' => ['paths' => [
        dirname(__DIR__).'/assets' => '@guide/grid-bundle',
    ]],
]);
```

This makes `assets/src/controllers/grid_controller.js` available as `@guide/grid-bundle/src/controllers/grid_controller.js`. An importmap entry alone does not register a directory. Check the actual logical path with:

```sh
php bin/console debug:asset-map
```

Both bundles must be installed and enabled. The consumer package declares its provider in Composer's `require`; the application's `Kernel` enables both bundles. These are local path packages to keep the example self-contained.

## Prefer an alias owned by the provider

A shorter public import avoids making consumers depend on a `src/controllers` layout. The grid package declares its own alias:

```json
{
  "symfony": {
    "importmap": {
      "@guide/grid-bundle/controller":
        "path:%PACKAGE%/src/controllers/grid_controller.js"
    }
  }
}
```

Consumers can then use `import GridController from '@guide/grid-bundle/controller'`. The example's standalone grid uses that alias. The API grid keeps the long cross-package import to demonstrate the question's configuration. These are two import names for the same mapped file.

## Run the complete example

Requirements: PHP 8.4+, Composer 2, and Node 20+ for the browser check.

```sh
npm ci
composer install --no-interaction
php bin/console debug:asset-map
php -S 127.0.0.1:8967 -t public public/router.php
```

Open `http://127.0.0.1:8967`. Both sections should say their controller connected. Click **Add API row** twice: the result becomes `API uses grid: 2 rows`. Click **Add grid row**: the result becomes `Grid: 1 row`. Reload and repeat. The original application content is rendered independently above the examples.

The supplied `importmap.php` already contains the app-owned mappings, so an ordinary locked `composer install` can run the page directly. Flex 2.11 synchronizes package metadata during require/update; a normal locked install is not a command to regenerate those entries. If you change local package metadata, update the installed package/lock and review the generated application files.

The example includes `symfony/flex` in the root requirements, enables its Composer plugin, requires `symfony/console` for the importmap command, tags each local package with `symfony-ux`, provides `importmap.php` before installation, and uses the expected `assets/package.json` location. It deliberately disables recipe downloads with `extra.symfony.endpoint: []`, because all application files are supplied here; normal Flex package synchronization remains enabled. No downloaded JavaScript or external service is needed at runtime.

To run the software-operated browser check, stop the development server first:

```sh
npx playwright install chromium
npm test
```

## Keep synchronization disabled when you intend to manage it yourself

The root setting is:

```json
{
  "extra": {
    "symfony/flex": { "synchronize_package_json": false }
  }
}
```

During a Composer require/update, Flex skips package synchronization before its AssetMapper branch when this setting is false. This includes package `symfony.importmap` entries and `controllers.json` updates. A package entry such as `@symfony/ux-router` is not an exception to the opt-out.

Keep the setting disabled and add the needed entries explicitly instead. For this example:

```sh
php bin/console importmap:require '@guide/grid-bundle/src/controllers/grid_controller.js' --path='@guide/grid-bundle/src/controllers/grid_controller.js'
php bin/console importmap:require '@guide/grid-bundle/controller' --path='@guide/grid-bundle/src/controllers/grid_controller.js'
php bin/console importmap:require '@guide/api-grid-bundle/controller' --path='@guide/api-grid-bundle/src/controllers/api_grid_controller.js'
```

Commit the resulting app-owned `importmap.php`. Register required controllers yourself when you opt out of their synchronization; `assets/app.js` does that explicitly here. For another bundle, use its actual metadata and the output of `debug:asset-map`. A command can only map a logical path that the application already exposes.

## Production assets

```sh
APP_ENV=prod php bin/console asset-map:compile
APP_ENV=prod php -S 127.0.0.1:8967 -t public public/router.php
```

Deploy the generated `public/assets/` alongside the application. The sample development router serves compiled files directly for its local check; configure your production web server to serve the `public/` document root normally.

## Verification and scope

The included browser check exercises actual PHP-rendered importmaps, real module requests, both controllers, repeated clicks, preserved application content, and reload. Dependency versions are recorded in the lock files. This is an ordinary configuration example; it does not modify Symfony or assert that the original application's bundles have been tested.

References: [AssetMapper logical paths and local packages](https://symfony.com/doc/current/frontend/asset_mapper.html#using-local-npm-packages), [Flex package synchronization](https://github.com/symfony/flex/blob/v2.11.0/src/PackageJsonSynchronizer.php), [Flex opt-out](https://github.com/symfony/flex/blob/v2.11.0/src/Flex.php).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
