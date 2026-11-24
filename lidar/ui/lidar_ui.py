#!/usr/bin/env python3
"""Native GTK/Wayland viewer for the board's existing RPLIDAR demo."""

import argparse
import fcntl
import json
import math
from pathlib import Path
import signal
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gdk, GLib, Gtk, Pango, PangoCairo
import cairo

from scan_model import Scanner


CSS = b'''
window { background: #101820; color: #e6eff5; font-family: Sans; font-size: 13px; }
label { color: #dce8ef; }
.title { font-size: 22px; font-weight: bold; color: #f3fafc; }
.muted { color: #8ea4b4; font-size: 12px; }
.section { color: #89a2b2; font-size: 11px; font-weight: bold; }
.metric { color: #58e1bd; font-size: 33px; font-weight: bold; }
.status { color: #58e1bd; font-size: 14px; font-weight: bold; }
.error { color: #ffb483; }
.sidebar { background: #16222d; border-radius: 12px; }
button { background: #253745; color: #e1edf3; border: none;
         border-radius: 7px; padding: 8px 10px; box-shadow: none; }
button:hover { background: #344e60; }
button:disabled { opacity: 0.4; }
button.primary { background: #39cfa7; color: #08251f; font-weight: bold; }
button.primary:hover { background: #61e4c2; }
button.stop { background: #4b3030; color: #ffc0ac; }
button:checked { background: #34634f; color: #8affd6; }
combobox button, spinbutton { background: #253745; color: #e1edf3; }
spinbutton entry { background: #253745; color: #e1edf3; border: none; }
separator { background: #2b3c49; min-height: 1px; }
'''


