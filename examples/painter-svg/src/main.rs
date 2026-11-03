use egui::{Context, Id, LayerId, Order, Rect, vec2};

struct Demo {
    ctx: Context,
    frames: u8,
}

impl eframe::App for Demo {
    // Eframe requires this host callback. Drawing uses the saved Context and
    // a layer Painter; no image widget or Ui allocation is involved below.
    fn ui(&mut self, _ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let available = self.ctx.content_rect();
        let width = (available.width() - 48.0).clamp(1.0, 240.0);
        let rect = Rect::from_center_size(available.center(), vec2(width, width / 2.0));
        let painter = self
            .ctx
            .layer_painter(LayerId::new(Order::Foreground, Id::unique("svg")));
        if let Err(error) = painter_svg::paint_svg(&painter, "bytes://tiles.svg", rect) {
            eprintln!("SVG could not be drawn: {error}");
        }
        if self.frames < 2 {
            self.frames += 1;
            self.ctx.request_repaint();
        }
    }
}

fn main() -> eframe::Result {
    eframe::run_native(
        "Painter SVG",
        eframe::NativeOptions {
            viewport: egui::ViewportBuilder::default().with_inner_size([400.0, 220.0]),
            renderer: eframe::Renderer::Glow,
            ..Default::default()
        },
        Box::new(|cc| {
            egui_extras::install_image_loaders(&cc.egui_ctx);
            cc.egui_ctx.include_bytes(
                "bytes://tiles.svg",
                include_bytes!("../assets/tiles.svg").as_slice(),
            );
            Ok(Box::new(Demo {
                ctx: cc.egui_ctx.clone(),
                frames: 0,
            }))
        }),
    )
}
