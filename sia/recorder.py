"""Recording: tee raw PCM to disk, then convert to WAV on stop.

The reader thread in :mod:`sia.radio` calls :meth:`Recorder.write` for every
chunk while recording is active; the hotkey thread calls :meth:`Recorder.toggle`.
A lock guards the file handle so a toggle never races an in-flight write.
"""

import threading
import time
import wave
from datetime import datetime
from pathlib import Path

from . import config


class Recorder:
    def __init__(self, output_dir, status, sample_rate=config.SAMPLE_RATE):
        self.output_dir = Path(output_dir)
        self.status = status
        self.sample_rate = sample_rate

        self._lock = threading.Lock()
        self._raw_file = None
        self._raw_path = None
        self.is_recording = False
        self._start_ts = None
        self._bytes_written = 0
        self.last_saved = None

    # ----- toggle ----------------------------------------------------------
    def toggle(self):
        """Flip recording on/off. Returns the new ``is_recording`` state."""
        if self.is_recording:
            self.stop()
        else:
            self.start()
        return self.is_recording

    def start(self):
        with self._lock:
            if self.is_recording:
                return
            self.output_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            name = f"{config.RECORDING_PREFIX}_{stamp}.raw"
            self._raw_path = self.output_dir / name
            # Never clobber an existing capture.
            counter = 1
            while self._raw_path.exists():
                name = f"{config.RECORDING_PREFIX}_{stamp}_{counter}.raw"
                self._raw_path = self.output_dir / name
                counter += 1
            self._raw_file = open(self._raw_path, "wb")
            self._bytes_written = 0
            self._start_ts = time.monotonic()
            self.is_recording = True
        self.status.info(f"Recording initiated — {self._raw_path.name}")

    def write(self, chunk):
        """Append a raw PCM chunk. Safe to call from the reader thread."""
        with self._lock:
            if self.is_recording and self._raw_file is not None:
                try:
                    self._raw_file.write(chunk)
                    self._bytes_written += len(chunk)
                except (ValueError, OSError):
                    pass

    def stop(self):
        with self._lock:
            if not self.is_recording:
                return None
            self.is_recording = False
            raw_path = self._raw_path
            try:
                self._raw_file.flush()
                self._raw_file.close()
            except (ValueError, OSError):
                pass
            self._raw_file = None
            self._start_ts = None

        self.status.info("Recording stopped by agent.")
        self.status.success("Converting raw PCM to WAV...")
        wav_path = raw_path.with_suffix(".wav")
        try:
            self._raw_to_wav(raw_path, wav_path)
            raw_path.unlink(missing_ok=True)
            size = self._human_size(wav_path.stat().st_size)
            self.last_saved = wav_path
            self.status.success(f"Recording saved: {wav_path.name} ({size})")
        except Exception as exc:  # noqa: BLE001
            self.status.alert(f"WAV conversion failed: {exc}. Raw kept at {raw_path.name}")
            return raw_path
        return wav_path

    def _raw_to_wav(self, raw_path, wav_path):
        with open(raw_path, "rb") as raw_file:
            raw_data = raw_file.read()
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)            # 16-bit -> 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(raw_data)

    # ----- helpers ---------------------------------------------------------
    def elapsed(self):
        """Seconds since recording began (0 if not recording)."""
        if self._start_ts is None:
            return 0
        return time.monotonic() - self._start_ts

    def elapsed_str(self):
        secs = int(self.elapsed())
        return f"{secs // 60:02d}:{secs % 60:02d}"

    @property
    def current_name(self):
        return self._raw_path.name if self._raw_path else ""

    @staticmethod
    def _human_size(num_bytes):
        size = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return f"{size:.1f} GB"
