# PriceBuddy availability from CSS classes

When the delivery text changes with stock quantity, read the element's **class attribute** instead of its text. PriceBuddy's native CSS-selector strategy supports `|class`.

In the store's **Availability strategy**, choose **CSS Selector** and use:

```text
span.delivery-information|class
```

Then configure **Match values**:

| Setting | Match type | Value |
| --- | --- | --- |
| Default status | — | In Stock |
| Out of Stock | Regex | `(?:^|\s)delivery-soldout(?:\s|$)` |
| Pre-Order | Regex | `(?:^|\s)delivery-preorder(?:\s|$)` |

Enter these patterns without regex delimiters. `delivery-preorder` is an **illustrative class** used in this example: replace it with the actual preorder class on your store's page. Add corresponding rules for any other unavailable states that store uses.

The common `delivery-information` selector keeps all delivery states in scope. The class-token boundaries avoid matching a different class such as `delivery-soldout-extra`. Class order and extra classes do not matter. Changing quantities, delivery estimates, nested spans or the message language does not change the result.

[availability.json](availability.json) is the same availability configuration in PriceBuddy's native stored shape. It is an availability section, not a complete store import. Use the UI fields above to update the existing store, preserving its title, price, image, domain and other settings.

Save and use the store's **Test** page with known available, sold-out and preorder pages. Confirm the extracted class string and resulting status before relying on the rule. Prefer the native Schema.org strategy when the page already publishes correct structured availability.

## Missing and unknown indicators

In PriceBuddy 1.0.57, a missing or empty extracted value resolves to **In Stock before the configured default is considered**. Setting the default to Out of Stock does not change this missing-value behavior. An unrecognized nonempty class uses the configured default, which is In Stock in the table above.

This configuration distinguishes the named states; it does not make a broken or missing selector a reliable availability signal. If a page introduces another class, add a rule for it. If the common indicator disappears, recheck the selector or use an accurate structured availability field.

## Run the native checks

Requires PHP 8.4+ and an existing PriceBuddy installation with its dependencies installed. From this example directory:

```sh
php verify.php /path/to/pricebuddy
```

The checker loads the installation's real classes. It sends [fixtures.json](fixtures.json) through the real HTTP scraper's public `setBody()` method, PriceBuddy's `StrategyExtractor` and `StockStatus::resolveAvailability()`. Ten complete HTML-to-status cases cover available, sold out, changed text, nested markup, reordered classes, empty text, illustrative preorder, a similar class name, an unrelated marker, an unknown class and a missing indicator. A separate check confirms that a missing value still resolves to In Stock when the default is Out of Stock.

Verified with PriceBuddy **1.0.57** source, web-scraper-for-laravel **1.0.9**, PHP **8.4.27**, DomCrawler **7.4.22** and CSS Selector **8.0.6**. DomCrawler 7.4.22 is a compatible patched version used for these checks; this is not a validation of the release's complete dependency lock. These are scripted checks of the native extraction/status layer. The full app, GUI, database refresh, notifications and live retailer pages were not tested. No upstream source is changed or distributed in this example.

See the official [store strategy guide](https://github.com/jez500/pricebuddy/blob/v1.0.57/docs/docs/stores.md), [selector parsing](https://github.com/jez500/pricebuddy/blob/v1.0.57/app/Services/ScrapeUrl.php) and [stock-status resolution](https://github.com/jez500/pricebuddy/blob/v1.0.57/app/Enums/StockStatus.php). PriceBuddy retains its GPL-3.0 license; this repository licenses only the original configuration, fixtures, checker and guide.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
