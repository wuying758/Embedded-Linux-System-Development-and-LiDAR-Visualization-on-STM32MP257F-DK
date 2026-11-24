from pathlib import Path
import tempfile
import time
import unittest

from scan_model import FrameAssembler, Scanner


class FrameTests(unittest.TestCase):
    def test_frames_align_at_sync_and_filter_invalid_returns(self):
        parser = FrameAssembler()
        self.assertIsNone(parser.feed(' theta: 359.1 Dist: 1000 Q: 47'))
        parser.feed('S  theta: 0.2 Dist: 554.00 Q: 47')
        parser.feed('   theta: 1.2 Dist: 0.00 Q: 0')
        parser.feed('   theta: 2.2 Dist: 300.00 Q: 0')
        parser.feed('   theta: 359.5 Dist: 620.00 Q: 12')
        frame = parser.feed('S  theta: 0.1 Dist: 555.00 Q: 47')
        self.assertEqual(frame.samples, 4)
        self.assertEqual([(p.angle, p.distance) for p in frame.points], [(0.2, 554), (359.5, 620)])
        self.assertEqual(parser.samples, 1)

    def test_malformed_lines_and_missing_sync_are_bounded(self):
        parser = FrameAssembler()
        for line in ('Version: 2.1.0', ' theta: 360 Dist: 2 Q: 4',
                     'S theta: 0..2 Dist: 20 Q: 47', ' theta: 0 Dist: 20 Q: 255'):
            self.assertIsNone(parser.feed(line))
        parser.feed('S theta: 0 Dist: 20 Q: 47')
        for _ in range(17000):
            parser.feed(' theta: 1 Dist: 20 Q: 47')
        self.assertFalse(parser.synced)
        self.assertEqual(parser.points, [])

    def test_real_saved_scan(self):
        parser = FrameAssembler()
        frames = []
        source = Path(__file__).resolve().parents[1] / 'scan-verification.log'
        with source.open() as stream:
            for line in stream:
                frame = parser.feed(line)
                if frame is not None:
                    frames.append(frame)
        self.assertEqual(len(frames), 122)
        self.assertTrue(all(frame.samples > 100 for frame in frames))
        self.assertGreater(sum(len(frame.points) for frame in frames), 47000)

    def test_extra_sync_marker_at_end_of_sorted_scan(self):
        parser = FrameAssembler()
        parser.feed('S theta: 0 Dist: 554 Q: 47')
        parser.feed(' theta: 180 Dist: 600 Q: 47')
        self.assertIsNone(parser.feed('S theta: 359.4 Dist: 548 Q: 47'))
        frame = parser.feed('S theta: 0 Dist: 560 Q: 47')
        self.assertEqual(frame.samples, 3)
        self.assertEqual(frame.points[-1].angle, 359.4)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.device = self.root / 'port'
        self.device.touch()

    def tearDown(self):
        self.tmp.cleanup()

    def wait_for(self, predicate, scanner, seconds=4):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            scanner.poll()
            if predicate():
                return
            time.sleep(.02)
        self.fail(f'Timed out: {scanner.snapshot()}')

    def fake(self, source):
        program = self.root / 'fake-scanner'
        program.write_text('#!/usr/bin/python3\n' + source)
        program.chmod(0o755)
        return Scanner(str(self.device), str(program))

    def test_start_stop_restart_and_cleanup_signal(self):
        marker = self.root / 'stopped'
        scanner = self.fake(f'''
import signal, time
from pathlib import Path
running = True
def stop(*args):
    global running
    running = False
signal.signal(signal.SIGINT, stop)
print('Firmware Ver: 1.02', flush=True)
print('SLAMTEC Lidar health status : 0', flush=True)
while running:
    print('S theta: 0.2 Dist: 554.00 Q: 47', flush=True)
    print(' theta: 180.2 Dist: 650.00 Q: 20', flush=True)
    time.sleep(.04)
Path({str(marker)!r}).write_text('motor-stop')
''')
        try:
            for _ in range(2):
                self.assertTrue(scanner.start())
                self.assertFalse(scanner.start())
                self.wait_for(lambda: scanner.snapshot().frames >= 3, scanner)
                self.assertEqual(scanner.snapshot().health, '正常')
                self.assertEqual(scanner.snapshot().firmware, '1.02')
                scanner.stop()
                self.wait_for(lambda: not scanner.running, scanner)
                self.assertEqual(scanner.snapshot().state, 'stopped')
                self.assertEqual(marker.read_text(), 'motor-stop')
        finally:
            scanner.stop()
            if scanner._thread:
                scanner._thread.join(3)

    def test_official_demo_zero_exit_with_error_is_not_success(self):
        scanner = self.fake("print('Error, cannot bind to the specified serial port /dev/ttyUSB0.')\n")
        scanner.start()
        self.wait_for(lambda: not scanner.running, scanner)
        self.assertEqual(scanner.snapshot().state, 'error')

    def test_stalled_stream_stops_and_preserves_connection_error(self):
        scanner = self.fake('''
import signal, time
running = True
def stop(*args):
    global running
    running = False
signal.signal(signal.SIGINT, stop)
for _ in range(3):
    print('S theta: 0.2 Dist: 554 Q: 47', flush=True)
    print(' theta: 180.2 Dist: 650 Q: 47', flush=True)
while running:
    time.sleep(.02)
''')
        try:
            scanner.start()
            self.wait_for(lambda: scanner.snapshot().frames >= 2, scanner)
            scanner._update(last_frame_at=time.monotonic() - 9)
            scanner.poll()
            self.wait_for(lambda: not scanner.running, scanner)
            self.assertEqual(scanner.snapshot().state, 'error')
            self.assertIn('未收到扫描数据', scanner.snapshot().message)
        finally:
            scanner.stop()
            if scanner._thread:
                scanner._thread.join(3)

    def test_missing_and_busy_device(self):
        scanner = Scanner(str(self.root / 'missing'))
        self.assertFalse(scanner.start())
        self.assertIn('未找到', scanner.snapshot().message)
        with self.device.open():
            # port_owner deliberately excludes this process; use another process.
            import subprocess
            holder = subprocess.Popen(['/usr/bin/python3', '-c',
                'import sys,time; f=open(sys.argv[1]); print("ready",flush=True); time.sleep(5)',
                str(self.device)], stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(holder.stdout.readline().strip(), 'ready')
                scanner = Scanner(str(self.device))
                self.assertFalse(scanner.start())
                self.assertIn('占用', scanner.snapshot().message)
            finally:
                holder.terminate()
                holder.wait()
                holder.stdout.close()


if __name__ == '__main__':
    unittest.main()
