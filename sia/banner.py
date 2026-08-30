"""ASCII art, the startup banner, boot animation, help and quit screens."""

import time

from rich.align import Align
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import config

# Block-style "SIA" wordmark used in the startup banner.
SIA_LOGO = r"""
 ███████╗██╗ █████╗
 ██╔════╝██║██╔══██╗
 ███████╗██║███████║
 ╚════██║██║██╔══██║
 ███████║██║██║  ██║
 ╚══════╝╚═╝╚═╝  ╚═╝
"""

BOOT_LINES = [
    ("info",    "Initializing SIA secure terminal..."),
    ("info",    "Loading encryption protocols..."),
    ("info",    "Establishing SDR uplink..."),
    ("info",    "Verifying agent credentials..."),
]


def is_compact(console):
    """True when the console is too small for the full layout (5" screens)."""
    size = console.size
    return size.height < 24 or size.width < 70


def startup_banner(agent):
    """Return the CLASSIC splash: centred SIA wordmark + mission header."""
    body = Text(justify="center")
    body.append(SIA_LOGO.strip("\n") + "\n\n", style="bright_green")
    body.append(f"{config.ORG_NAME}\n", style="bold bright_green")
    body.append(f"── MISSION INTERCEPT v{config.APP_VERSION} ──\n",
                style="bright_green")
    body.append("── CHANNEL 3 SURVEILLANCE ──\n\n", style="bright_green")
    body.append("AGENTS: ", style="bright_green")
    body.append(f"{config.AGENTS.upper()}\n\n", style="bright_yellow")
    body.append("████ TOP SECRET ████", style="bright_red")

    return Panel(
        Align.center(body),
        border_style="bright_green",
        title="[bright_yellow]\U0001f575️  CLASSIFIED — SIA[/]",
        subtitle=f"[bright_yellow]AGENT: {agent.upper()}[/]",
        padding=(1, 4),
    )


def press_any_key(console, prompt="Press any key to begin the mission..."):
    """Pause after the splash until the operator presses a key.

    Uses a one-shot raw read (true "any key") on a real terminal, restoring
    terminal state immediately in a finally — it spawns no threads and never
    grabs input globally, so it can't lock the console. Falls back to Enter
    (input()) when stdin isn't a tty, and never crashes the boot on failure.
    """
    import sys

    console.print()
    console.print(Align.center(Text(prompt, style="bright_yellow")))

    if not sys.stdin.isatty():
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
        return

    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except KeyboardInterrupt:
        pass
    except Exception:  # noqa: BLE001 — never block boot on a key-read failure
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass


def play_boot_sequence(agent, status, delay=0.15):
    """Print the dramatic boot sequence, one line at a time.

    ``status`` is the sia.status module (passed in so we honour its console).
    """
    for level, msg in BOOT_LINES:
        getattr(status, level)(msg)
        time.sleep(delay)
    status.success(f"All systems nominal. Welcome, Agent {agent.upper()}.")
    time.sleep(delay)


def help_panel(compact=False):
    """Return a mission-briefing styled help Panel.

    In compact mode the EXAMPLES block is dropped so the overlay fits a 5"
    screen.
    """
    text = Text()
    text.append("USAGE:\n", style="bright_yellow")
    text.append("  python mission_intercept.py [OPTIONS]\n\n", style="white")
    text.append("MISSION PARAMETERS:\n", style="bright_yellow")
    rows = [
        ("-a, --agent NAME", "Agent codename [default: MegaSpy]"),
        ("-g, --gain DB", "SDR gain in dB, 0-50 [default: 20]"),
        ("-s, --squelch LEVEL", "Squelch threshold [default: 70]"),
        ("-V, --volume MULT", "Audio volume multiplier, 0-20 [default: 10.0]"),
        ("-o, --output DIR", "Recording output directory [default: ./recordings]"),
        ("-f, --freq MHZ", "Target frequency in MHz [default: 462.6125]"),
        ("-c, --channel N", "FRS channel 1-22 (overrides --freq)"),
        ("    --no-color", "Disable colour output"),
        ("-h, --help", "Show this mission briefing and exit"),
    ]
    for flag, desc in rows:
        text.append(f"  {flag:<22}", style="bright_green")
        text.append(f"{desc}\n", style="white")
    text.append("\nIN-MISSION HOTKEYS:\n", style="bright_yellow")
    text.append("  R  Record    ", style="bright_green")
    text.append("Q  Quit    ", style="bright_green")
    text.append("H  Help    ", style="bright_green")
    text.append("+/-  Volume\n", style="bright_green")
    if not compact:
        text.append("\nEXAMPLES:\n", style="bright_yellow")
        for ex in (
            "python mission_intercept.py",
            "python mission_intercept.py -a Spyhunter -g 30 -V 2.5",
            "python mission_intercept.py -c 3 -o /tmp/recordings",
            "python mission_intercept.py --help",
        ):
            text.append(f"  {ex}\n", style="bright_black")

    return Panel(
        text,
        title="[bright_green]SPY INTELLIGENCE AGENCY — MISSION HELP[/]",
        border_style="green",
        padding=(0, 2) if compact else (1, 2),
    )


def _mode_label(radio, recorder):
    if recorder.is_recording:
        return "RECORDING", "bright_red"
    if radio.signal_active:
        return "INTERCEPTING", "bright_green"
    return "LISTENING", "cyan"


