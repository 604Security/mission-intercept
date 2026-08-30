# 🕵️ CLASSIFIED — SPY INTELLIGENCE AGENCY
## Project: Mission Intercept — RTL-SDR FRS Channel Monitor
### Codename: SPYHUNTER-TERMINAL
### Clearance Level: TOP SECRET
### Assigned Agents: MegaSpy & Spyhunter

---

## MISSION BRIEFING

You are tasked with building a **fun, bright, spy-themed Python terminal application** called **Mission Intercept** for the **Spy Intelligence Agency (SIA)**. This tool listens to FRS/GMRS radio Channel 3 (462.6125 MHz) using an RTL-SDR dongle (RTL-SDR Blog V4), displays live status in a Metasploit-style terminal UI, and allows the operator to toggle recording on/off with the `R` key while listening. The app must be rich in ASCII art, colour, personality, and polish.

This document is a **complete, verbose specification** intended to be handed directly to a coding AI (Claude Code) to implement without ambiguity. Follow every section precisely.

---

## SECTION 1 — PROJECT OVERVIEW

| Field | Value |
|---|---|
| App Name | Mission Intercept |
| Organization | Spy Intelligence Agency (SIA) |
| Agents | MegaSpy, Spyhunter |
| Language | Python 3.10+ |
| Target OS | Linux (Kali/Debian) |
| SDR Hardware | RTL-SDR Blog V4 |
| Target Frequency | 462.6125 MHz (FRS Channel 3) |
| Demodulation | NFM (Narrow FM) |
| SDR Backend | `rtl_fm` CLI (subprocess pipe) |
| Audio Output | `aplay` (via subprocess pipe) |
| Recording Format | Raw 16-bit signed LE PCM → convert to `.wav` on stop |
| UI Framework | `rich` library (for colour, panels, live updates) |
| Hotkeys | `R` = toggle record, `Q` = quit |
| CLI Args | `--help/-h`, `--agent/-a`, `--gain/-g`, `--squelch/-s`, `--output/-o`, `--no-color` |

---

## SECTION 2 — SYSTEM REQUIREMENTS & DEPENDENCIES

### 2.1 System Packages (must be installed on host)
```
rtl-sdr        # provides rtl_fm binary
sox            # optional, for audio conversion
alsa-utils     # provides aplay
```

### 2.2 Python Dependencies
```
rich           # pip install rich
pynput         # pip install pynput   (for non-blocking hotkey detection)
```

### 2.3 Installation Check
On startup, the app must verify:
- `rtl_fm` binary exists (use `shutil.which('rtl_fm')`)
- `aplay` binary exists (use `shutil.which('aplay')`)
- RTL-SDR dongle is connected (attempt `rtl_test -t` or parse `rtl_fm` startup output)

If any check fails, print a styled error and exit gracefully with a spy-flavoured message.

Example:
```
[!] MISSION ABORT: rtl_fm not found. Install rtl-sdr package first, Agent.
```

---

## SECTION 3 — FILE STRUCTURE

```
spy-game/
├── mission_intercept.py        # Main entry point
├── sia/
│   ├── __init__.py
│   ├── banner.py               # All ASCII art and banners
│   ├── radio.py                # RTL-SDR subprocess management
│   ├── recorder.py             # Recording logic (raw PCM → WAV)
│   ├── hotkeys.py              # Pynput keyboard listener
│   ├── status.py               # Metasploit-style status message helpers
│   └── config.py               # Constants, defaults, channel frequency map
├── recordings/                 # Default output directory for recordings
│   └── .gitkeep
└── README.md
```

---

## SECTION 4 — ASCII ART & VISUAL DESIGN

### 4.1 Colour Palette
Use `rich` markup for all colour. The theme is **bright spy/hacker green on black** with **yellow accents** and **red for alerts**.

| Element | Color |
|---|---|
| Banner text | `bright_green` |
| Agent name | `bright_yellow` |
| Status `[*]` info | `cyan` |
| Status `[+]` success | `bright_green` |
| Status `[!]` alert/warning | `bright_red` |
| Status `[-]` standby | `dim white` |
| Recording indicator | `bright_red` blinking |
| Signal bar | `bright_green` |
| Panel borders | `green` |
| Timestamps | `bright_black` (grey) |

