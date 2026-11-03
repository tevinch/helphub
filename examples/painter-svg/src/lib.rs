use egui::{
    Color32, Painter, Rect, TextureId, TextureOptions,
    load::{LoadError, SizeHint, TexturePoll},
    pos2,
};

/// Rasterize a registered SVG for this rectangle, then add it to a Painter.
///
/// Install `egui_extras` image loaders once and register the SVG bytes first.
/// The URI must end in `.svg`. Match the rectangle to the SVG's aspect ratio
/// if you want to avoid stretching. `None` means pending or an empty rectangle.
pub fn paint_svg(painter: &Painter, uri: &str, rect: Rect) -> Result<Option<TextureId>, LoadError> {
    if !rect.is_finite() || rect.width() <= 0.0 || rect.height() <= 0.0 {
        return Ok(None);
    }
    let width = (rect.width() * painter.pixels_per_point()).ceil().max(1.0) as u32;
    match painter
        .ctx()
        .try_load_texture(uri, TextureOptions::LINEAR, SizeHint::Width(width))?
    {
        TexturePoll::Ready { texture } => {
            painter.image(
                texture.id,
                rect,
                Rect::from_min_max(pos2(0.0, 0.0), pos2(1.0, 1.0)),
                Color32::WHITE,
            );
            Ok(Some(texture.id))
        }
        TexturePoll::Pending { .. } => {
            painter.ctx().request_repaint();
            Ok(None)
        }
    }
}
