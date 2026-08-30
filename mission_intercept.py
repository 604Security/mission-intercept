#!/usr/bin/env python3
"""Mission Intercept — SIA RTL-SDR FRS channel monitor (entry point).

Thin orchestration only: parse args, run dependency checks, play the boot
sequence, then hand off to the live session loop. All real work lives in the
``sia`` package.
"""

import argparse
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from sia import config


# ----------------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------------
def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="mission_intercept.py",
        add_help=False,
        description="SIA Mission Intercept — FRS/GMRS channel monitor.",
    )
    parser.add_argument("-a", "--agent", default=config.DEFAULT_AGENT)
    parser.add_argument("-g", "--gain", type=int, default=config.DEFAULT_GAIN)
    parser.add_argument("-s", "--squelch", type=int, default=config.DEFAULT_SQUELCH)
    parser.add_argument("-o", "--output", default=config.DEFAULT_OUTPUT)
    parser.add_argument("-f", "--freq", type=float, default=config.DEFAULT_FREQ)
    parser.add_argument("-c", "--channel", type=int, default=None)
    parser.add_argument("-V", "--volume", type=float, default=config.DEFAULT_VOLUME)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    return parser.parse_args(argv)


# ----------------------------------------------------------------------------
# Dependency + hardware checks
# ----------------------------------------------------------------------------
def check_binaries(status):
    ok = True
    for binary in ("rtl_fm", "aplay"):
        status.info(f"Checking for {binary} binary...")
        path = shutil.which(binary)
        if path:
            status.success(f"{binary} found at {path}")
        else:
            status.alert(
                f"MISSION ABORT: {binary} not found. "
                f"Install the relevant package first, Agent."
            )
            ok = False
    return ok


