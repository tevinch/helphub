# Add text padding to one JXDatePicker

With FlatLaf's SwingX addon, the date editor has an empty border. Its `setMargin` value therefore does not provide the visible inset you would get from a margin-aware text-field border. The picker also has its own layout padding, read from `ComboBox.padding`.

For extra padding inside one editor, set its border after creating the picker:

```java
import com.formdev.flatlaf.ui.FlatEmptyBorder;

datePicker.getEditor().setBorder(new FlatEmptyBorder(6, 10, 6, 10));
datePicker.revalidate();
datePicker.repaint();
```

This adds six logical pixels above and below the text, and ten on either side. These are **additional editor insets**, alongside the picker's existing outer border and layout padding. It leaves the picker's outer border and popup button in place. `FlatEmptyBorder` scales the insets with FlatLaf's UI scale.

This does not require changing `ComboBox.padding` globally. The latter also affects other controls. A native look-and-feel update can recreate the editor or replace its UI-resource border: apply the border again **after** `SwingUtilities.updateComponentTreeUI(...)`. The included demo shows that order when switching themes.

## Run

The example uses FlatLaf 3.7.2, its SwingX addon 3.7.2, and SwingX 1.6.5-1. These were the current Maven Central releases checked on October 29, 2026. Use a JDK with `java` and `javac`; verification used JDK 21.0.12.1.

Download these three JARs into a `lib` directory, or use the same coordinates in your existing build:

| Artifact | Download | SHA-256 |
| --- | --- | --- |
| `com.formdev:flatlaf:3.7.2` | [flatlaf-3.7.2.jar](https://repo.maven.apache.org/maven2/com/formdev/flatlaf/3.7.2/flatlaf-3.7.2.jar) | `917aff3963c88d797d0fd9b9ccbd70f7681c101df9d11c59e2bc7a3a6c0fabf4` |
| `com.formdev:flatlaf-swingx:3.7.2` | [flatlaf-swingx-3.7.2.jar](https://repo.maven.apache.org/maven2/com/formdev/flatlaf-swingx/3.7.2/flatlaf-swingx-3.7.2.jar) | `2ad96beae20885941576afdbc36cdf4c862041e63266d46cb920fb782615864d` |
| `org.swinglabs.swingx:swingx-all:1.6.5-1` | [swingx-all-1.6.5-1.jar](https://repo.maven.apache.org/maven2/org/swinglabs/swingx/swingx-all/1.6.5-1/swingx-all-1.6.5-1.jar) | `2a4f82979cd16d8f1c9eea232a985dff62bf69c4794a37b96099b20d322907c0` |

From this directory, on macOS or Linux:

```sh
javac -cp 'lib/*' DatePickerExample.java PaddingCheck.java
java -cp '.:lib/*' DatePickerExample
```

On Windows, use `.;lib/*` for the runtime classpath instead of `.:lib/*`. The compile classpath remains `lib/*`.

The first field uses the original margin-only approach; the second uses the extra editor border. Both remain ordinary editable date pickers. Switch between light and dark to see the padding reapplied after the native UI update.

## Checks

```sh
java -Dflatlaf.uiScale=1 -Dcheck.scale=1 -cp '.:lib/*' PaddingCheck
java -Dflatlaf.uiScale=2 -Dcheck.scale=2 -cp '.:lib/*' PaddingCheck
```

Each process checks light and dark themes, the actual native editor insets and preferred size, retention of the outer border and UI delegate, reapplication after a native UI update, preservation of the selected date, and committing a different date through the editor. It also renders offscreen PNGs in the current directory. For the original failing control, add `--original`: it must fail because the editor insets remain zero after `setMargin`.

These are scripted EDT and offscreen-rendering checks of the standard left-to-right date editor. Interactive popup selection, the requester's application and human manual validation were not performed. The GUI demo is provided for trying those interactions in your application.

The relevant native implementations are [FlatDatePickerUI](https://github.com/JFormDesigner/FlatLaf/blob/3.7.2/flatlaf-swingx/src/main/java/com/formdev/flatlaf/swingx/ui/FlatDatePickerUI.java) and [FlatEmptyBorder](https://github.com/JFormDesigner/FlatLaf/blob/3.7.2/flatlaf-core/src/main/java/com/formdev/flatlaf/ui/FlatEmptyBorder.java). See also the official [SwingX addon setup](https://github.com/JFormDesigner/FlatLaf/blob/3.7.2/flatlaf-swingx/README.md) and [customization guidance](https://www.formdev.com/flatlaf/how-to-customize/).

## Optional coffee

This example is free. If it saved you some time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
