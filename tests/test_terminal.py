"""Exercise real curses initialization, key delivery, and terminal restoration."""

import fcntl
import json
import os
import pty
from pathlib import Path
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest


class TerminalTests(unittest.TestCase):
    def test_interactive_session(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 100, 0, 0))
        original = termios.tcgetattr(slave)
        with tempfile.TemporaryDirectory() as data:
            process = subprocess.Popen(
                [sys.executable, "-m", "vimtype", "--data-dir", data],
                stdin=slave, stdout=slave, stderr=slave,
                env=dict(os.environ, TERM="xterm-256color"),
            )
            def cleanup():
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)

            self.addCleanup(cleanup)
            output = bytearray()

            def expect(marker):
                deadline = time.monotonic() + 5
                while marker not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        output.extend(os.read(master, 65536))
                self.assertIn(marker, output, output.decode(errors="replace"))

            def send(keys):
                output.clear()
                os.write(master, keys)

            expect(b"vimtype")
            send(b"s")
            expect(b"test mode")
            send(b":words 10\n")
            expect(b"Settings updated")
            send(b":pool english_5k\n")
            expect(b"Settings updated")
            self.assertEqual(json.loads((Path(data) / "settings.json").read_text())["pool"], "english_5k")
            send(b"i")
            expect(b"INSERT")
            send(b"hjkl")
            expect(b"h")
            send(b"\x1b")
            expect(b"Test aborted")
            send(b"H")
            expect(b"history / 0 tests")
            send(b"?")
            expect(b"GETTING AROUND")
            send(b"i")
            expect(b"INSERT")
            send(b"x " * 10 + b"i\tq\n")
            expect(b"TEST COMPLETE")
            expect(b"WPM trend")
            expect(b"latest:")
            self.assertTrue(any(0x2800 <= ord(c) <= 0x28ff for c in output.decode(errors="replace")), repr(output))
            send(b":graph\n")
            expect(b":results returns")
            send(b":results\n")
            expect(b"Previous scores")
            send(b"i\tq\n:invalid\n")
            expect(b"Unknown command")
            self.assertIsNone(process.poll())
            self.assertEqual(len(json.loads((Path(data) / "history.json").read_text())), 1)
            send(b":q\n")
            deadline = time.monotonic() + 5
            while process.poll() is None and time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    output.extend(os.read(master, 65536))
            self.assertEqual(process.wait(timeout=5), 0)
            restored = termios.tcgetattr(slave)
            # Python/macOS may set NOKERNINFO at startup; verify the user-facing
            # input, output, echo, signal and canonical-mode settings.
            self.assertEqual(restored[:3], original[:3])
            modes = termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN
            self.assertEqual(restored[3] & modes, original[3] & modes)
            self.assertEqual(restored[4:], original[4:])

    def test_noninteractive_run_is_actionable(self):
        process = subprocess.run([sys.executable, "-m", "vimtype"], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertIn("interactive terminal", process.stderr)
