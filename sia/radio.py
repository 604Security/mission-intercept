"""RTL-SDR backend: rtl_fm -> aplay pipeline with a recording tee.

The reader thread pulls raw 16-bit PCM chunks from ``rtl_fm``'s stdout, writes
them to ``aplay``'s stdin for live monitoring, optionally tees them to an active
recorder, and derives a cosmetic signal level for the UI.
"""

import array
import subprocess
import threading
import time

from . import config

# Software volume scaler. audioop.mul is a fast C routine that multiplies every
# 16-bit sample and clamps on overflow; it is deprecated and removed in Python
# 3.13, so fall back to a pure-stdlib array multiply when it is unavailable.
try:
    import audioop

    def _scale(chunk, factor):
        return audioop.mul(chunk, 2, factor)
except ImportError:  # Python 3.13+
    def _scale(chunk, factor):
        n = len(chunk) - (len(chunk) % 2)
        samples = array.array("h")
        samples.frombytes(chunk[:n])
        for i in range(len(samples)):
            v = int(samples[i] * factor)
            samples[i] = 32767 if v > 32767 else -32768 if v < -32768 else v
        return samples.tobytes() + chunk[n:]


class Radio:
    def __init__(self, frequency, gain, squelch, status,
                 volume=config.DEFAULT_VOLUME,
                 sample_rate=config.SAMPLE_RATE, chunk_size=config.CHUNK_SIZE):
        self.frequency = float(frequency)
        self.gain = int(gain)
        self.squelch = int(squelch)
        self.status = status
        self.volume = float(volume)
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        self.rtl_proc = None
        self.aplay_proc = None
        self._reader = None
        self._stop = threading.Event()

        # Shared state for the UI / recorder (guarded by _lock).
        self._lock = threading.Lock()
        self._signal_level = 0.0      # smoothed 0.0 - 1.0
        self._signal_active = False
        self.recorder = None          # set by the app; tee target
        self._restarted = False
        self.crashed = False

    # ----- command construction -------------------------------------------
    def _rtl_cmd(self):
        return [
            "rtl_fm",
            "-f", f"{self.frequency}M",
            "-M", "fm",
            "-s", config.CAPTURE_RATE,
            "-r", str(self.sample_rate),
            "-g", str(self.gain),
            "-l", str(self.squelch),
        ]

    def _aplay_cmd(self):
        return [
            "aplay",
            "-r", str(self.sample_rate),
            "-f", "S16_LE",
            "-t", "raw",
            "-c", "1",
        ]

    # ----- lifecycle -------------------------------------------------------
    def start(self):
        """Launch the subprocess pipeline and the reader thread."""
        self._stop.clear()
        self.crashed = False
        self._spawn_processes()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    def _spawn_processes(self):
        self.rtl_proc = subprocess.Popen(
            self._rtl_cmd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self.aplay_proc = subprocess.Popen(
            self._aplay_cmd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

    def stop(self):
        """Signal the reader to stop and tear down both subprocesses."""
        self._stop.set()
        if self._reader and self._reader.is_alive():
            self._reader.join(timeout=2)
        self._terminate_processes()

    def _terminate_processes(self):
        for proc in (self.rtl_proc, self.aplay_proc):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        self.rtl_proc = None
        self.aplay_proc = None

    # ----- core pump loop --------------------------------------------------
    def _pump(self):
        while not self._stop.is_set():
            if self.rtl_proc is None or self.rtl_proc.stdout is None:
                break
            try:
                chunk = self.rtl_proc.stdout.read(self.chunk_size)
            except (ValueError, OSError):
                break

            if not chunk:
                # rtl_fm died or EOF — try a single restart, then give up.
                if self._stop.is_set():
                    break
                if self._handle_crash():
                    continue
                break

            # Meter the raw RF so the signal bar reflects actual signal
            # strength, not the software volume setting.
            self._update_signal(chunk)

            vol = self.volume
            out = chunk if vol == 1.0 else _scale(chunk, vol)

            if self.aplay_proc and self.aplay_proc.stdin:
                try:
                    self.aplay_proc.stdin.write(out)
                except (BrokenPipeError, ValueError, OSError):
                    pass

            rec = self.recorder
            if rec is not None and rec.is_recording:
                rec.write(out)

    def _handle_crash(self):
        """Attempt exactly one restart of the pipeline after a crash."""
        if self._restarted:
            self.crashed = True
            self.status.alert("RTL-FM process crashed — restart already attempted. Aborting.")
            return False
        self._restarted = True
        self.status.alert("RTL-FM process crashed — attempting one restart...")
        self._terminate_processes()
        time.sleep(0.5)
        try:
            self._spawn_processes()
        except Exception as exc:  # noqa: BLE001
            self.crashed = True
            self.status.alert(f"Restart failed: {exc}")
            return False
        self.status.success("SDR uplink re-established.")
        return True

    # ----- volume ----------------------------------------------------------
    def volume_up(self):
        """Raise the software volume by one step. Returns the new multiplier."""
        self.volume = min(config.VOLUME_MAX, self.volume + config.VOLUME_STEP)
        return self.volume

    def volume_down(self):
        """Lower the software volume by one step. Returns the new multiplier."""
        self.volume = max(config.VOLUME_MIN, self.volume - config.VOLUME_STEP)
        return self.volume

    # ----- signal metering -------------------------------------------------
    def _update_signal(self, chunk):
        n = len(chunk) - (len(chunk) % 2)
        if n <= 0:
            return
        samples = array.array("h")
        samples.frombytes(chunk[:n])
        if not samples:
            return
        mean_abs = sum(abs(s) for s in samples) / len(samples)
        level = min(1.0, mean_abs / 3000.0)
        with self._lock:
            # Exponential smoothing so the bar doesn't jitter wildly.
            self._signal_level = 0.6 * self._signal_level + 0.4 * level
            self._signal_active = mean_abs > config.SIGNAL_THRESHOLD

    @property
    def signal_level(self):
        with self._lock:
            return self._signal_level

    @property
    def signal_active(self):
        with self._lock:
            return self._signal_active

    def signal_bar(self, width=16):
        """Return (markup_string, label) for the cosmetic signal meter."""
        level = self.signal_level
        active = self.signal_active
        filled = int(round(level * width))
        bar = "█" * filled + "░" * (width - filled)
        if not active:
            label, color = "SILENT", "dim white"
        elif level > 0.66:
            label, color = "STRONG", "bright_green"
        elif level > 0.33:
            label, color = "MEDIUM", "yellow"
        else:
            label, color = "WEAK", "bright_red"
        return f"[{color}]{bar}[/]  [{color}]{label}[/]"

    @property
    def alive(self):
        return self.rtl_proc is not None and self.rtl_proc.poll() is None
