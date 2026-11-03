use egui::{Color32, Context, Id, LayerId, Order, RawInput, Rect, Shape, TextureId, pos2, vec2};
use painter_svg::paint_svg;

// A headless test inspects deltas instead of uploading them to a GPU.
struct Output(egui::FullOutput);
impl std::ops::Deref for Output {
    type Target = egui::FullOutput;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}
impl Drop for Output {
    fn drop(&mut self) {
        self.0.textures_delta.clear();
    }
}

const URI: &str = "bytes://tiles.svg";
const SVG: &[u8] = include_bytes!("../assets/tiles.svg");

fn setup() -> Context {
    let ctx = Context::default();
    egui_extras::install_image_loaders(&ctx);
    ctx.include_bytes(URI, SVG);
    ctx
}

fn draw(ctx: &Context, rect: Rect) -> (Output, TextureId) {
    let mut calls = 0;
    let mut texture = None;
    let output = Output(ctx.run_pass(
        RawInput {
            screen_rect: Some(Rect::from_min_size(pos2(0.0, 0.0), vec2(800.0, 600.0))),
            ..Default::default()
        },
        |ctx| {
            calls += 1;
            let painter = ctx.layer_painter(LayerId::new(Order::Middle, Id::unique("picture")));
            texture = paint_svg(&painter, URI, rect).expect("valid embedded SVG");
        },
    ));
    assert!(calls > 0, "drawing callback must actually run");
    let texture = texture.expect("SVG must be drawn, not left pending or omitted");
    (output, texture)
}

fn assert_mesh(output: &Output, texture: TextureId, rect: Rect) {
    let meshes: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            Shape::Mesh(m) if m.texture_id == texture => Some(m),
            _ => None,
        })
        .collect();
    assert_eq!(meshes.len(), 1, "Painter must add exactly one image mesh");
    let mesh = meshes[0];
    assert!(mesh.is_valid());
    assert_eq!(mesh.vertices.len(), 4);
    assert_eq!(mesh.indices.len(), 6);
    assert_eq!(mesh.calc_bounds(), rect);
    assert_eq!(
        mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>(),
        vec![
            pos2(0.0, 0.0),
            pos2(1.0, 0.0),
            pos2(0.0, 1.0),
            pos2(1.0, 1.0)
        ]
    );
    assert!(mesh.vertices.iter().all(|v| v.color == Color32::WHITE));
}

#[test]
fn svg_becomes_rgba_texture_and_painter_mesh_then_remains_drawable() {
    let ctx = setup();
    let rect = Rect::from_min_size(pos2(24.0, 32.0), vec2(120.0, 60.0));
    let (output, id) = draw(&ctx, rect);
    assert_mesh(&output, id, rect);
    let delta = output
        .textures_delta
        .set
        .get(&id)
        .and_then(|d| d.first())
        .expect("SVG texture uploaded");
    let egui::ImageData::Color(image) = &delta.image;
    assert_eq!(image.size, [120, 60]);
    assert_eq!(image.pixels[30 * 120 + 25], Color32::from_rgb(229, 75, 75));
    assert_eq!(image.pixels[30 * 120 + 90], Color32::from_rgb(54, 179, 126));
    assert_eq!(image.pixels[0], Color32::TRANSPARENT);
    let primitives = ctx.tessellate(output.shapes.clone(), output.pixels_per_point);
    assert!(primitives.iter().any(|p| matches!(&p.primitive, egui::epaint::Primitive::Mesh(m) if m.texture_id == id && !m.indices.is_empty())));
    let (again, same_id) = draw(&ctx, rect);
    assert_eq!(same_id, id);
    assert_mesh(&again, same_id, rect);
}

#[test]
fn resizing_and_high_dpi_use_physical_resolution_without_changing_destination() {
    let ctx = setup();
    let rect = Rect::from_min_size(pos2(20.0, 20.0), vec2(180.0, 90.0));
    ctx.set_pixels_per_point(2.0);
    let (output, id) = draw(&ctx, rect);
    assert_eq!(output.pixels_per_point, 2.0);
    assert_mesh(&output, id, rect);
    let delta = output
        .textures_delta
        .set
        .get(&id)
        .and_then(|d| d.first())
        .unwrap();
    assert_eq!(delta.image.size(), [360, 180]);
    let (small, small_id) = draw(
        &ctx,
        Rect::from_min_size(pos2(20.0, 20.0), vec2(60.0, 30.0)),
    );
    let delta = small
        .textures_delta
        .set
        .get(&small_id)
        .and_then(|d| d.first())
        .unwrap();
    assert_eq!(delta.image.size(), [120, 60]);
}

#[test]
fn missing_loader_wrong_extension_and_invalid_svg_report_errors() {
    for (installed, uri, bytes) in [
        (false, URI, SVG),
        (true, "bytes://tiles", SVG),
        (true, URI, b"<not-an-svg>" as &[u8]),
    ] {
        let ctx = Context::default();
        if installed {
            egui_extras::install_image_loaders(&ctx);
        }
        ctx.include_bytes(uri, bytes.to_vec());
        let mut calls = 0;
        let mut error = None;
        let _output = Output(ctx.run_pass(Default::default(), |ctx| {
            calls += 1;
            let painter = ctx.layer_painter(LayerId::background());
            error = paint_svg(
                &painter,
                uri,
                Rect::from_min_size(pos2(0.0, 0.0), vec2(120.0, 60.0)),
            )
            .err();
        }));
        assert!(calls > 0);
        assert!(
            error.is_some(),
            "configuration/parse error must not be silently ignored: {uri}, loader={installed}"
        );
    }
}
