# Give custom HTML colors precedence in Markwon

When a paragraph or heading factory and an inline HTML handler both add a foreground color, both spans are present. In Markwon 4.6.2, a default-priority theme span in this setup can override the HTML color when Android draws the text. Changing plugin registration order alone does not give the inline tag a higher drawing precedence.

[HtmlColors.java](src/main/java/example/HtmlColors.java) makes the theme color a fallback. The paragraph and heading factories append non-drawing markers while keeping the regular Markwon formatting spans. The theme plugin reads those markers in `afterRender` and attaches its foreground spans with Android priority 1. The independent HTML handler attaches its foreground span with the usual priority 0. Android applies the fallback first, then the explicit color inside the tag's range. Both spans are already configured when `toMarkdown()` returns.

The example uses the [Markwon render lifecycle](https://noties.io/Markwon/docs/v4/core/plugins.html#inspect-node-after-render) and the [Android priority flag](https://developer.android.com/reference/android/text/Spanned#SPAN_PRIORITY_SHIFT). The drawing order described here was verified on Android API 33.

## Use it in an Android app

Copy `HtmlColors.java` to your app and adjust its package name. Use the same versions of Markwon Core and HTML in your app's Gradle dependencies.

```kotlin
implementation("io.noties.markwon:core:4.6.2")
implementation("io.noties.markwon:html:4.6.2")
```

Pass your own colors and your existing `TextView`.

```kotlin
val markwon = HtmlColors.create(
    preview.context,
    Color.rgb(10, 60, 140),
    Color.rgb(91, 32, 101),
    Color.rgb(176, 28, 30),
)

val markdown = """
    # Title <accent>RED</accent> end

    Before <accent>RED</accent> after **bold**.
""".trimIndent()

val formatted = markwon.toMarkdown(markdown)
markwon.setParsedMarkdown(preview, formatted)
```

Both instances of `RED` render in red. Other heading text stays purple. Other body text stays blue, and `bold` keeps its emphasis. You can also call `markwon.setMarkdown(preview, markdown)` directly.

If you already have separate plugins, adapt your theme factories to return the markers shown in `ThemeForegroundPlugin` and keep the HTML handler's call to `setSpan()` at its default priority. Replace your original theme foreground spans so only the new fallback spans provide the theme color. Leave your other style spans and HTML settings in place.

## Run the checks

From this directory, run with JDK 21 and Gradle 9.6.1.

```sh
gradle test
```

The tests run Android API 33 text layout and draw each `TextView` into a bitmap with Robolectric native graphics. They check the actual colors inside and around both HTML ranges, the original Markdown structure, a second render in the same view, and reversed plugin registration. They also reproduce the conflict with a default-priority theme and check that the HTML color goes away when its handler is omitted. No Android device or SDK installation is required for this test setup.

## Optional coffee

If this example saved you time and you'd like to buy me a coffee, contributions are entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
