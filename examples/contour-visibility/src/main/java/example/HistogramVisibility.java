package example;

import io.fair_acc.chartfx.XYChart;
import io.fair_acc.chartfx.axes.spi.DefaultNumericAxis;
import io.fair_acc.chartfx.renderer.ContourType;
import io.fair_acc.chartfx.renderer.spi.ContourDataSetRenderer;
import io.fair_acc.chartfx.ui.css.DataSetNode;
import io.fair_acc.chartfx.ui.geometry.Side;
import io.fair_acc.dataset.spi.Histogram2;
import javafx.application.Application;
import javafx.geometry.Insets;
import javafx.scene.Scene;
import javafx.scene.control.ToggleButton;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.stage.Stage;

import static io.fair_acc.dataset.spi.AbstractHistogram.HistogramOuterBounds.BINS_ALIGNED_WITH_BOUNDARY;

/** Two external controls for the existing series of one contour renderer. */
public final class HistogramVisibility {
    private HistogramVisibility() {}

    public static BorderPane createContent() {
        var x = new DefaultNumericAxis("x", 0, 10, 1);
        var y = new DefaultNumericAxis("y", 0, 10, 1);
        var z = new DefaultNumericAxis("count", 0, 30, 5);
        x.setSide(Side.BOTTOM);
        y.setSide(Side.LEFT);
        z.setSide(Side.RIGHT);
        x.setAutoRanging(false);
        y.setAutoRanging(false);
        z.setAutoRanging(false);

        var chart = new XYChart(x, y);
        chart.setId("histogram-chart");
        chart.setAnimated(false);
        chart.setLegendVisible(false);

        var renderer = new ContourDataSetRenderer();
        renderer.setContourType(ContourType.HEATMAP);
        renderer.getAxes().addAll(x, y, z);
        chart.getRenderers().setAll(renderer);

        var left = histogram("Histogram A", 0, 5);
        var right = histogram("Histogram B", 5, 10);
        DataSetNode seriesA = renderer.addDataSet(left);
        DataSetNode seriesB = renderer.addDataSet(right);

        var controls = new HBox(12,
                visibilityButton("Histogram A", "toggle-a", seriesA),
                visibilityButton("Histogram B", "toggle-b", seriesB));
        controls.setPadding(new Insets(12));
        return new BorderPane(chart, controls, null, null, null);
    }

    private static ToggleButton visibilityButton(String label, String id, DataSetNode series) {
        var button = new ToggleButton(label);
        button.setId(id);
        button.setSelected(series.isVisible());
        // This is the same visibility property that the built-in legend toggles.
        button.selectedProperty().bindBidirectional(series.visibleProperty());
        return button;
    }

    private static Histogram2 histogram(String name, double minX, double maxX) {
        var histogram = new Histogram2(name, 12, minX, maxX, 12, 0, 10,
                BINS_ALIGNED_WITH_BOUNDARY);
        for (int x = 0; x < 12; x++) {
            for (int y = 0; y < 12; y++) {
                double weight = 1 + ((x + 3 * y) % 20);
                histogram.fill(minX + (x + 0.5) * (maxX - minX) / 12,
                        (y + 0.5) * 10 / 12, weight);
            }
        }
        return histogram;
    }

    public static final class Window extends Application {
        @Override public void start(Stage stage) {
            stage.setTitle("Histogram visibility");
            stage.setScene(new Scene(createContent(), 900, 650));
            stage.show();
        }
    }

    public static void main(String[] args) {
        Application.launch(Window.class, args);
    }
}
