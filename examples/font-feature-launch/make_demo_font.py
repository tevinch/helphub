"""Make a tiny sample font with one stylistic alternative; installs no fonts."""
import sys
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString


def make_font(destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"Choose a new output path: {destination}")
    glyphs = [".notdef", "a", "a.alt"]
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(glyphs)
    builder.setupCharacterMap({97: "a"})
    outlines = {}
    for name in glyphs:
        pen = TTGlyphPen(None)
        if name != ".notdef":
            points = [(80, 0), (520, 0), (300, 700)] if name == "a.alt" else [(80, 0), (520, 0), (520, 500), (80, 500)]
            pen.moveTo(points[0])
            for point in points[1:]:
                pen.lineTo(point)
            pen.closePath()
        outlines[name] = pen.glyph()
    builder.setupGlyf(outlines)
    builder.setupHorizontalMetrics({name: (600, 0) for name in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Feature Demo", "styleName": "Regular", "uniqueFontIdentifier": "FeatureDemo-Regular", "fullName": "Feature Demo Regular", "psName": "FeatureDemo-Regular", "version": "Version 1.0"})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.setupMaxp()
    addOpenTypeFeaturesFromString(builder.font, "languagesystem DFLT dflt; feature ss01 { sub a by a.alt; } ss01;")
    builder.save(destination)
    print(destination)


if __name__ == "__main__":
    make_font(sys.argv[1] if len(sys.argv) > 1 else "feature-demo.ttf")
