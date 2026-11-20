use std::{error::Error, io};

use smithay_client_toolkit::{
    compositor::{CompositorHandler, CompositorState},
    output::{OutputHandler, OutputState},
    registry::{ProvidesRegistryState, RegistryState},
    shell::{
        xdg::{
            window::{Window, WindowConfigure, WindowDecorations, WindowHandler},
            XdgShell,
        },
        WaylandSurface,
    },
    shm::{slot::SlotPool, Shm, ShmHandler},
};
use wayland_client::{
    globals::registry_queue_init,
    protocol::{wl_output, wl_shm, wl_surface},
    Connection, Proxy, QueueHandle,
};

fn main() -> Result<(), Box<dyn Error>> {
    let connection = Connection::connect_to_env()?;
    let (globals, mut queue) = registry_queue_init(&connection)?;
    let queue_handle = queue.handle();
    let compositor = CompositorState::bind(&globals, &queue_handle)?;
    let shell = XdgShell::bind(&globals, &queue_handle)?;
    let surface = compositor.create_surface(&queue_handle);
    let window = shell.create_window(surface, WindowDecorations::RequestServer, &queue_handle);
    window.set_title("Wayland integer scaling");
    window.set_app_id("wayland-integer-scale");
    window.commit(); // An empty commit solicits the first xdg-shell configure.

    let shm = Shm::bind(&globals, &queue_handle)?;
    let mut demo = Demo {
        registry: RegistryState::new(&globals),
        outputs: OutputState::new(&globals, &queue_handle),
        pool: SlotPool::new(256 * 160 * 4, &shm)?,
        shm,
        window,
        logical_size: (256, 160),
        scale: 1,
        configured: false,
        redraw: false,
        closed: false,
    };

    while !demo.closed {
        queue.blocking_dispatch(&mut demo)?;
        if demo.redraw && !demo.closed {
            demo.draw()?;
            demo.redraw = false;
        }
    }

    Ok(())
}

struct Demo {
    registry: RegistryState,
    outputs: OutputState,
    pool: SlotPool,
    shm: Shm,
    window: Window,
    logical_size: (i32, i32),
    scale: i32,
    configured: bool,
    redraw: bool,
    closed: bool,
}

impl Demo {
    fn draw(&mut self) -> Result<(), Box<dyn Error>> {
        let surface = self.window.wl_surface();
        let (logical_width, logical_height) = self.logical_size;
        let scale = if surface.version() >= 3 {
            self.scale
        } else {
            1
        };
        let invalid_size = || io::Error::other("scaled window exceeds wl_shm size limits");
        let width = logical_width.checked_mul(scale).ok_or_else(invalid_size)?;
        let height = logical_height.checked_mul(scale).ok_or_else(invalid_size)?;
        let stride = width.checked_mul(4).ok_or_else(invalid_size)?;
        let bytes = stride.checked_mul(height).ok_or_else(invalid_size)? as usize;

        // A fresh slot avoids writing into a buffer still held by the compositor.
        let (buffer, canvas) =
            self.pool
                .create_buffer(width, height, stride, wl_shm::Format::Argb8888)?;
        for (index, pixel) in canvas[..bytes].chunks_exact_mut(4).enumerate() {
            let x = (index % width as usize) as i32;
            let y = (index / width as usize) as i32;
            let cell = (x / scale / 32 + y / scale / 32) % 2;
            let color: u32 = if cell == 0 { 0xff2a6a95 } else { 0xffeaa265 };
            pixel.copy_from_slice(&color.to_le_bytes());
        }

        if surface.version() >= 3 {
            surface.set_buffer_scale(scale);
        }
        buffer.attach_to(surface)?;
        if surface.version() >= 4 {
            surface.damage_buffer(0, 0, width, height);
        } else {
            surface.damage(0, 0, logical_width, logical_height);
        }
        self.window.commit();
        Ok(())
    }
}

impl CompositorHandler for Demo {
    fn scale_factor_changed(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        surface: &wl_surface::WlSurface,
        new_scale: i32,
    ) {
        if surface == self.window.wl_surface() && new_scale > 0 && new_scale != self.scale {
            self.scale = new_scale;
            self.redraw = self.configured;
        }
    }

    fn transform_changed(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &wl_surface::WlSurface,
        _: wl_output::Transform,
    ) {
    }
    fn frame(&mut self, _: &Connection, _: &QueueHandle<Self>, _: &wl_surface::WlSurface, _: u32) {}
    fn surface_enter(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &wl_surface::WlSurface,
        _: &wl_output::WlOutput,
    ) {
    }
    fn surface_leave(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &wl_surface::WlSurface,
        _: &wl_output::WlOutput,
    ) {
    }
}

impl WindowHandler for Demo {
    fn request_close(&mut self, _: &Connection, _: &QueueHandle<Self>, _: &Window) {
        self.closed = true;
    }

    fn configure(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &Window,
        config: WindowConfigure,
        _: u32,
    ) {
        if let Some(width) = config.new_size.0 {
            self.logical_size.0 = width.get() as i32;
        }
        if let Some(height) = config.new_size.1 {
            self.logical_size.1 = height.get() as i32;
        }
        self.configured = true;
        self.redraw = true;
    }
}

impl OutputHandler for Demo {
    fn output_state(&mut self) -> &mut OutputState {
        &mut self.outputs
    }
    fn new_output(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {}
    fn update_output(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {}
    fn output_destroyed(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {}
}

impl ShmHandler for Demo {
    fn shm_state(&mut self) -> &mut Shm {
        &mut self.shm
    }
}

impl ProvidesRegistryState for Demo {
    fn registry(&mut self) -> &mut RegistryState {
        &mut self.registry
    }
    smithay_client_toolkit::registry_handlers![OutputState];
}

smithay_client_toolkit::delegate_registry!(Demo);
smithay_client_toolkit::delegate_dispatch2!(Demo);