class Viewer:
    def __init__(self, args):
        self.args = args
        self.scanner = Scanner(args.device, args.binary)
        self.display = self.scanner.snapshot()
        self.closing = False
        self.paused = False
        self.selected = None
        self.radius_mm = 6000
        self.minimum_quality = 1
        self.hit_points = []
        self.verify_phase = 0
        self.verify_first = 0
        self.verify_restarted = 0
        self.verify_passed = False
        self.started_at = time.monotonic()
        self.saved_screenshot = False
        self.window = Gtk.Window(title='C1 雷达 · 实时扫描')
        self.window.set_icon_from_file(str(Path(__file__).with_name('radar.png')))
        self.window.set_default_size(1024, 600)
        self.window.set_size_request(800, 480)
        self.window.connect('delete-event', self.on_close)
        self.window.connect('key-press-event', self.on_key)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_border_width(14)
        self.window.add(root)
        header = Gtk.Box(spacing=16)
        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        heading.pack_start(self.label('C1  /  雷达扫描', 'title'), False, False, 0)
        heading.pack_start(self.label('360° 实时点云  ·  RPLIDAR C1', 'muted'), False, False, 0)
        header.pack_start(heading, True, True, 0)
        self.status = self.label('●  准备就绪', 'status')
        header.pack_end(self.status, False, False, 0)
        root.pack_start(header, False, False, 0)

        main = Gtk.Box(spacing=16)
        root.pack_start(main, True, True, 0)
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.connect('draw', self.draw)
        self.canvas.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.canvas.connect('motion-notify-event', self.on_pointer)
        self.canvas.connect('button-press-event', self.on_pointer)
        main.pack_start(self.canvas, True, True, 0)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11)
        panel.get_style_context().add_class('sidebar')
        panel.set_size_request(248, -1)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        side.set_border_width(12)
        panel.pack_start(side, True, True, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(100)
        scroll.set_propagate_natural_height(False)
        scroll.add(panel)
        main.pack_end(scroll, False, False, 0)
        side.pack_start(self.label('扫描控制', 'section'), False, False, 0)
        controls = Gtk.Box(spacing=8)
        self.start_button = Gtk.Button(label='开始')
        self.start_button.get_style_context().add_class('primary')
        self.start_button.connect('clicked', self.start)
        self.stop_button = Gtk.Button(label='停止')
        self.stop_button.get_style_context().add_class('stop')
        self.stop_button.connect('clicked', lambda *_: self.scanner.stop())
        controls.pack_start(self.start_button, True, True, 0)
        controls.pack_start(self.stop_button, False, False, 0)
        side.pack_start(controls, False, False, 0)
        self.pause = Gtk.ToggleButton(label='暂停画面')
        self.pause.set_tooltip_text('冻结当前画面以便观察；雷达继续采集。停止电机请点击“停止”。')
        self.pause.connect('toggled', self.on_pause)
        controls.pack_start(self.pause, False, False, 0)
        side.pack_start(Gtk.Separator(), False, False, 2)
        side.pack_start(self.label('最近有效距离', 'section'), False, False, 0)
        self.nearest = self.label('—  m', 'metric')
        side.pack_start(self.nearest, False, False, 0)
        self.points_label = self.label('有效点  —   /   本圈采样  —', 'muted')
        self.rate_label = self.label('扫描频率  — Hz', 'muted')
        side.pack_start(self.points_label, False, False, 0)
        side.pack_start(self.rate_label, False, False, 0)
        side.pack_start(Gtk.Separator(), False, False, 2)
        range_row = Gtk.Box(spacing=8)
        range_row.pack_start(self.label('显示半径'), True, True, 0)
        self.range_combo = Gtk.ComboBoxText()
        for radius in (1, 2, 4, 6, 12):
            self.range_combo.append(str(radius), f'{radius} m')
        self.range_combo.set_active_id('6')
        self.range_combo.connect('changed', self.on_range)
        range_row.pack_end(self.range_combo, False, False, 0)
        side.pack_start(range_row, False, False, 0)
        q_row = Gtk.Box(spacing=8)
        q_row.pack_start(self.label('最低质量 Q'), True, True, 0)
        self.q_spin = Gtk.SpinButton.new_with_range(1, 63, 1)
        self.q_spin.set_value(1)
        self.q_spin.set_tooltip_text('仅显示 Q 大于等于此值的有效点；Q 不是精度百分比。')
        self.q_spin.connect('value-changed', self.on_quality)
        q_row.pack_end(self.q_spin, False, False, 0)
        side.pack_start(q_row, False, False, 0)
        side.pack_start(Gtk.Separator(), False, False, 2)
        self.device_label = self.label(f'{args.device}  ·  460800', 'muted')
        self.health_label = self.label('健康 —   ·   固件 —', 'muted')
        side.pack_start(self.device_label, False, False, 0)
        side.pack_start(self.health_label, False, False, 0)
        self.canvas.set_tooltip_text('亮绿色表示较高质量；悬停或点选扫描点可查看角度、距离和 Q。')

        self.message = self.label('准备就绪，点击开始扫描', 'muted')
        self.message.set_line_wrap(True)
        self.message.set_max_width_chars(90)
        root.pack_start(self.message, False, False, 0)
        self.detail = self.label('角度 —   ·   距离 —   ·   质量 Q —', 'muted')
        root.pack_start(self.detail, False, False, 0)
        self.window.show_all()
        self.window.maximize()
        GLib.timeout_add(100, self.tick)
        if args.auto_start or args.verify:
            GLib.timeout_add(300, self.initial_start)

    @staticmethod
    def label(text, style=None):
        widget = Gtk.Label(label=text, xalign=0)
        if style:
            widget.get_style_context().add_class(style)
        return widget

    def initial_start(self):
        self.start_button.emit('clicked')
        return False

    def start(self, *_):
        self.pause.set_active(False)
        self.selected = None
        self.scanner.start()
        self.display = self.scanner.snapshot()

    def on_pause(self, button):
        self.paused = button.get_active()
        button.set_label('继续画面' if self.paused else '暂停画面')

    def on_range(self, combo):
        self.radius_mm = int(combo.get_active_id()) * 1000
        self.selected = None
        self.canvas.queue_draw()

    def on_quality(self, spin):
        self.minimum_quality = spin.get_value_as_int()
        self.selected = None
        self.canvas.queue_draw()

    def on_pointer(self, _widget, event):
        nearby = [(math.hypot(x - event.x, y - event.y), p) for x, y, p in self.hit_points]
        best = min(nearby, default=(99, None), key=lambda item: item[0])
        self.selected = best[1] if best[0] < 15 else None
        self.canvas.queue_draw()
        return True

    def on_key(self, _widget, event):
        if event.keyval == Gdk.KEY_space and not isinstance(self.window.get_focus(), Gtk.SpinButton):
            self.pause.set_active(not self.pause.get_active())
            return True
        return False

    def on_close(self, *_):
        if not self.closing:
            self.closing = True
            self.scanner.stop()
            self.start_button.set_sensitive(False)
        return True  # wait for the child's SIGINT cleanup before quitting GTK

    def visible_points(self):
        return [p for p in self.display.frame.points if p.quality >= self.minimum_quality]

    def tick(self):
        self.scanner.poll()
        current = self.scanner.snapshot()
        if not self.paused:
            self.display = current
        running = self.scanner.running
        self.start_button.set_sensitive(not running and not self.closing)
        self.stop_button.set_sensitive(running and current.state != 'stopping' and not self.closing)
        states = {'idle': '准备就绪', 'connecting': '正在连接', 'scanning': '实时扫描',
                  'stopping': '正在停止', 'stopped': '已停止', 'error': '连接异常'}
        self.status.set_text('●  ' + states.get(current.state, current.state) +
                             (' · 画面暂停' if self.paused else ''))
        if current.state == 'error':
            self.status.get_style_context().add_class('error')
        else:
            self.status.get_style_context().remove_class('error')
        points = self.visible_points()
        self.nearest.set_text(f'{min(p.distance for p in points) / 1000:.2f}  m' if points else '—  m')
        self.points_label.set_text(f'有效点  {len(points)}   /   本圈采样  {self.display.frame.samples}')
        self.rate_label.set_text(f'扫描频率  {current.hz:.1f} Hz' if running and current.hz else '扫描频率  — Hz')
        self.health_label.set_text(f'健康 {current.health}   ·   固件 {current.firmware}')
        message = current.message
        if not running and self.display.frames:
            message += ' · 当前保留最后一圈画面'
        elif self.paused:
            message += ' · 画面已冻结，雷达仍在采集'
        self.message.set_text(message)
        if self.selected:
            p = self.selected
            self.detail.set_text(f'角度 {p.angle:.2f}°   ·   距离 {p.distance / 1000:.3f} m   ·   质量 Q {p.quality}')
        else:
            self.detail.set_text('角度 —   ·   距离 —   ·   质量 Q —')
        self.canvas.queue_draw()

        if self.args.verify and not self.closing:
            if self.verify_phase == 0 and current.frames >= 12:
                self.verify_first = current.frames
                self.pause.set_active(True)
                self.range_combo.set_active_id('4')
                self.q_spin.set_value(10)
                self.stop_button.emit('clicked')
                self.verify_phase = 1
            elif self.verify_phase == 1 and not running:
                if current.state != 'stopped':
                    self.on_close()
                else:
                    self.start_button.emit('clicked')
                    self.verify_phase = 2
            elif self.verify_phase == 2 and current.frames >= 12:
                self.verify_restarted = current.frames
                self.verify_passed = bool(points and current.health == '正常')
                self.capture()
                self.on_close()
            if time.monotonic() - self.started_at > 35:
                self.on_close()
        if self.args.quit_after and time.monotonic() - self.started_at >= self.args.quit_after:
            self.capture()
            self.on_close()
        if self.closing and not running:
            if self.args.report:
                report = {
                    'state': current.state, 'frames': current.frames,
                    'valid_points': len(current.frame.points), 'health': current.health,
                    'firmware': current.firmware, 'child_stopped': not running,
                    'verify_passed': self.verify_passed and current.state == 'stopped',
                    'first_run_frames': self.verify_first, 'restarted_frames': self.verify_restarted,
                    'radius_mm': self.radius_mm, 'minimum_quality': self.minimum_quality,
                    'screenshot_saved': self.saved_screenshot,
                }
                Path(self.args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            Gtk.main_quit()
            return False
        return True

    def capture(self):
        if self.args.screenshot and not self.saved_screenshot:
            self.window.check_resize()
            width = self.window.get_allocated_width()
            height = self.window.get_allocated_height()
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            self.window.draw(cairo.Context(surface))
            surface.write_to_png(self.args.screenshot)
            self.saved_screenshot = True

    @staticmethod
    def text(cr, x, y, text, size=11, color=(.51, .64, .71), center=False):
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription(f'Sans {size}'))
        layout.set_text(text, -1)
        w, _ = layout.get_pixel_size()
        cr.set_source_rgb(*color)
        cr.move_to(x - w / 2 if center else x, y)
        PangoCairo.show_layout(cr, layout)

    def draw(self, widget, cr):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        cx, cy = width / 2, height / 2
        radius = max(30, min(width, height) / 2 - 32)
        cr.set_source_rgb(.041, .076, .103)
        cr.paint()
        cr.set_line_width(1)
        for ring in range(1, 5):
            r = radius * ring / 4
            cr.set_source_rgb(.12, .21, .26)
            cr.arc(cx, cy, r, 0, math.tau)
            cr.stroke()
            self.text(cr, cx + 7, cy - r + 4, f'{self.radius_mm * ring / 4000:g} m', 9)
        for angle in range(0, 360, 45):
            a = math.radians(angle)
            cr.set_source_rgb(.10, .17, .22)
            cr.move_to(cx, cy)
            cr.line_to(cx + math.sin(a) * radius, cy - math.cos(a) * radius)
            cr.stroke()
            self.text(cr, cx + math.sin(a) * (radius + 19),
                      cy - math.cos(a) * (radius + 19) - 7, f'{angle}°', 9, center=True)
        self.hit_points = []
        for point in self.visible_points():
            if point.distance > self.radius_mm:
                continue
            a = math.radians(point.angle)
            r = point.distance / self.radius_mm * radius
            x, y = cx + math.sin(a) * r, cy - math.cos(a) * r
            brightness = min(point.quality / 47, 1)
            cr.set_source_rgb(.20 + .12 * brightness, .45 + .44 * brightness, .43 + .30 * brightness)
            cr.arc(x, y, 2.1, 0, math.tau)
            cr.fill()
            self.hit_points.append((x, y, point))
            if point == self.selected:
                cr.set_source_rgb(1, .75, .35)
                cr.arc(x, y, 7, 0, math.tau)
                cr.stroke()
        cr.set_source_rgb(.94, .74, .36)
        cr.move_to(cx, cy - 6)
        cr.line_to(cx - 4, cy + 4)
        cr.line_to(cx + 4, cy + 4)
        cr.close_path()
        cr.fill()
        if not self.display.frames:
            self.text(cr, cx, cy + 25, '点击“开始扫描”查看周围环境', 12, center=True)
        self.text(cr, 12, 12, '0° 在上方 · 角度顺时针增加', 9)
        if self.paused:
            self.text(cr, 12, height - 26, '画面已暂停', 10, (1, .75, .35))
        elif not self.scanner.running and self.display.frames:
            self.text(cr, 12, height - 26, '已停止 · 保留最后一圈', 10, (1, .75, .35))
        return False


def main():
    parser = argparse.ArgumentParser(description='RPLIDAR C1 native GTK viewer')
    parser.add_argument('--device', default='/dev/ttyUSB0')
    parser.add_argument('--binary', default='/usr/local/bin/rplidar-ultra-simple')
    parser.add_argument('--auto-start', action='store_true')
    parser.add_argument('--verify', action='store_true', help='run board UI start/stop/restart verification')
    parser.add_argument('--quit-after', type=float, default=0)
    parser.add_argument('--screenshot')
    parser.add_argument('--report')
    args = parser.parse_args()
    with open('/tmp/rplidar-ui.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(1, '雷达界面已经运行，请切换到现有窗口。\n')
        viewer = Viewer(args)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: viewer.on_close())
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: viewer.on_close())
        Gtk.main()
        return 0 if not args.verify or viewer.verify_passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
