# Mission Intercept

Spy-themed RTL-SDR FRS/GMRS channel monitor for the **Spy Intelligence Agency (SIA)**.
Listens to an FRS/GMRS channel (default **Channel 3 — 462.6125 MHz**) via an
RTL-SDR dongle, plays the audio live, and records to WAV on demand — all inside
a bright, Metasploit-style terminal UI built with [`rich`](https://github.com/Textualize/rich).

```
rtl_fm  ──stdout──▶  reader thread  ──▶  aplay (live monitor)
                          │
                          └──▶  recorder (raw PCM ──▶ .wav on stop)
```

## Requirements

System packages:

- `rtl-sdr` — provides `rtl_fm` and `rtl_test`
- `alsa-utils` — provides `aplay`

Python: 3.10+ with `rich` and `pynput`.

## Setup

This system is PEP 668 "externally managed", so the dependencies live in a
project virtualenv:

```bash
python3 -m venv .venv
.venv/bin/pip install rich pynput
```

## Usage

The `./intercept` launcher runs the app from the project virtualenv (and works
from any directory):

```bash
./intercept                          # default: Channel 3, agent MegaSpy
./intercept -a Spyhunter -g 30 -V 2.5
./intercept -c 3 -o /tmp/recordings
./intercept --help
```

Equivalent to invoking the venv directly:

```bash
.venv/bin/python mission_intercept.py [OPTIONS]
```

### Options

| Flag | | Default | Description |
|---|---|---|---|
| `--agent` | `-a` | `MegaSpy` | Agent codename shown in the UI |
| `--gain` | `-g` | `20` | RTL-SDR tuner gain in dB (0–50, clamped) |
| `--squelch` | `-s` | `70` | Squelch level for `rtl_fm -l` |
| `--volume` | `-V` | `10.0` | Software audio volume multiplier (0–20, clamped; starts maxed at 1000%) |
| `--output` | `-o` | `./recordings` | Recording output directory |
| `--freq` | `-f` | `462.6125` | Target frequency in MHz |
| `--channel` | `-c` | — | FRS channel 1–22 (overrides `--freq`) |
| `--no-color` | | off | Disable colour output |
| `--help` | `-h` | | Show the mission-briefing help |

### Hotkeys

| Key | Action |
|---|---|
| `R` | Toggle recording on/off |
| `Q` | Quit |
| `H` | Toggle help overlay |
| `+` / `-` | Volume up / down (0–1000% in 50% steps; `=` works as `+`) |
| `Ctrl+C` | Quit (auto-saves any in-progress recording) |

Recordings are written as `SIA_INTERCEPT_YYYY-MM-DD_HHMMSS.wav` (mono, 16-bit,
48 kHz) in the output directory. The current volume boost is applied **before**
recording, so saved WAVs reflect the live volume setting.

## Notes

- **Silent channel = no recording data.** With squelch enabled (`-s 70`),
  `rtl_fm` emits audio only while a transmission is breaking squelch. If a
  recording comes out empty, the channel was simply quiet — lower the squelch
  (e.g. `-s 0`) to capture continuous audio/noise.
- **Faint audio?** FRS audio can be quiet, so the volume defaults to **400%**
  (`-V 4.0`). The tuner gain (`-g`) is RF gain, not loudness — use `-V`/`--volume`
  (or the `+`/`-` keys) to adjust the software boost. High multipliers can clip;
  back off with `-` if it sounds harsh.
- **Small screens.** The live UI auto-adapts: on a console under ~24 rows or
  ~70 columns (e.g. a 5" panel) it switches to a compact layout with tighter
  panels, a narrower signal bar, and a single-line footer. No flag needed —
  resize and it follows.
- **Hotkey backend.** `pynput` is used when an X display is available;
  on a headless/SSH session the app transparently falls back to reading the
  terminal in raw mode (keep the window focused for keys to register). The
  `+`/`-` volume keys work in both backends.
- **No dongle / missing binary** aborts with a styled error before tuning.
  An unwritable output directory falls back to `/tmp/sia_recordings`.

## Layout

```
mission_intercept.py     # entry point: args, checks, boot, session loop
sia/
  config.py              # channel map, defaults, constants
  status.py              # Metasploit-style status log + shared console
  banner.py              # ASCII art, boot/help/quit screens, live layout
  radio.py               # rtl_fm -> aplay pipeline, tee, signal metering
  recorder.py            # recording toggle, raw PCM -> WAV
  hotkeys.py             # pynput listener (+ stdin fallback)
recordings/              # default output directory
```

## Legal

Receive-only: this listens and records, it never transmits, so no licence is needed to run it.
Recording other people's conversations is a different question and the rules vary by country and
province/state — know what applies where you are before you keep anything off a shared channel.

## License

MIT — see [LICENSE](LICENSE).

---

*CLASSIFIED — Spy Intelligence Agency — Eyes Only*

