package example;

import android.content.Context;
import android.text.Spanned;
import android.text.style.ForegroundColorSpan;

import java.util.Collection;
import java.util.Collections;

import io.noties.markwon.AbstractMarkwonPlugin;
import io.noties.markwon.Markwon;
import io.noties.markwon.MarkwonSpansFactory;
import io.noties.markwon.MarkwonVisitor;
import io.noties.markwon.SpannableBuilder;
import io.noties.markwon.html.HtmlPlugin;
import io.noties.markwon.html.HtmlTag;
import io.noties.markwon.html.MarkwonHtmlRenderer;
import io.noties.markwon.html.TagHandler;
import org.commonmark.node.Heading;
import org.commonmark.node.Node;
import org.commonmark.node.Paragraph;

public final class HtmlColors {
    private HtmlColors() {}

    public static Markwon create(Context context, int paragraphColor, int headingColor, int accentColor) {
        return Markwon.builder(context)
                .usePlugin(new ThemeForegroundPlugin(paragraphColor, headingColor))
                .usePlugin(HtmlPlugin.create()
                        .excludeDefaults(true)
                        .addHandler(new AccentTagHandler(accentColor)))
                .build();
    }

    public static final class ThemeForegroundPlugin extends AbstractMarkwonPlugin {
        // Android applies the higher-priority fallback color before the explicit HTML color.
        private static final int FALLBACK_FLAGS =
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE | (1 << Spanned.SPAN_PRIORITY_SHIFT);

        private final int paragraphColor;
        private final int headingColor;

        public ThemeForegroundPlugin(int paragraphColor, int headingColor) {
            this.paragraphColor = paragraphColor;
            this.headingColor = headingColor;
        }

        @Override
        public void configureSpansFactory(MarkwonSpansFactory.Builder builder) {
            builder.appendFactory(Paragraph.class, (configuration, props) -> new ThemeRegion(paragraphColor));
            builder.appendFactory(Heading.class, (configuration, props) -> new ThemeRegion(headingColor));
        }

        @Override
        public void afterRender(Node node, MarkwonVisitor visitor) {
            SpannableBuilder builder = visitor.builder();
            for (SpannableBuilder.Span span : builder.getSpans(0, builder.length())) {
                if (span.what instanceof ThemeRegion && span.start < span.end) {
                    ThemeRegion region = (ThemeRegion) span.what;
                    builder.setSpan(new ForegroundColorSpan(region.color), span.start, span.end, FALLBACK_FLAGS);
                }
            }
        }
    }

    private static final class ThemeRegion {
        private final int color;

        private ThemeRegion(int color) {
            this.color = color;
        }
    }

    public static final class AccentTagHandler extends TagHandler {
        private final int color;

        public AccentTagHandler(int color) {
            this.color = color;
        }

        @Override
        public Collection<String> supportedTags() {
            return Collections.singletonList("accent");
        }

        @Override
        public void handle(MarkwonVisitor visitor, MarkwonHtmlRenderer renderer, HtmlTag tag) {
            if (tag.start() < tag.end()) {
                visitor.builder().setSpan(new ForegroundColorSpan(color), tag.start(), tag.end());
            }
        }
    }
}