### 4.2 Startup Banner
Display this on launch (before anything else). Center it in the terminal. Use `rich.panel.Panel` with `bright_green` border.

```
 ________  ___  ________     
|\\   ____\\|\\  \\|\\   __  \\    
\\ \\  \\___|\\ \\  \\ \\  \\|\\  \\   
 \\ \\_____  \\ \\  \\ \\   __  \\  
  \\|____|\\  \\ \\  \\ \\  \\ \\  \\ 
    ____\\_\\  \\ \\__\\ \\__\\ \\__\\
   |\\_________\\|__|\\|__|\\|__|
   \\|_________|              

  SPY INTELLIGENCE AGENCY
  ── MISSION INTERCEPT v1.0 ──
  ── CHANNEL 3 SURVEILLANCE ──

  AGENTS: MEGASPY & SPYHUNTER
  CLASSIFICATION: TOP SECRET
```

Below the banner, display a short animated "booting" sequence using `rich.progress` or a simple loop with `time.sleep(0.1)`:
```
[*] Initializing SIA secure terminal...
[*] Loading encryption protocols...
[*] Establishing SDR uplink...
[*] Verifying agent credentials...
[+] All systems nominal. Welcome, Agent [AGENT_NAME].
```

Each line should appear with a ~0.15 second delay for dramatic effect.

### 4.3 Main Listening UI Layout

Use `rich.layout.Layout` to divide the terminal into sections:

```
┌─────────────────────────────────────────────────┐
│             SPY INTELLIGENCE AGENCY              │
│         MISSION INTERCEPT — LIVE FEED            │
├─────────────────────────────────────────────────┤
│  FREQUENCY : 462.6125 MHz   CHANNEL : FRS-3     │
│  GAIN      : 20 dB          SQUELCH : 70        │
│  AGENT     : MEGASPY        MODE    : LISTENING  │
├─────────────────────────────────────────────────┤
│  SIGNAL    : ████████░░░░░░░░  STRONG            │
├─────────────────────────────────────────────────┤
│  STATUS LOG                                      │
│  [05:43:01] [*] Squelch closed. Standing by...  │
│  [05:43:12] [+] SIGNAL DETECTED                 │
│  [05:43:12] [*] Duration: 00:00:04              │
│  [05:43:16] [-] Signal lost. Resuming watch...  │
├─────────────────────────────────────────────────┤
│  [R] RECORD   [Q] QUIT   [H] HELP               │
│  ● REC: 00:01:23   recordings/2026-05-21_054301 │
└─────────────────────────────────────────────────┘
```

The signal bar should be a simple ASCII block bar built from `█` and `░` characters, updated every second based on whether audio data is flowing.

### 4.4 Recording Indicator
When recording is active, show a blinking red `●` REC indicator with elapsed time in `MM:SS` format. Use `rich`'s `Live` update loop to refresh this every second.

### 4.5 Quit Screen
On `Q` or `CTRL+C`, show:
```
[!] MISSION ABORT INITIATED...
[*] Securing recordings...
[*] Wiping session data...
[+] SIA terminal closed. Stay safe, Agent MEGASPY.

    ── END TRANSMISSION ──
```

---

## SECTION 5 — CLI ARGUMENTS

Implement using Python's `argparse`. Style the help output with `rich` using a custom formatter if possible, otherwise standard argparse is acceptable.

### 5.1 Arguments

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--agent` | `-a` | str | `MegaSpy` | Agent codename displayed in UI |
| `--gain` | `-g` | int | `20` | RTL-SDR tuner gain in dB (0–50) |
| `--squelch` | `-s` | int | `70` | Squelch level for rtl_fm `-l` flag |
| `--output` | `-o` | str | `./recordings` | Directory to save recordings |
| `--no-color` | | flag | False | Disable colour output |
| `--freq` | `-f` | float | `462.6125` | Override frequency in MHz |
| `--channel` | `-c` | int | None | FRS channel number (1–22), overrides --freq |
| `--help` | `-h` | | | Show help and exit |

### 5.2 Help Screen Style
The `--help` output should be styled like a mission briefing:

```
╔══════════════════════════════════════════════════╗
║      SPY INTELLIGENCE AGENCY — MISSION HELP      ║
╚══════════════════════════════════════════════════╝

