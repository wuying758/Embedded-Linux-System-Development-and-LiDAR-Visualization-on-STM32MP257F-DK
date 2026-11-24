"""Bounded scan frames and lifecycle control for the official SLAMTEC demo."""

from dataclasses import dataclass, replace
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time


@dataclass(frozen=True)
class Point:
    angle: float
    distance: float  # millimetres
    quality: int


@dataclass(frozen=True)
class Frame:
    points: tuple = ()
    samples: int = 0


class FrameAssembler:
    pattern = re.compile(
        r"^\s*(S)?\s*theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)\s+Q:\s*(\d+)\s*$"
    )

    def __init__(self):
        self.synced = False
        self.points = []
        self.samples = 0
        self.last_angle = None

    def feed(self, line):
        match = self.pattern.match(line)
        if not match:
            return None
        try:
            angle, distance = float(match[2]), float(match[3])
            quality = int(match[4])
        except ValueError:
            return None
        if not (math.isfinite(angle) and 0 <= angle < 360
                and math.isfinite(distance) and distance >= 0 and 0 <= quality <= 63):
            return None
        finished = None
        # ultra_simple prints ascendScanData() in angle order. The original S
        # flag can also occur near 359 degrees, immediately before S at zero.
        # Use the angular wrap so that marker never creates a one-point frame.
        wrap = self.last_angle is not None and self.last_angle - angle > 90
        if wrap or (not self.synced and match[1] and angle < 90):
            if self.synced:
                finished = Frame(tuple(self.points), self.samples)
            self.synced = True
            self.points = []
            self.samples = 0
        self.last_angle = angle
        if self.synced:
            self.samples += 1
            if distance > 0 and quality > 0:
                self.points.append(Point(angle, distance, quality))
            # A missing synchronization marker must never grow memory indefinitely.
            if self.samples > 16384:
                self.synced = False
                self.points = []
                self.samples = 0
        return finished


def port_owner(device):
    """Catch an existing CLI reader before opening the same serial port."""
    target = os.path.realpath(device)
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            for descriptor in (process / 'fd').iterdir():
                try:
                    if os.readlink(descriptor) == target:
                        return process.name
                except OSError:
                    pass
        except OSError:
            pass
    return None


@dataclass(frozen=True)
class Snapshot:
    state: str = 'idle'
    message: str = '准备就绪，点击开始扫描'
    frame: Frame = Frame()
    frames: int = 0
    hz: float = 0.0
    last_frame_at: float = 0.0
    firmware: str = '—'
    health: str = '—'


class Scanner:
    def __init__(self, device='/dev/ttyUSB0', binary='/usr/local/bin/rplidar-ultra-simple'):
        self.device = device
        self.binary = binary
        self._lock = threading.Lock()
        self._snapshot = Snapshot()
        self._thread = None
        self._process = None
        self._stop = threading.Event()
        self._started_at = 0.0
        self._stop_at = 0.0

    def snapshot(self):
        with self._lock:
            return self._snapshot

    def _update(self, **values):
        with self._lock:
            self._snapshot = replace(self._snapshot, **values)

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return False
        if not Path(self.device).exists():
            self._update(state='error', message=f'未找到 {self.device}，请检查雷达 USB 连接')
            return False
        owner = port_owner(self.device)
        if owner:
            self._update(state='error', message=f'串口被进程 {owner} 占用，请先停止命令行扫描')
            return False
        self._stop.clear()
        self._stop_at = 0
        self._started_at = time.monotonic()
        with self._lock:
            self._snapshot = Snapshot(state='connecting', message='正在连接雷达…')
        self._thread = threading.Thread(target=self._read, name='lidar-reader', daemon=True)
        self._thread.start()
        return True

    def stop(self):
        if not self.running or self._stop.is_set():
            return
        self._stop.set()
        self._stop_at = time.monotonic()
        if self.snapshot().state != 'error':
            self._update(state='stopping', message='正在停止扫描和电机…')
        with self._lock:
            process = self._process
        if process and process.poll() is None:
            try:
                process.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass

    def poll(self):
        """Called by the GUI timer, including when the serial reader is blocked."""
        now = time.monotonic()
        state = self.snapshot()
        if self.running and not self._stop.is_set():
            last = state.last_frame_at or self._started_at
            if now - last > 8:
                self._update(state='error', message='未收到扫描数据，请检查 USB 连接和供电后重试')
                self.stop()
        if self.running and self._stop_at and now - self._stop_at > 6:
            with self._lock:
                process = self._process
            if process and process.poll() is None:
                process.kill()
                self._update(state='error', message='停止超时，程序已结束；请重新插拔雷达以确认电机停止')

    def _read(self):
        assembler = FrameAssembler()
        error = None
        process = None
        try:
            process = subprocess.Popen(
                ['stdbuf', '-oL', self.binary, '--channel', '--serial', self.device, '460800'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1,
                start_new_session=True,
            )
            with self._lock:
                self._process = process
            if self._stop.is_set():
                process.send_signal(signal.SIGINT)
            for line in process.stdout:
                if 'Error,' in line or 'error detected' in line or 'insufficent memory' in line:
                    error = '雷达连接失败，请检查串口占用、USB 连接及供电'
                if line.startswith('Firmware Ver:'):
                    self._update(firmware=line.split(':', 1)[1].strip())
                if 'health status :' in line:
                    code = line.rsplit(':', 1)[1].strip()
                    self._update(health={'0': '正常', '1': '警告', '2': '故障'}.get(code, code))
                frame = assembler.feed(line)
                if frame is not None:
                    now = time.monotonic()
                    previous = self.snapshot()
                    elapsed = now - previous.last_frame_at
                    hz = previous.hz
                    if previous.last_frame_at and elapsed > 0:
                        measured = 1 / elapsed
                        hz = measured if not hz else hz * .8 + measured * .2
                    self._update(
                        frame=frame, frames=previous.frames + 1, hz=hz, last_frame_at=now,
                        **({} if self._stop.is_set() else
                           {'state': 'scanning', 'message': '实时扫描中'}),
                    )
            code = process.wait()
            if not self._stop.is_set():
                error = error or f'扫描程序已退出（{code}），请检查连接后重新开始'
        except (OSError, subprocess.SubprocessError) as exc:
            error = f'无法启动扫描程序：{exc}'
        finally:
            if process:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                if process.stdout:
                    process.stdout.close()
            with self._lock:
                self._process = None
            if error:
                self._update(state='error', message=error)
            elif self.snapshot().state != 'error':
                self._update(state='stopped', message='已停止，电机已发送停止指令')
