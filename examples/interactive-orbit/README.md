# Interactive orbit

Pan or rotate a PyVista scene while a small simulation step keeps updating an actor. This standalone example uses PyVistaQt's documented Qt timer: it updates 180 orbit positions, then leaves the window open for further camera interaction.

## Run

Use Python 3.10 or newer in a desktop environment with a display and compatible binary wheels. The pinned PySide6 release requires macOS 14 or newer on macOS.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.txt
python orbit.py
```

The red cube moves around a blue globe. Drag to rotate; hold Shift while dragging to pan. The 180 updates take about 3.6 seconds at the requested 20 ms interval when the machine keeps up. After the cube stops, keep dragging in the same window. Close the window to exit. Run the command again for another animation.

The scene uses synthetic geometry: a 120×120 sphere, a green marker, a red cube and fixed bounds covering the orbit. It downloads no textures or other assets. Replace those meshes with your own scene while retaining the timer/event-loop pattern.

## The event-loop pattern

`start_orbit()` schedules a short function with:

```python
pl.add_callback(advance, interval=20, count=180)
```

Each call changes the existing satellite actor's `position`, calls `pl.render()` and returns. `QApplication.exec()` keeps processing input and timer events after the finite timer stops. The example sets `auto_update=False`, so explicit rendering also updates the scene when the mouse is still.

Keep scene updates and rendering on the GUI thread, and keep each callback short. Qt timers do not make a blocking simulation step concurrent and do not guarantee an exact frame rate. An existing Qt application should use its existing application/event loop; this script is intended to run standalone.

This is an optional Qt integration. Current native `Plotter.add_timer_event()` drag behavior and the original Linux setup remain unverified here.

## Check the interaction

```sh
python verify.py --output verification
```

The check opens a visible widget and sends scripted QtTest mouse events. It observes the widget's actual press, move and release events, including the held-button mask. Independently observed widget composition events must show both camera movement and changing satellite positions during a held drag, continued rendered animation after release, all 180 timer updates, the final orbit position, interaction before and after completion, and timer cleanup on close. It writes a trace and three framebuffer images, and returns a nonzero exit code if acceptance fails.

Verified on macOS 14.6 arm64, Python 3.12.4, PyVista 0.49.2, PyVistaQt 0.14.0, VTK 9.7.2 and PySide6/Qt 6.12.0. These are scripted checks of a visible native Qt widget; human manual validation and Linux/Windows results are unverified. An offscreen-only run does not establish camera interaction.

References: [PyVistaQt usage](https://qtdocs.pyvista.org/usage.html), [BackgroundPlotter callback API](https://qtdocs.pyvista.org/api_reference.html#pyvistaqt.BackgroundPlotter.add_callback), [Qt timer behavior](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html), and the motivating [interaction question](https://github.com/pyvista/pyvista/issues/9548) with its [linked animation example](https://github.com/pyvista/pyvista/issues/8172).

## Optional coffee

This example is free. If it saves you time, a coffee contribution is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