USAGE:
  python mission_intercept.py [OPTIONS]

MISSION PARAMETERS:
  -a, --agent NAME       Agent codename [default: MegaSpy]
  -g, --gain DB          SDR gain in dB, 0-50 [default: 20]
  -s, --squelch LEVEL    Squelch threshold [default: 70]
  -o, --output DIR       Recording output directory [default: ./recordings]
  -f, --freq MHZ         Target frequency in MHz [default: 462.6125]
  -c, --channel N        FRS channel 1-22 (overrides --freq)
      --no-color         Disable colour output

EXAMPLES:
  python mission_intercept.py
  python mission_intercept.py -a Spyhunter -g 30 -s 50
  python mission_intercept.py -c 3 -o /tmp/recordings
  python mission_intercept.py --help
```

---

## SECTION 6 — RADIO BACKEND (radio.py)

### 6.1 RTL-FM Command Construction
Build the `rtl_fm` command dynamically from config:

```python
cmd_rtlfm = [
    'rtl_fm',
    '-f', f'{frequency}M',
    '-M', 'fm',
    '-s', '200k',
    '-r', '48000',
    '-g', str(gain),
    '-l', str(squelch)
]

cmd_aplay = [
    'aplay',
    '-r', '48000',
    '-f', 'S16_LE',
    '-t', 'raw',
    '-c', '1'
]
```

### 6.2 Process Pipeline
- Launch `rtl_fm` as a subprocess with `stdout=PIPE`
- Pipe `rtl_fm.stdout` into `aplay` stdin
- **Also** tee the raw audio data into a buffer when recording is active
- Use a background thread to read from `rtl_fm.stdout` in chunks (4096 bytes)
- The main thread handles UI updates and hotkeys

### 6.3 Tee Logic (listen + record simultaneously)
```python
# Pseudocode
while running:
    chunk = rtl_fm_process.stdout.read(4096)
    if chunk:
        aplay_process.stdin.write(chunk)
        if recording:
            recording_buffer.write(chunk)
```

### 6.4 Signal Detection (Simple)
Track whether audio chunks contain non-zero data. If the chunk is all zeros or below a threshold, mark as "squelch closed". If data is present, mark as "signal detected". Use this to update the signal bar in the UI.

---

## SECTION 7 — RECORDER (recorder.py)

### 7.1 Recording Toggle
- `R` key toggles recording on/off
- When toggled ON:
  - Create a new file in the output directory
  - Filename format: `SIA_INTERCEPT_YYYY-MM-DD_HHMMSS.raw`
  - Start writing raw PCM chunks to file
  - Display REC indicator
- When toggled OFF:
  - Close the raw file
  - Convert to WAV using Python's `wave` module
  - Delete the raw file
  - Log: `[+] Recording saved: SIA_INTERCEPT_2026-05-21_054301.wav`

### 7.2 WAV Conversion
```python
import wave

def raw_to_wav(raw_path, wav_path):
    with open(raw_path, 'rb') as raw_file:
        raw_data = raw_file.read()
    with wave.open(wav_path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)       # 16-bit = 2 bytes
        wav_file.setframerate(48000)
        wav_file.writeframes(raw_data)
```

### 7.3 Auto-save on Exit
If the user quits while recording is active, automatically stop and save the recording before exiting.

---

## SECTION 8 — HOTKEYS (hotkeys.py)

Use `pynput.keyboard.Listener` in a non-blocking background thread.

| Key | Action |
|---|---|
| `r` or `R` | Toggle recording on/off |
| `q` or `Q` | Quit application |
| `h` or `H` | Show help overlay |
| `CTRL+C` | Quit application (handle via signal handler) |

Do NOT use blocking `input()` for hotkeys. The listener must run in a daemon thread so the main UI loop is never blocked.

---

## SECTION 9 — STATUS MESSAGES (status.py)

All status messages must follow Metasploit style with timestamp prefix.

```python
from datetime import datetime
from rich.console import Console

