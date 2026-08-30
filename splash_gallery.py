#!/usr/bin/env python3
"""SIA Splash Screen Gallery — browse 10 candidate splash screens.

Standalone preview tool. Pick a favourite by number, then we wire it into
``sia/banner.py:startup_banner()``. This program never touches the SDR and uses
only plain blocking input() for navigation — no pynput, no raw-mode tty, so it
cannot lock the console.

    .venv/bin/python splash_gallery.py
"""

import argparse
import sys
import time

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Theme palette (matches the main app).
GREEN = "bright_green"
YELLOW = "bright_yellow"
RED = "bright_red"
CYAN = "cyan"
DIM = "bright_black"

console = Console()


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def _show(con, renderable, content_height):
    """Clear the screen and print a renderable centred horizontally + roughly
    vertically (so it sits nicely on a small 5" panel)."""
    con.clear()
    pad = max(0, (con.size.height - content_height) // 2 - 1)
    for _ in range(pad):
        con.print()
    con.print(Align.center(renderable))


def _block(segments):
    """Build a multi-line Text from a list of (text, style) tuples.

    Each line is centred independently. Good for symmetric text stacks; NOT for
    ASCII art whose lines must stay vertically aligned — use _compose for that.
    Using append() avoids rich markup parsing of literal '[' / ']' in the art.
    """
    t = Text(justify="center")
    for i, (line, style) in enumerate(segments):
        t.append(line, style=style)
        if i != len(segments) - 1:
            t.append("\n")
    return t


def _compose(art, caps=()):
    """Build a left-justified Text where ART lines keep their relative columns
    (shifted by one shared pad so the block is centred) and CAPTION lines are
    centred on the same axis. Centres correctly even when captions are wider
    than the art. Pass to _show, which centres the whole block on screen.
    """
    art_w = max((len(line) for line, _ in art), default=0)
    cap_w = max((len(line) for line, _ in caps), default=0)
    maxw = max(art_w, cap_w)
    art_pad = (maxw - art_w) // 2
    t = Text()
    first = True
    for line, style in art:
        if not first:
            t.append("\n")
        first = False
        t.append(" " * art_pad + line, style=style)
    for line, style in caps:
        if not first:
            t.append("\n")
        first = False
        t.append(" " * ((maxw - len(line)) // 2) + line, style=style)
    return t


# ---------------------------------------------------------------------------
# Splash designs 1-10. Each: render_N(con, animate=True)
# ---------------------------------------------------------------------------
SIA_LOGO = (
    " ███████╗██╗ █████╗\n"
    " ██╔════╝██║██╔══██╗\n"
    " ███████╗██║███████║\n"
    " ╚════██║██║██╔══██║\n"
    " ███████║██║██║  ██║\n"
    " ╚══════╝╚═╝╚═╝  ╚═╝"
)


def render_1(con, animate=True):
    """CLASSIC — the original block wordmark + TOP SECRET stamp."""
    body = Text(justify="center")
    body.append(SIA_LOGO + "\n\n", style=GREEN)
    body.append("SPY INTELLIGENCE AGENCY\n", style="bold " + GREEN)
    body.append("── MISSION INTERCEPT v1.0.0 ──\n", style=GREEN)
    body.append("── CHANNEL 3 SURVEILLANCE ──\n\n", style=GREEN)
    body.append("AGENTS: ", style=GREEN)
    body.append("MEGASPY & SPYHUNTER\n\n", style=YELLOW)
    body.append("████ TOP SECRET ████", style=RED)
    panel = Panel(Align.center(body), border_style=GREEN,
                  title="[bright_yellow]CLASSIFIED — SIA[/]", padding=(1, 4))
    _show(con, panel, 18)


def render_2(con, animate=True):
    """ANTENNA UPLINK — broadcasting tower with RF waves."""
    art = [
        "   (( ° ))",
        "    \\   /",
        "     \\ /",
        "      |",
        "     /|\\",
        "    ┌─┴─┐",
        "    │SIA│",
        "    └───┘",
    ]
    caps = [
        ("", GREEN),
        ("SDR UPLINK ESTABLISHED", YELLOW),
        ("462.6125 MHz · FRS CH 3", CYAN),
    ]
    _show(con, _compose([(a, GREEN) for a in art], caps), 12)


def render_3(con, animate=True):
    """TARGET LOCK (animated) — surveillance crosshair locking on."""
    def frame(center_glyph, filled, label, label_style):
        art = [
            ("        │", GREEN),
            ("        │", GREEN),
            (f"  ──────{center_glyph}──────", GREEN),
            ("        │", GREEN),
            ("        │", GREEN),
        ]
        bar = "▰" * filled + "▱" * (5 - filled)
        caps = [
            ("", GREEN),
            (f"[{bar}]  {label}", label_style),
            ("462.6125 MHz", CYAN),
        ]
        return _compose(art, caps)

    if animate:
        try:
            for i in range(6):
                glyph = "┼" if i % 2 else "╋"
                _show(con, frame(glyph, i, "ACQUIRING TARGET", YELLOW), 11)
                time.sleep(0.14)
        except KeyboardInterrupt:
            pass
    _show(con, frame("⊕", 5, "● TARGET ACQUIRED", "bold " + GREEN), 11)


def render_4(con, animate=True):
    """CLASSIFIED DOSSIER — redacted case file with TOP SECRET stamp."""
    body = Text()
    body.append("CASE FILE  ", style="bold " + GREEN)
    body.append("#SIA-0003\n", style=YELLOW)
    body.append("────────────────────────\n", style=DIM)
    body.append("SUBJECT : ", style=GREEN)
    body.append("███████████\n", style=DIM)
    body.append("FREQ    : ", style=GREEN)
    body.append("462.6125 MHz\n", style=YELLOW)
    body.append("STATUS  : ", style=GREEN)
    body.append("████ ", style=DIM)
    body.append("INTERCEPT\n\n", style=RED)
    body.append("        ╱ TOP SECRET ╲\n", style="bold " + RED)
    body.append("          EYES ONLY", style=RED)
    panel = Panel(body, border_style=RED, title="[bright_red]CLASSIFIED[/]",
                  padding=(1, 3))
    _show(con, panel, 14)


def render_5(con, animate=True):
    """RADAR SWEEP (animated) — scope sweeping for contacts."""
    # Each sweep is three fixed-width (9-col) interior rows so the box edges
    # always line up.
    SWEEPS = {
        "-": ("         ", "  ─────  ", "         "),
        "|": ("    │    ", "    │    ", "    │    "),
        "\\": (" ╲       ", "    ╲    ", "       ╲ "),
        "/": ("       ╱ ", "    ╱    ", " ╱       "),
    }

    def scope(key, blip, label, label_style):
        r1, r2, r3 = SWEEPS[key]
        if blip:
            r1 = r1[:7] + "•" + r1[8:]
        art = [
            ("  ╭─────────╮", GREEN),
            (f"  │{r1}│", GREEN),
            (f"  │{r2}│", GREEN),
            (f"  │{r3}│", GREEN),
            ("  ╰─────────╯", GREEN),
        ]
        return _compose(art, [("", GREEN), (label, label_style)])

    if animate:
        try:
            for i in range(10):
                key = "|\\-/"[i % 4]
                _show(con, scope(key, i >= 6, "SCANNING 462.6125 MHz", YELLOW), 10)
                time.sleep(0.13)
        except KeyboardInterrupt:
            pass
    _show(con, scope("-", True, "● CONTACT — 462.6125 MHz", "bold " + GREEN), 10)


def render_6(con, animate=True):
    """SPY NOIR — minimal agent silhouette."""
    seg = [
        ("🕵", YELLOW),
        ("", GREEN),
        ("SPY INTELLIGENCE AGENCY", "bold " + GREEN),
        ("- - - - - - - - - - - - - -", DIM),
        ('"TRUST NO SIGNAL"', YELLOW),
        ("", GREEN),
        ("MISSION INTERCEPT · CH 3", CYAN),
    ]
    _show(con, _block(seg), 9)


def render_7(con, animate=True):
    """WAVEFORM — RF capture look."""
    seg = [
        ("S I A   I N T E R C E P T", "bold " + GREEN),
        ("", GREEN),
        ("▁▂▃▅▇▆▄▂▃▅▇▆▄▃▂▁▂▃▅▇▆▄▂▅", GREEN),
        ("▇▆▄▂▃▅▇▆▄▃▂▁▂▃▅▇▆▄▂▃▅▇▆▄", CYAN),
        ("", GREEN),
        ("FRS CH 3 · 462.6125 MHz", YELLOW),
        ("● MONITORING", RED),
    ]
    _show(con, _block(seg), 9)


def render_8(con, animate=True):
    """TUNER DIAL — frequency dial with needle on Channel 3."""
    art = [
        ("            ▼", RED),
        ("  ┝━━━━━━━━━┿━━━━━━━━━┥", GREEN),
        ("  462.5     ·     462.7", DIM),
    ]
    caps = [
        ("", GREEN),
        ("462.6125 MHz", "bold " + YELLOW),
        ("CH 3 · FM · SIA INTERCEPT", CYAN),
    ]
    _show(con, _compose(art, caps), 8)


def render_9(con, animate=True):
    """MATRIX BOOT (animated) — hacker-style access-granted sequence."""
    boot = [
        ("> initializing SIA secure terminal", GREEN),
        ("> loading encryption protocols", GREEN),
        ("> establishing SDR uplink", GREEN),
        ("> verifying agent credentials", GREEN),
        ("> ACCESS GRANTED", "bold " + GREEN),
    ]
    title = ("[ SIA · MISSION INTERCEPT ]", YELLOW)

    if animate:
        try:
            for k in range(1, len(boot) + 1):
                _show(con, _compose(list(boot[:k])), 9)
                time.sleep(0.22)
        except KeyboardInterrupt:
            pass
    _show(con, _compose(boot, [("", GREEN), title]), 9)


def render_10(con, animate=True):
    """SATELLITE RELAY — orbital uplink."""
    art = [
        "    ▟▙       ) ) )",
        "   ▟██▙     ╱",
        "   ▝▀▀▘    ╱",
        "         ╱",
        "   ┌────┴─┐",
        "   │ RELAY│",
        "   └──────┘",
    ]
    caps = [
        ("", GREEN),
        ("UPLINK ESTABLISHED", YELLOW),
        ("SIA ORBITAL RELAY · CH 3", CYAN),
    ]
    _show(con, _compose([(a, GREEN) for a in art], caps), 11)


SPLASHES = [
    (1, "CLASSIC", render_1),
    (2, "ANTENNA UPLINK", render_2),
    (3, "TARGET LOCK  (animated)", render_3),
    (4, "CLASSIFIED DOSSIER", render_4),
    (5, "RADAR SWEEP  (animated)", render_5),
    (6, "SPY NOIR", render_6),
    (7, "WAVEFORM", render_7),
    (8, "TUNER DIAL", render_8),
    (9, "MATRIX BOOT  (animated)", render_9),
    (10, "SATELLITE RELAY", render_10),
]


# ---------------------------------------------------------------------------
# Viewer + menu (plain input only)
# ---------------------------------------------------------------------------
def view(con, entry, animate=True):
    number, name, fn = entry
    fn(con, animate=animate)
    con.print()
    footer = Text(justify="center")
    footer.append("── ", style=DIM)
    footer.append(f"SPLASH #{number}", style="bold " + YELLOW)
    footer.append(f" · {name} ── ", style=DIM)
    footer.append("[Enter] back to menu", style=GREEN)
    con.print(Align.center(footer))
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass


def menu(con):
    while True:
        con.clear()
        title = Text(justify="center")
        title.append("SIA SPLASH GALLERY\n", style="bold " + GREEN)
        title.append("choose a splash screen\n", style=DIM)
        con.print(Align.center(title))
        listing = Text(justify="center")
        for number, name, _ in SPLASHES:
            listing.append(f"{number:>2}", style="bold " + YELLOW)
            listing.append(f"  {name}\n", style="white")
        con.print(Align.center(listing))
        prompt = Text(justify="center")
        prompt.append("\nSelect ", style=GREEN)
        prompt.append("1-10", style=YELLOW)
        prompt.append(", ", style=GREEN)
        prompt.append("a", style=YELLOW)
        prompt.append(" = play all, ", style=GREEN)
        prompt.append("q", style=YELLOW)
        prompt.append(" = quit", style=GREEN)
        con.print(Align.center(prompt))
        try:
            choice = input("\n  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if choice in ("q", "quit", "exit"):
            break
        if choice == "a":
            for entry in SPLASHES:
                view(con, entry)
        elif choice.isdigit() and 1 <= int(choice) <= len(SPLASHES):
            view(con, SPLASHES[int(choice) - 1])
        # anything else: redraw the menu


def main(argv=None):
    parser = argparse.ArgumentParser(description="SIA splash screen gallery")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    global console
    console = Console(no_color=args.no_color)
    try:
        menu(console)
    finally:
        console.show_cursor(True)
    console.clear()
    console.print(f"[{GREEN}]Gallery closed. Tell me which # you want, Agent.[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
