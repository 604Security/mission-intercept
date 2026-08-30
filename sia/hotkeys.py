"""Non-blocking hotkey handling.

Primary backend is ``pynput`` (per the mission spec) running in a daemon
thread. If pynput cannot initialise — common on headless/SSH sessions with no
X display — we transparently fall back to a raw-mode stdin reader so the app
stays usable. Either way the same callbacks fire:

    r / R    -> on_record
    q / Q    -> on_quit
    h / H    -> on_help
    + / =    -> on_volume_up
    - / _    -> on_volume_down
"""

import sys
import threading


class HotkeyListener:
    def __init__(self, on_record, on_quit, on_help,
                 on_volume_up=None, on_volume_down=None):
        self.on_record = on_record
        self.on_quit = on_quit
        self.on_help = on_help
        self.on_volume_up = on_volume_up or (lambda: None)
        self.on_volume_down = on_volume_down or (lambda: None)
        self._listener = None        # pynput listener, if used
        self._thread = None          # stdin fallback thread, if used
        self._stop = threading.Event()
        self.backend = None          # "pynput" or "stdin"

    def start(self):
        if self._start_pynput():
            self.backend = "pynput"
        else:
            self._start_stdin()
            self.backend = "stdin"
        return self.backend

    # ----- pynput backend --------------------------------------------------
    def _start_pynput(self):
        try:
            from pynput import keyboard
        except Exception:  # noqa: BLE001 — import may fail without a backend
            return False

        def on_press(key):
            try:
                char = key.char.lower() if key.char else None
            except AttributeError:
                char = None
            self._dispatch(char)

        try:
            self._listener = keyboard.Listener(on_press=on_press)
            self._listener.daemon = True
            self._listener.start()
        except Exception:  # noqa: BLE001 — e.g. no X display
            self._listener = None
            return False
        return True

    # ----- stdin fallback backend -----------------------------------------
    def _start_stdin(self):
        self._thread = threading.Thread(target=self._stdin_loop, daemon=True)
        self._thread.start()

    def _stdin_loop(self):
        try:
            import termios
            import tty
        except ImportError:
            return
        if not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            import select
            while not self._stop.is_set():
                if select.select([sys.stdin], [], [], 0.2)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "\x03":          # Ctrl+C
                        self.on_quit()
                        break
                    self._dispatch(ch.lower())
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # ----- shared dispatch -------------------------------------------------
    def _dispatch(self, char):
        if char == "r":
            self.on_record()
        elif char == "q":
            self.on_quit()
        elif char == "h":
            self.on_help()
        elif char in ("+", "="):     # '=' is '+' without Shift
            self.on_volume_up()
        elif char in ("-", "_"):
            self.on_volume_down()

    def stop(self):
        self._stop.set()
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # noqa: BLE001
                pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