console = Console()

def timestamp():
    return datetime.now().strftime('%H:%M:%S')

def info(msg):
    console.print(f"[bright_black][{timestamp()}][/] [cyan][*][/] {msg}")

def success(msg):
    console.print(f"[bright_black][{timestamp()}][/] [bright_green][+][/] {msg}")

def alert(msg):
    console.print(f"[bright_black][{timestamp()}][/] [bright_red][!][/] {msg}")

def standby(msg):
    console.print(f"[bright_black][{timestamp()}][/] [dim white][-][/] {msg}")
```

### 9.1 Status Message Examples Used Throughout App

```
[*] Initializing SIA secure terminal...
[*] Checking for rtl_fm binary...
[+] rtl_fm found at /usr/bin/rtl_fm
[*] Checking for aplay binary...
[+] aplay found at /usr/bin/aplay
[*] Scanning for RTL-SDR hardware...
[+] RTL-SDR Blog V4 detected. Serial: 00000001
[*] Tuning to 462.6125 MHz (FRS Channel 3)...
[+] SDR uplink established. Gain: 20dB. Squelch: 70
[-] Squelch closed. Standing by for transmission...
[+] SIGNAL DETECTED — Intercept in progress
[-] Signal lost. Resuming surveillance...
[*] Recording initiated: SIA_INTERCEPT_2026-05-21_054301.raw
[+] Recording stopped. Converting to WAV...
[+] Recording saved: SIA_INTERCEPT_2026-05-21_054301.wav (2.3 MB)
[!] MISSION ABORT — User requested exit
[*] Shutting down SDR uplink...
[+] Terminal secured. Stay safe, Agent MEGASPY.
```

---

## SECTION 10 — CHANNEL FREQUENCY MAP (config.py)

```python
FRS_CHANNELS = {
    1:  462.5625,
    2:  462.5875,
    3:  462.6125,
    4:  462.6375,
    5:  462.6625,
    6:  462.6875,
    7:  462.7125,
    8:  467.5625,
    9:  467.5875,
    10: 467.6125,
    11: 467.6375,
    12: 467.6625,
    13: 467.6875,
    14: 467.7125,
    15: 462.5500,
    16: 462.5750,
    17: 462.6000,
    18: 462.6250,
    19: 462.6500,
    20: 462.6750,
    21: 462.7000,
    22: 462.7250,
}