def _header_panel(agent, radio, recorder, compact):
    text = Text(justify="center")
    if compact:
        mode, mode_color = _mode_label(radio, recorder)
        text.append(f"{config.ORG_ABBR} INTERCEPT · ", style="bold bright_green")
        text.append(f"{agent.upper()} · ", style="bright_yellow")
        text.append(mode, style=mode_color)
    else:
        text.append(f"{config.ORG_NAME}\n", style="bold bright_green")
        text.append("MISSION INTERCEPT — LIVE FEED", style="bright_yellow")
    return Panel(text, border_style="green", padding=(0, 1))


def _params_panel(agent, freq, channel, gain, squelch, radio, recorder, compact):
    mode, mode_color = _mode_label(radio, recorder)
    ch_label = f"FRS-{channel}" if channel else "CUSTOM"
    table = Table.grid(padding=(0, 2), expand=True)
    table.add_column(justify="left")
    table.add_column(justify="left")

    width = 8 if compact else 10

    def cell(label, value, value_style="bright_yellow"):
        t = Text()
        t.append(f"{label:<{width}}: ", style="green")
        t.append(str(value), style=value_style)
        return t

    table.add_row(cell("FREQ", f"{freq:.4f} MHz"), cell("CHANNEL", ch_label))
    table.add_row(cell("GAIN", f"{gain} dB"), cell("SQUELCH", squelch))
    if not compact:
        # AGENT and MODE live in the header when compact.
        table.add_row(cell("AGENT", agent.upper()), cell("MODE", mode, mode_color))
    return Panel(table, border_style="green", padding=(0, 1),
                 title="[green]MISSION PARAMETERS[/]", title_align="left")


def _signal_panel(radio, compact):
    bar = radio.signal_bar(width=12 if compact else 24)
    vol_pct = int(radio.volume * 100)
    t = Text.from_markup(
        f"  SIGNAL : {bar}   [cyan]VOL[/] [bright_yellow]{vol_pct}%[/]"
    )
    return Panel(t, border_style="green", padding=(0, 1))


def _log_panel(status, compact):
    return Panel(status.render_log(limit=6 if compact else 10), border_style="green",
                 title="[green]STATUS LOG[/]", title_align="left", padding=(0, 1))


def _footer_panel(recorder, compact):
    keys = Text(justify="center")
    for i, (key, label) in enumerate(
        (("R", "REC"), ("Q", "QUIT"), ("H", "HELP"), ("+/-", "VOL"))
    ):
        if i:
            keys.append("  ")
        keys.append(f"[{key}] {label}", style="bright_yellow")

    if compact:
        # Single combined line: keys, plus a short REC marker only while
        # recording (idle needs no text — the keys row is enough).
        if recorder.is_recording:
            keys.append("   ")
            keys.append("● REC ", style="blink bright_red")
            keys.append(recorder.elapsed_str(), style="bright_red")
        return Panel(keys, border_style="green", padding=(0, 1))

    status_line = Text(justify="center")
    if recorder.is_recording:
        status_line.append("● REC ", style="blink bright_red")
        status_line.append(recorder.elapsed_str(), style="bright_red")
        status_line.append(f"   {recorder.current_name}", style="bright_black")
    else:
        status_line.append("○ standing by — not recording", style="dim white")

    group = Table.grid(expand=True)
    group.add_column(justify="center")
    group.add_row(keys)
    group.add_row(status_line)
    return Panel(group, border_style="green", padding=(0, 1))


def live_layout(*, agent, freq, channel, gain, squelch,
                radio, recorder, status, help_visible=False):
    """Compose the full live-feed Layout for the rich.live.Live loop.

    The layout auto-adapts: on a small console (e.g. a 5" screen) it switches
    to compact panels with tighter heights, a narrower signal bar, and a
    single-line footer. Size is re-read each render so it reacts to resizes.
    """
    compact = is_compact(status.console)
    layout = Layout()
    layout.split_column(
        Layout(_header_panel(agent, radio, recorder, compact),
               name="header", size=3 if compact else 4),
        Layout(_params_panel(agent, freq, channel, gain, squelch,
                             radio, recorder, compact),
               name="params", size=4 if compact else 5),
        Layout(_signal_panel(radio, compact), name="signal", size=3),
        Layout(name="body", ratio=1),
        Layout(_footer_panel(recorder, compact),
               name="footer", size=3 if compact else 4),
    )
    if help_visible:
        layout["body"].update(help_panel(compact=compact))
    else:
        layout["body"].update(_log_panel(status, compact))
    return layout


def quit_panel(agent):
    """Return the end-of-mission farewell Panel."""
    text = Text()
    text.append("[!] MISSION ABORT INITIATED...\n", style="bright_red")
    text.append("[*] Securing recordings...\n", style="cyan")
    text.append("[*] Wiping session data...\n", style="cyan")
    text.append(
        f"[+] SIA terminal closed. Stay safe, Agent {agent.upper()}.\n\n",
        style="bright_green",
    )
    text.append("    ── END TRANSMISSION ──", style="bright_yellow")
    return Panel(
        Align.center(text),
        border_style="bright_red",
        padding=(1, 4),
    )
