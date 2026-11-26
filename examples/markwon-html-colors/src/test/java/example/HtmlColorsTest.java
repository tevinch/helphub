package example;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.text.Layout;
import android.text.Spanned;
import android.text.TextPaint;
import android.text.style.ForegroundColorSpan;
import android.text.style.UnderlineSpan;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import io.noties.markwon.AbstractMarkwonPlugin;
import io.noties.markwon.Markwon;
import io.noties.markwon.MarkwonSpansFactory;
import io.noties.markwon.core.spans.HeadingSpan;
import io.noties.markwon.core.spans.StrongEmphasisSpan;
import io.noties.markwon.html.HtmlPlugin;
import org.commonmark.node.Heading;
import org.commonmark.node.Paragraph;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

@RunWith(RobolectricTestRunner.class)
@SuppressWarnings("deprecation") // This JVM fixture uses the Android framework resources only.
@Config(sdk = 33, manifest = Config.NONE)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class HtmlColorsTest {
    private static final int PARAGRAPH = Color.rgb(10, 60, 140);
    private static final int HEADING = Color.rgb(91, 32, 101);
    private static final int EMPHASIS = Color.rgb(176, 28, 30);
    private static final String DOCUMENT = """
            # Title <accent>RED</accent> end

            Before <accent>RED</accent> after **bold**.

            Plain text.
            """;

    @Test
    public void htmlOverridesOnlyItsOwnRangesAndPreservesMarkdown() {
        Markwon markwon = HtmlColors.create(RuntimeEnvironment.getApplication(), PARAGRAPH, HEADING, EMPHASIS);
        Spanned parsed = markwon.toMarkdown(DOCUMENT);
        assertEquals("Title RED end\n\nBefore RED after bold.\n\nPlain text.", parsed.toString());

        HeadingSpan[] headings = parsed.getSpans(0, parsed.length(), HeadingSpan.class);
        assertEquals(1, headings.length);
        assertEquals(0, parsed.getSpanStart(headings[0]));
        assertEquals("Title RED end".length(), parsed.getSpanEnd(headings[0]));

        int boldStart = parsed.toString().indexOf("bold");
        StrongEmphasisSpan[] bold = parsed.getSpans(boldStart, boldStart + 4, StrongEmphasisSpan.class);
        assertEquals(1, bold.length);
        TextPaint paint = new TextPaint();
        bold[0].updateDrawState(paint);
        assertTrue(paint.isFakeBoldText());
        assertEquals(boldStart, parsed.getSpanStart(bold[0]));
        assertEquals(boldStart + 4, parsed.getSpanEnd(bold[0]));

        TextView textView = textView();
        markwon.setParsedMarkdown(textView, parsed);
        assertDrawnColor(textView, "Title", 0, HEADING);
        assertDrawnColor(textView, "RED", 0, EMPHASIS);
        assertDrawnColor(textView, "end", 0, HEADING);
        assertDrawnColor(textView, "Before", 0, PARAGRAPH);
        assertDrawnColor(textView, "RED", 1, EMPHASIS);
        assertDrawnColor(textView, "after", 0, PARAGRAPH);
        assertDrawnColor(textView, "bold", 0, PARAGRAPH);
        assertDrawnColor(textView, "Plain", 0, PARAGRAPH);

        markwon.setMarkdown(textView, "New <accent>RED</accent> after.");
        assertEquals("New RED after.", textView.getText().toString());
        assertDrawnColor(textView, "New", 0, PARAGRAPH);
        assertDrawnColor(textView, "RED", 0, EMPHASIS);
        assertDrawnColor(textView, "after", 0, PARAGRAPH);
    }

    @Test
    public void reversingPluginRegistrationKeepsTheColorsAndHtmlSettings() {
        Markwon markwon = Markwon.builder(RuntimeEnvironment.getApplication())
                .usePlugin(HtmlPlugin.create().excludeDefaults(true)
                        .addHandler(new HtmlColors.AccentTagHandler(EMPHASIS)))
                .usePlugin(new HtmlColors.ThemeForegroundPlugin(PARAGRAPH, HEADING))
                .build();
        TextView textView = textView();
        Spanned parsed = markwon.toMarkdown("Before <accent>RED</accent> <u>Plain</u>.");
        assertEquals("Before RED Plain.", parsed.toString());
        assertEquals(0, parsed.getSpans(0, parsed.length(), UnderlineSpan.class).length);
        int redStart = parsed.toString().indexOf("RED");
        ForegroundColorSpan[] spans = parsed.getSpans(redStart, redStart + 3, ForegroundColorSpan.class);
        assertEquals(2, spans.length);
        assertEquals(PARAGRAPH, spans[0].getForegroundColor());
        assertEquals(EMPHASIS, spans[1].getForegroundColor());
        assertEquals(redStart, parsed.getSpanStart(spans[1]));
        assertEquals(redStart + 3, parsed.getSpanEnd(spans[1]));
        markwon.setParsedMarkdown(textView, parsed);
        assertDrawnColor(textView, "Before", 0, PARAGRAPH);
        assertDrawnColor(textView, "RED", 0, EMPHASIS);
        assertDrawnColor(textView, "Plain", 0, PARAGRAPH);
    }

    @Test
    public void defaultPriorityThemeOverridesRegisteredHtmlColor() {
        TextView textView = textView();
        Markwon markwon = createLegacyMarkwon();
        Spanned parsed = markwon.toMarkdown(DOCUMENT);
        int redStart = parsed.toString().indexOf("RED");
        ForegroundColorSpan[] spans = parsed.getSpans(redStart, redStart + 3, ForegroundColorSpan.class);
        assertEquals(2, spans.length);
        assertEquals(EMPHASIS, spans[0].getForegroundColor());
        assertEquals(HEADING, spans[1].getForegroundColor());
        markwon.setParsedMarkdown(textView, parsed);
        assertDrawnColor(textView, "RED", 0, HEADING);
        assertDrawnColor(textView, "RED", 1, PARAGRAPH);
    }

    @Test
    public void omittingTheCustomTagHandlerLeavesOnlyTheThemeColor() {
        Markwon markwon = Markwon.builder(RuntimeEnvironment.getApplication())
                .usePlugin(new HtmlColors.ThemeForegroundPlugin(PARAGRAPH, HEADING))
                .usePlugin(HtmlPlugin.create().excludeDefaults(true))
                .build();
        TextView textView = textView();
        markwon.setMarkdown(textView, "Before <accent>RED</accent> after.");
        assertDrawnColor(textView, "RED", 0, PARAGRAPH);
    }

    private static Markwon createLegacyMarkwon() {
        AbstractMarkwonPlugin theme = new AbstractMarkwonPlugin() {
            @Override
            public void configureSpansFactory(MarkwonSpansFactory.Builder builder) {
                builder.appendFactory(Paragraph.class, (config, props) -> new ForegroundColorSpan(PARAGRAPH));
                builder.appendFactory(Heading.class, (config, props) -> new ForegroundColorSpan(HEADING));
            }
        };
        return Markwon.builder(RuntimeEnvironment.getApplication())
                .usePlugin(theme)
                .usePlugin(HtmlPlugin.create().excludeDefaults(true)
                        .addHandler(new HtmlColors.AccentTagHandler(EMPHASIS)))
                .build();
    }

    private static TextView textView() {
        TextView view = new TextView(RuntimeEnvironment.getApplication());
        view.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        view.setTextColor(Color.BLACK);
        view.setTextSize(28);
        return view;
    }

    private static void assertDrawnColor(TextView view, String word, int occurrence, int color) {
        int exactWidth = View.MeasureSpec.makeMeasureSpec(900, View.MeasureSpec.EXACTLY);
        int freeHeight = View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED);
        view.measure(exactWidth, freeHeight);
        view.layout(0, 0, view.getMeasuredWidth(), view.getMeasuredHeight());

        String value = view.getText().toString();
        int start = -1;
        for (int i = 0; i <= occurrence; i++) {
            start = value.indexOf(word, start + 1);
            assertTrue("Missing word " + word, start >= 0);
        }
        Layout layout = view.getLayout();
        assertNotNull(layout);
        int line = layout.getLineForOffset(start);
        int xStart = Math.round(layout.getPrimaryHorizontal(start)) + view.getTotalPaddingLeft();
        int xEnd = Math.round(layout.getPrimaryHorizontal(start + word.length())) + view.getTotalPaddingLeft();
        int yStart = layout.getLineTop(line) + view.getTotalPaddingTop();
        int yEnd = layout.getLineBottom(line) + view.getTotalPaddingTop();

        Bitmap bitmap = Bitmap.createBitmap(view.getWidth(), view.getHeight(), Bitmap.Config.ARGB_8888);
        view.draw(new Canvas(bitmap));
        int matching = 0;
        int unexpected = 0;
        for (int y = yStart; y < yEnd; y++) {
            for (int x = xStart; x < xEnd; x++) {
                int pixel = bitmap.getPixel(x, y);
                if (pixel == color) {
                    matching++;
                } else if (pixel == PARAGRAPH || pixel == HEADING || pixel == EMPHASIS) {
                    unexpected++;
                }
            }
        }
        bitmap.recycle();
        assertTrue(word + " rendered " + matching + " ink pixels in #" + Integer.toHexString(color),
                matching > 3);
        assertEquals(word + " has ink from another configured color", 0, unexpected);
    }
}