DEFAULT_FREQ     = 462.6125   # FRS Channel 3
DEFAULT_GAIN     = 20
DEFAULT_SQUELCH  = 70
DEFAULT_AGENT    = "MegaSpy"
DEFAULT_OUTPUT   = "./recordings"
SAMPLE_RATE      = 48000
CHUNK_SIZE       = 4096
APP_VERSION      = "1.0.0"
ORG_NAME         = "Spy Intelligence Agency"
```

---

## SECTION 11 — ERROR HANDLING

| Scenario | Behaviour |
|---|---|
| `rtl_fm` not found | Print `[!]` error, exit code 1 |
| `aplay` not found | Print `[!]` error, exit code 1 |
| No RTL-SDR dongle detected | Print `[!]` error, exit code 1 |
| Output directory not writable | Print `[!]` error, fall back to `/tmp` |
| RTL-FM process crashes mid-session | Print `[!]` alert, attempt restart once, then exit |
| `CTRL+C` during recording | Auto-save recording, then exit cleanly |
| Invalid channel number | Print `[!]` error listing valid channels 1–22 |
| Invalid gain (out of 0–50) | Print `[!]` error, clamp to nearest valid value |

---

## SECTION 12 — EXAMPLE FULL SESSION OUTPUT

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║    ███████╗██╗ █████╗                                ║
║    ██╔════╝██║██╔══██╗                               ║
║    ███████╗██║███████║                               ║
║    ╚════██║██║██╔══██║                               ║
║    ███████║██║██║  ██║                               ║
║    ╚══════╝╚═╝╚═╝  ╚═╝                               ║
║                                                      ║
║               SPY INTELLIGENCE AGENCY                ║
║        ── MISSION INTERCEPT v1.0 ──                  ║
║        AGENTS: MEGASPY & SPYHUNTER                   ║
║        CLASSIFICATION: ████ TOP SECRET ████          ║
║                                                      ║
╚══════════════════════════════════════════════════════╝

[05:43:00] [*] Initializing SIA secure terminal...
[05:43:00] [*] Checking for rtl_fm binary...
[05:43:00] [+] rtl_fm found at /usr/bin/rtl_fm
[05:43:00] [*] Checking for aplay binary...
[05:43:00] [+] aplay found at /usr/bin/aplay
[05:43:01] [*] Scanning for RTL-SDR hardware...
[05:43:01] [+] RTL-SDR Blog V4 detected. Serial: 00000001
[05:43:01] [*] Tuning to 462.6125 MHz (FRS Channel 3)...
[05:43:01] [+] SDR uplink established. Gain: 20dB. Squelch: 70
[05:43:01] [-] Squelch closed. Standing by for transmission...

┌─ LIVE INTERCEPT ─────────────────────────────────────┐
│  FREQ: 462.6125 MHz   CH: FRS-3   AGENT: MEGASPY     │
│  SIGNAL: ░░░░░░░░░░░░░░░░  SILENT                    │
│  [R] RECORD  [Q] QUIT  [H] HELP                      │
└──────────────────────────────────────────────────────┘

[05:43:12] [+] SIGNAL DETECTED — Intercept in progress
[05:43:12] [*] Recording initiated — SIA_INTERCEPT_2026-05-21_054312.raw
[05:43:16] [-] Signal lost. Resuming surveillance...
[05:43:20] [+] SIGNAL DETECTED — Intercept in progress
[05:43:25] [-] Signal lost. Resuming surveillance...
[05:43:30] [*] Recording stopped by agent.
[05:43:30] [+] Converting raw PCM to WAV...
[05:43:30] [+] Recording saved: SIA_INTERCEPT_2026-05-21_054312.wav (892 KB)

[05:43:45] [!] MISSION ABORT — Agent MEGASPY requested exit
[05:43:45] [*] Shutting down SDR uplink...
[05:43:45] [*] Securing all recordings...
[05:43:45] [+] Terminal secured. Stay safe, Agent MEGASPY.

    ── END TRANSMISSION ──
```

---

## SECTION 13 — IMPLEMENTATION NOTES FOR CLAUDE CODE

1. **Do not use `curses`** — use `rich` library exclusively for all UI. It is cleaner and more maintainable.
2. **Threading model**: Main thread = UI loop. Thread 1 = RTL-FM stdout reader. Thread 2 = pynput keyboard listener. Use `threading.Event` for clean shutdown signalling across threads.
3. **The `rich.live.Live` context manager** should wrap the main status panel and refresh every 1 second.
4. **Do not hardcode paths** — use `pathlib.Path` throughout.
5. **All subprocess pipes must be cleaned up** on exit — call `.terminate()` then `.wait()` on both `rtl_fm` and `aplay` processes.
6. **Test the boot sequence animation** — it should feel dramatic, not instant.
7. **The signal bar** is purely cosmetic — base it on whether audio chunks are non-zero, not actual dBm values.
8. **Recording filenames** must be unique — use timestamp. Never overwrite existing files.
9. **The `--no-color` flag** should set `rich.console.Console(no_color=True)`.
10. **Keep `mission_intercept.py` thin** — it should only parse args, run dependency checks, and call into `sia/` modules.

---

## SECTION 14 — STRETCH GOALS (implement only after core is working)

- [ ] CTCSS tone injection on recording filename (e.g. `_CTCSS131.8`)
- [ ] Multi-channel scanner mode (cycle through all 22 FRS channels)
- [ ] Signal strength history graph using `rich` sparkline characters `▁▂▃▄▅▆▇█`
- [ ] Automatic transcription of recordings using `whisper` (OpenAI)
- [ ] Discord webhook alert when signal detected

---

*This document is CLASSIFIED — Spy Intelligence Agency — Eyes Only*
*MegaSpy & Spyhunter — Authorized Personnel Only*
*── END OF MISSION BRIEF ──*
