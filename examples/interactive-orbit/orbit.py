"""Keep camera interaction available while a short Qt timer advances an orbit."""
from __future__ import annotations

import math
import sys

from PySide6.QtWidgets import QApplication
import pyvista as pv
from pyvistaqt import BackgroundPlotter


def create_scene(app: QApplication) -> tuple[BackgroundPlotter, pv.Actor]:
    pl = BackgroundPlotter(app=app, show=True, window_size=(960, 720),
                           title='Interactive orbit', toolbar=False, menu_bar=False,
                           auto_update=False)
    pl.set_background('#182333')
    pl.add_mesh(pv.Sphere(radius=1, theta_resolution=120, phi_resolution=120),
                color='#417ba6', smooth_shading=True, name='globe')
    latitude, longitude = math.radians(47), math.radians(109)
    marker = (math.cos(latitude) * math.cos(longitude),
              math.cos(latitude) * math.sin(longitude), math.sin(latitude))
    pl.add_mesh(pv.Sphere(radius=.065, center=marker), color='lime', name='marker')
    satellite = pl.add_mesh(pv.Cube(x_length=.1, y_length=.1, z_length=.1),
                            color='#ff514b', name='satellite')
    satellite.position = (1.2, 0, 0)
    pl.show_bounds(bounds=(-1.3, 1.3, -1.3, 1.3, -1.3, 1.3),
                   grid='back', location='outer', color='white')
    pl.camera_position = 'iso'
    pl.camera.zoom(.8)
    pl.add_text('Drag: rotate | Shift + drag: pan\nOrbit: 180 steps at 20 ms; the window stays open.',
                font_size=11, color='white')
    return pl, satellite


def start_orbit(pl: BackgroundPlotter, satellite: pv.Actor):
    """Schedule exactly 180 short GUI-thread updates and return their QTimer."""
    step = 0

    def advance():
        nonlocal step
        angle = 2 * math.pi * step / 180
        satellite.position = (1.2 * math.cos(angle), 1.2 * math.sin(angle), 0)
        step += 1
        pl.render()

    return pl.add_callback(advance, interval=20, count=180)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    pl, satellite = create_scene(app)
    timer = start_orbit(pl, satellite)
    # Keep the application event loop running, including after the finite timer stops.
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