def detect_device(status):
    """Probe for an RTL-SDR dongle via rtl_test. Returns (found, serial)."""
    status.info("Scanning for RTL-SDR hardware...")
    if shutil.which("rtl_test") is None:
        # No rtl_test; assume present and let rtl_fm surface any failure.
        status.standby("rtl_test unavailable — skipping hardware probe.")
        return True, None
    try:
        proc = subprocess.Popen(
            ["rtl_test", "-t"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            out, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                out, _ = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate()
    except Exception as exc:  # noqa: BLE001
        status.alert(f"Hardware probe failed: {exc}")
        return False, None

    if "No supported devices" in out or "usb_open error" in out:
        status.alert("MISSION ABORT: No RTL-SDR dongle detected. Plug me in, Agent.")
        return False, None

    serial = None
    m = re.search(r"SN:\s*(\S+)", out)
    if m:
        serial = m.group(1)
    found = "Found" in out or "Realtek" in out or "tuner" in out.lower()
    if found:
        suffix = f" Serial: {serial}" if serial else ""
        status.success(f"RTL-SDR detected.{suffix}")
        return True, serial
    status.alert("MISSION ABORT: No RTL-SDR dongle detected. Plug me in, Agent.")
    return False, None


def resolve_output_dir(path_str, status):
    """Ensure the output directory is writable; fall back to /tmp."""
    path = Path(path_str)
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".sia_write_test"
        probe.touch()
        probe.unlink()
        return path
    except OSError:
        fallback = Path("/tmp/sia_recordings")
        status.alert(f"Output dir '{path}' not writable — falling back to {fallback}")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def validate_and_clamp(args, status):
    """Resolve channel/freq and clamp gain. Returns (freq, channel) or exits."""
    channel = None
    freq = args.freq
    if args.channel is not None:
        if args.channel not in config.FRS_CHANNELS:
            valid = ", ".join(str(c) for c in sorted(config.FRS_CHANNELS))
            status.alert(f"Invalid channel {args.channel}. Valid FRS channels: {valid}")
            sys.exit(1)
        channel = args.channel
        freq = config.FRS_CHANNELS[channel]
    else:
        channel = config.channel_for_freq(freq)

    if not (config.GAIN_MIN <= args.gain <= config.GAIN_MAX):
        clamped = max(config.GAIN_MIN, min(config.GAIN_MAX, args.gain))
        status.alert(f"Gain {args.gain} out of range — clamping to {clamped} dB.")
        args.gain = clamped

    if not (config.VOLUME_MIN <= args.volume <= config.VOLUME_MAX):
        clamped = max(config.VOLUME_MIN, min(config.VOLUME_MAX, args.volume))
        status.alert(f"Volume {args.volume} out of range — clamping to {clamped:g}x.")
        args.volume = clamped

    return freq, channel


# ----------------------------------------------------------------------------
# Live session
# ----------------------------------------------------------------------------
def run_session(args, freq, channel, status):
    from rich.live import Live
    from sia import banner
    from sia.radio import Radio
    from sia.recorder import Recorder
    from sia.hotkeys import HotkeyListener

    recorder = Recorder(args.output, status)
    radio = Radio(freq, args.gain, args.squelch, status, volume=args.volume)
    radio.recorder = recorder

    quit_event = threading.Event()
    help_state = {"visible": False}

    def on_record():
        recorder.toggle()

    def on_quit():
        quit_event.set()

    def on_help():
        help_state["visible"] = not help_state["visible"]

    def on_volume_up():
        vol = radio.volume_up()
        status.info(f"Volume: {int(vol * 100)}%")

    def on_volume_down():
        vol = radio.volume_down()
        status.info(f"Volume: {int(vol * 100)}%")

    # Ctrl+C -> graceful quit (Section 11).
    def handle_sigint(signum, frame):
        quit_event.set()
    signal.signal(signal.SIGINT, handle_sigint)

    ch_name = f"FRS Channel {channel}" if channel else "custom frequency"
    status.info(f"Tuning to {freq:.4f} MHz ({ch_name})...")
    radio.start()
    status.success(
        f"SDR uplink established. Gain: {args.gain}dB. "
        f"Squelch: {args.squelch}. Volume: {int(args.volume * 100)}%"
    )
    status.standby("Squelch closed. Standing by for transmission...")

    hotkeys = HotkeyListener(on_record, on_quit, on_help,
                             on_volume_up=on_volume_up,
                             on_volume_down=on_volume_down)
    backend = hotkeys.start()
    if backend == "stdin":
        status.standby("Hotkeys via terminal (no display) — keep this window focused.")

    status.set_live(True)
    prev_signal = False
    try:
        with Live(
            banner.live_layout(
                agent=args.agent, freq=freq, channel=channel,
                gain=args.gain, squelch=args.squelch,
                radio=radio, recorder=recorder, status=status,
                help_visible=help_state["visible"],
            ),
            console=status.console,
            screen=True,
            refresh_per_second=4,
        ) as live:
            while not quit_event.is_set():
                # Narrate signal transitions into the status log.
                now_signal = radio.signal_active
                if now_signal and not prev_signal:
                    status.success("SIGNAL DETECTED — Intercept in progress")
                elif prev_signal and not now_signal:
                    status.standby("Signal lost. Resuming surveillance...")
                prev_signal = now_signal

                if radio.crashed:
                    quit_event.set()

                live.update(banner.live_layout(
                    agent=args.agent, freq=freq, channel=channel,
                    gain=args.gain, squelch=args.squelch,
                    radio=radio, recorder=recorder, status=status,
                    help_visible=help_state["visible"],
                ))
                time.sleep(0.25)
    finally:
        status.set_live(False)
        hotkeys.stop()
        if recorder.is_recording:
            status.alert("Exit during recording — auto-saving capture...")
            recorder.stop()
        radio.stop()


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    from sia import status
    status.configure(no_color=args.no_color)

    from sia import banner
    compact = banner.is_compact(status.console)
    if args.help:
        status.console.print(banner.help_panel(compact=compact))
        return 0

    status.console.print(banner.startup_banner(args.agent))
    banner.press_any_key(status.console)
    banner.play_boot_sequence(args.agent, status)

    if not check_binaries(status):
        return 1

    found, _serial = detect_device(status)
    if not found:
        return 1

    args.output = resolve_output_dir(args.output, status)
    freq, channel = validate_and_clamp(args, status)

    run_session(args, freq, channel, status)

    status.console.print(banner.quit_panel(args.agent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
