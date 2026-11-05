# Show and hide contour datasets with custom buttons

A `ContourDataSetRenderer` has one `DataSetNode` for each attached dataset. Change that node's `visible` property to hide or show the series. The [built-in legend uses the same property](https://github.com/fair-acc/chart-fx/blob/11.3.1/chartfx-chart/src/main/java/io/fair_acc/chartfx/legend/spi/DefaultLegend.java#L69-L75).

For data already attached to your renderer:

```java
DataSetNode series = renderer.getStyleableNode(histogram);
button.setOnAction(event -> series.setVisible(!series.isVisible()));
```

Use the same dataset object that you added to this renderer. `getStyleableNode` throws if that object isn't attached. When adding a new dataset, `renderer.addDataSet(histogram)` returns its node directly.

The dataset stays in `renderer.getDatasets()`, with its data intact. You don't need to reload it or remove and re-add it. Visibility belongs to the node **in that renderer**: if the same data also appears in another renderer, toggle that renderer's node separately. This also applies to separate projection datasets.

## Run the example

Requires JDK 21 and Maven. This example pins ChartFX **11.3.1** and JavaFX **21.0.13**.

```sh
mvn compile exec:java
```

The window shows two 2D histograms rendered by one `ContourDataSetRenderer`, with the legend hidden. The two buttons above the chart independently show and hide Histogram A and Histogram B. You can hide both, then show them again.

Here the buttons are `ToggleButton`s, so their selected state is bound to visibility:

```java
button.setSelected(series.isVisible());
button.selectedProperty().bindBidirectional(series.visibleProperty());
```

This keeps a button in sync if another control also changes the same node's visibility. Use this binding **instead of** the `setOnAction` toggle above. Don't bind a property that your application already controls through another binding. Make changes on the JavaFX application thread; normal button handlers already run there.

The sample uses fixed axes so hiding a series doesn't change the coordinate system. With auto-ranging enabled, visible datasets also affect the axis range.

## Verification

Scripted checks used ChartFX 11.3.1, JavaFX 21.0.13 and Temurin JDK 21.0.12.1 on macOS, with Monocle 21.0.2 and software rendering. They exercised the actual JavaFX buttons, scene and rendered canvas: A hidden, both hidden, A only, both restored, repeated toggles, and a data update while A was hidden. The unchanged series' pixels stayed the same, the original canvas returned exactly after restoring visibility, and the dataset objects, nodes and original bin values stayed intact through the toggles. The hidden update appeared when A was shown again.

These are offscreen software checks. They don't verify your application's renderer setup, other platform graphics backends or your version of ChartFX.

API references: [dataset node lookup](https://github.com/fair-acc/chart-fx/blob/11.3.1/chartfx-chart/src/main/java/io/fair_acc/chartfx/renderer/Renderer.java#L47-L63), [visibility in rendering and axis ranges](https://github.com/fair-acc/chart-fx/blob/11.3.1/chartfx-chart/src/main/java/io/fair_acc/chartfx/renderer/spi/AbstractRendererXY.java#L49-L69).

## Optional coffee

This example is free. If it saved you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
