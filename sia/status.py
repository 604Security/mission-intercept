"""Metasploit-style status messages and a shared status log.

Status lines carry a timestamp prefix and a coloured severity tag:

    [HH:MM:SS] [*] info        (cyan)
    [HH:MM:SS] [+] success     (bright_green)
    [HH:MM:SS] [!] alert       (bright_red)
    [HH:MM:SS] [-] standby     (dim white)

During the boot sequence messages are printed directly to the console.
Once the Live UI takes over, ``set_live(True)`` stops direct printing and the
``StatusLog`` (rendered inside a panel) becomes the single source of truth.
"""

from collections import deque
from datetime import datetime

from rich.console import Console
from rich.text import Text

# Severity tag -> markup colour
_TAGS = {
    "info":    ("[*]", "cyan"),
    "success": ("[+]", "bright_green"),
    "alert":   ("[!]", "bright_red"),
    "standby": ("[-]", "dim white"),
}

# Shared console; reconfigured by configure() once CLI args are parsed.
console = Console()

# Whether the Live UI owns the screen. When True we don't print directly.
_live = False

# Rolling history of (timestamp, level, message) for the status panel.
_history = deque(maxlen=200)


def configure(no_color=False):
    """Reconfigure the shared console (e.g. to honour --no-color)."""
    global console
    console = Console(no_color=no_color)


def set_live(value):
    """Toggle Live-UI mode. While live, messages only feed the status log."""
    global _live
    _live = bool(value)


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def _emit(level, msg):
    tag, color = _TAGS[level]
    ts = timestamp()
    _history.append((ts, level, msg))
    if not _live:
        console.print(
            f"[bright_black][{ts}][/] [{color}]{tag}[/] {msg}"
        )


def info(msg):
    _emit("info", msg)


def success(msg):
    _emit("success", msg)


def alert(msg):
    _emit("alert", msg)


def standby(msg):
    _emit("standby", msg)


def history(limit=None):
    """Return recent (timestamp, level, message) tuples, newest last."""
    items = list(_history)
    if limit is not None:
        items = items[-limit:]
    return items


def render_log(limit=12):
    """Render the recent status history as a Rich ``Text`` block."""
    text = Text()
    entries = history(limit)
    if not entries:
        text.append("  (awaiting activity...)", style="dim white")
        return text
    for i, (ts, level, msg) in enumerate(entries):
        tag, color = _TAGS[level]
        text.append(f"[{ts}] ", style="bright_black")
        text.append(f"{tag} ", style=color)
        text.append(msg, style=color if level == "alert" else "white")
        if i != len(entries) - 1:
            text.append("\n")
    return text
