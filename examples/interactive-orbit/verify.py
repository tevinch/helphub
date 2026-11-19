"""Check a visible Qt orbit window using scripted mouse input.

This requires a desktop display. It is not human manual validation.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import importlib.metadata
from pathlib import Path
import time

from PySide6 import QtCore, QtTest, QtWidgets

from orbit import create_scene, start_orbit


def check_trace(trace: dict) -> list[str]:
    errors = []
    events = [e for e in trace['events'] if e['phase'] == 'animation']
    presses = [e for e in events if e['kind'] == 'press']
    releases = [e for e in events if e['kind'] == 'release']
    if not presses or not releases:
        return ['Animation drag was not observed.']
    start, end = presses[0]['t'], releases[-1]['t']
    held = [f for f in trace['frames'] if start < f['t'] < end]
    after = [f for f in trace['frames'] if end < f['t'] and f['phase'] == 'animation']
    moves = [e for e in events if e['kind'] == 'move' and start < e['t'] < end and e['buttons'] & 1]
    if end - start < 2 or len(moves) < 8:
        errors.append('A held drag of at least two seconds was not observed.')
    if len(held) < 8 or len({tuple(f['satellite']) for f in held}) < 8:
        errors.append('Rendered orbit did not advance during the held drag.')
    if not held or max((math.dist(held[0]['camera'], f['camera']) for f in held), default=0) < .05:
        errors.append('Camera did not materially change during the held drag.')
    if len({tuple(f['satellite']) for f in after}) < 4:
        errors.append('Rendered animation did not continue after release.')
    ticks = trace['ticks']
    if len(ticks) != 180:
        errors.append(f'Expected 180 timer callbacks; observed {len(ticks)}.')
    for i, tick in enumerate(ticks):
        angle = 2 * math.pi * i / 180
        if math.dist(tick['satellite'], [1.2 * math.cos(angle), 1.2 * math.sin(angle), 0]) > 1e-7:
            errors.append('Satellite positions do not follow the 180-step orbit.')
            break
    expected_final = [1.2 * math.cos(2 * math.pi * 179 / 180), 1.2 * math.sin(2 * math.pi * 179 / 180), 0]
    final_frames = [f for f in trace['frames'] if f['tick_count'] == 180]
    if not final_frames or math.dist(final_frames[-1]['satellite'], expected_final) > 1e-7:
        errors.append('The final orbit position was not rendered.')
    if trace.get('timer_active_at_completion') is not False:
        errors.append('Finite callback timer did not stop.')
    for phase in ['before', 'after']:
        frames = [f for f in trace['frames'] if f['phase'] == phase]
        if not frames or max((math.dist(frames[0]['camera'], f['camera']) for f in frames), default=0) < .05:
            errors.append(f'Camera interaction {phase} animation was not observed.')
    if len(trace.get('images', [])) != 3 or not all(i['saved'] for i in trace['images']):
        errors.append('Framebuffer images were not saved.')
    if not trace.get('scene_present'):
        errors.append('Expected scene content is missing.')
    if not trace.get('closed') or not trace.get('timer_destroyed') or trace.get('callbacks_after_close'):
        errors.append('Window/timer cleanup failed.')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('verification'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    pl, satellite = create_scene(app)
    clock = time.monotonic()
    phase = 'before'
    timer = None
    closed = False
    post_started = False
    trace = {'events': [], 'frames': [], 'ticks': [], 'timer_destroyed': False,
             'closed': False, 'callbacks_after_close': 0, 'images': []}

    def now():
        return time.monotonic() - clock

    def camera():
        return list(pl.camera.position) + list(pl.camera.focal_point)

    class ObserveInput(QtCore.QObject):
        def eventFilter(self, _obj, event):
            kind = {QtCore.QEvent.Type.MouseButtonPress: 'press',
                    QtCore.QEvent.Type.MouseButtonRelease: 'release',
                    QtCore.QEvent.Type.MouseMove: 'move'}.get(event.type())
            if kind:
                trace['events'].append({'t': now(), 'phase': phase, 'kind': kind,
                                        'buttons': event.buttons().value,
                                        'xy': [event.position().x(), event.position().y()]})
            return False

    observer = ObserveInput()
    pl.interactor.installEventFilter(observer)

    def composed():
        if not closed:
            trace['frames'].append({'t': now(), 'phase': phase,
                                    'camera': camera(), 'satellite': list(satellite.position),
                                    'tick_count': len(trace['ticks'])})

    # A widget composition notification, independent of the orbit callback.
    pl.interactor.frameSwapped.connect(composed)

    def observed_tick():
        if closed:
            trace['callbacks_after_close'] += 1
        else:
            trace['ticks'].append({'t': now(), 'satellite': list(satellite.position)})

    def destroyed():
        trace['timer_destroyed'] = True

    def image(label):
        saved = pl.interactor.grabFramebuffer().save(str(args.output / f'{label}.png'))
        trace['images'].append({'label': label, 't': now(), 'saved': saved})

    def press(pan=False):
        modifier = QtCore.Qt.KeyboardModifier.ShiftModifier if pan else QtCore.Qt.KeyboardModifier.NoModifier
        QtTest.QTest.mousePress(pl.interactor, QtCore.Qt.MouseButton.LeftButton, modifier, QtCore.QPoint(360, 320))

    def move(i):
        QtTest.QTest.mouseMove(pl.interactor, QtCore.QPoint(360 + i * 2, 320 + i), 0)

    def release(pan=False):
        modifier = QtCore.Qt.KeyboardModifier.ShiftModifier if pan else QtCore.Qt.KeyboardModifier.NoModifier
        QtTest.QTest.mouseRelease(pl.interactor, QtCore.Qt.MouseButton.LeftButton, modifier, QtCore.QPoint(480, 380))

    def begin():
        nonlocal phase, timer
        phase = 'animation'
        timer = start_orbit(pl, satellite)
        timer.timeout.connect(observed_tick)
        timer.destroyed.connect(destroyed)
        QtCore.QTimer.singleShot(180, lambda: press(True))
        for i in range(60):
            QtCore.QTimer.singleShot(220 + i * 40, lambda i=i: move(i))
        QtCore.QTimer.singleShot(2700, lambda: release(True))
        # Images are supplementary; frame acceptance uses independent composition events.
        QtCore.QTimer.singleShot(800, lambda: image('during-drag-1'))
        QtCore.QTimer.singleShot(1800, lambda: image('during-drag-2'))

    def post_interaction():
        nonlocal phase, post_started
        post_started = True
        trace['timer_active_at_completion'] = timer.isActive()
        trace['scene_present'] = all(name in pl.renderer.actors and pl.renderer.actors[name].visibility
                                     for name in ['globe', 'marker', 'satellite'])
        context_format = pl.interactor.context().format()
        trace['environment'] = {'platform': platform.platform(), 'python': platform.python_version(),
                                'packages': {name: importlib.metadata.version(name) for name in ['pyvista', 'pyvistaqt', 'vtk', 'PySide6']},
                                'qt_platform': app.platformName(),
                                'render_window': type(pl.render_window).__name__,
                                'opengl_version': [context_format.majorVersion(), context_format.minorVersion()]}
        image('completed-orbit')
        phase = 'after'
        press()
        for i in range(12):
            QtCore.QTimer.singleShot(30 + i * 25, lambda i=i: move(i))
        QtCore.QTimer.singleShot(360, release)
        QtCore.QTimer.singleShot(500, finish)

    def watch():
        if timer is not None and len(trace['ticks']) == 180 and not timer.isActive() and not post_started:
            post_interaction()

    def finish():
        nonlocal closed, phase
        if closed:
            return
        watcher.stop()
        phase = 'closing'
        pl.close()
        closed = True
        trace['closed'] = True
        QtCore.QTimer.singleShot(200, app.quit)

    watcher = QtCore.QTimer()
    watcher.timeout.connect(watch)
    watcher.start(50)
    QtCore.QTimer.singleShot(500, press)
    for i in range(12):
        QtCore.QTimer.singleShot(530 + i * 25, lambda i=i: move(i))
    QtCore.QTimer.singleShot(860, release)
    QtCore.QTimer.singleShot(1100, begin)
    QtCore.QTimer.singleShot(12000, finish)
    app.exec()
    errors = check_trace(trace)
    trace['errors'] = errors
    (args.output / 'trace.json').write_text(json.dumps(trace, indent=2), encoding='utf-8')
    print(json.dumps({'passed': not errors, 'callbacks': len(trace['ticks']),
                      'composed_frames': len(trace['frames']), 'errors': errors}, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
