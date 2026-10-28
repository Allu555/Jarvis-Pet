"""
ui/overlay.py – Always-on-top status overlay and system tray icon for JARVIS.

Overlay: small tkinter window showing Status / Last Command / Last Response.
Tray:    pystray icon with Pause / Resume / Quit menu.
"""

import logging
import queue
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable

logger = logging.getLogger("jarvis.ui.overlay")

# ─── Status messages ──────────────────────────────────────────────────────────
STATUS_COLORS = {
    "Idle":      "#555555",
    "Listening": "#00e5ff",
    "Thinking":  "#ffd600",
    "Acting":    "#ff6d00",
    "Speaking":  "#69f0ae",
    "Paused":    "#b0bec5",
    "Error":     "#ff1744",
}


class Overlay:
    """
    Thread-safe tkinter overlay.
    Runs in its own thread (Tk must own its thread).
    Use the public set_* methods from any thread.
    """

    def __init__(self, on_submit: Callable[[str], None] | None = None):
        self._q: queue.Queue = queue.Queue()
        self._root: tk.Tk | None = None
        self._entry: tk.Entry | None = None
        self._on_submit = on_submit
        self._thread = threading.Thread(target=self._run, daemon=True, name="overlay")
        self._thread.start()

    # ── Public API (thread-safe) ───────────────────────────────────────────────

    def set_status(self, status: str):
        self._q.put(("status", status))

    def set_command(self, text: str):
        self._q.put(("command", text[:80]))

    def set_response(self, text: str):
        self._q.put(("response", text[:120]))

    def destroy(self):
        self._q.put(("quit", None))

    # ── Tk thread ─────────────────────────────────────────────────────────────

    def _run(self):
        try:
            self._root = tk.Tk()
            self._build_ui()
            self._poll()
            self._root.mainloop()
        except Exception as e:
            logger.error(f"Overlay crashed: {e}")

    def _build_ui(self):
        root = self._root

        # Window chrome
        root.title("JARVIS")
        root.geometry("380x185+40+40")
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.92)
        root.overrideredirect(True)          # no title bar
        root.configure(bg="#0a0a0a")
        root.resizable(False, False)

        # Drag-to-move
        root.bind("<ButtonPress-1>",   self._drag_start)
        root.bind("<B1-Motion>",       self._drag_motion)

        # Fonts
        title_font  = tkfont.Font(family="Consolas", size=10, weight="bold")
        status_font = tkfont.Font(family="Consolas", size=14, weight="bold")
        text_font   = tkfont.Font(family="Consolas", size=9)

        # Header
        header = tk.Frame(root, bg="#111", pady=4)
        header.pack(fill="x")
        tk.Label(header, text="⬡  J A R V I S", bg="#111",
                 fg="#00e5ff", font=title_font).pack(side="left", padx=12)
        tk.Button(header, text="✕", bg="#111", fg="#555", relief="flat",
                  font=title_font, command=root.destroy,
                  activebackground="#111", activeforeground="#ff1744",
                  cursor="hand2").pack(side="right", padx=8)

        # Status row
        sf = tk.Frame(root, bg="#0a0a0a")
        sf.pack(fill="x", padx=12, pady=(6, 2))
        tk.Label(sf, text="STATUS", bg="#0a0a0a", fg="#444", font=text_font).pack(side="left")
        self._status_lbl = tk.Label(sf, text="Idle", bg="#0a0a0a",
                                    fg="#555555", font=status_font)
        self._status_lbl.pack(side="left", padx=8)

        # Divider
        tk.Frame(root, bg="#1e1e1e", height=1).pack(fill="x", padx=12)

        # Command row
        cf = tk.Frame(root, bg="#0a0a0a")
        cf.pack(fill="x", padx=12, pady=(3, 1))
        tk.Label(cf, text="CMD »", bg="#0a0a0a", fg="#444", font=text_font).pack(side="left")
        self._cmd_lbl = tk.Label(cf, text="—", bg="#0a0a0a",
                                 fg="#bdbdbd", font=text_font, wraplength=280, anchor="w")
        self._cmd_lbl.pack(side="left", padx=6)

        # Response row
        rf = tk.Frame(root, bg="#0a0a0a")
        rf.pack(fill="x", padx=12, pady=(1, 3))
        tk.Label(rf, text="ANS »", bg="#0a0a0a", fg="#444", font=text_font).pack(side="left")
        self._resp_lbl = tk.Label(rf, text="—", bg="#0a0a0a",
                                  fg="#69f0ae", font=text_font, wraplength=280, anchor="w")
        self._resp_lbl.pack(side="left", padx=6)

        # Text input row
        ef = tk.Frame(root, bg="#111", pady=2)
        ef.pack(fill="x", padx=10, pady=(2, 6))
        self._entry = tk.Entry(
            ef, bg="#181818", fg="#00e5ff", insertbackground="#00e5ff",
            font=text_font, relief="flat", highlightthickness=1,
            highlightbackground="#2a2a2a", highlightcolor="#00e5ff"
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(4, 4), ipady=2)
        self._entry.bind("<Return>", self._on_enter_pressed)

    def _on_enter_pressed(self, event=None):
        if not self._entry:
            return
        text = self._entry.get().strip()
        if text:
            self._entry.delete(0, tk.END)
            if self._on_submit:
                self._on_submit(text)

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_motion(self, event):
        root = self._root
        x = root.winfo_x() + (event.x - self._drag_x)
        y = root.winfo_y() + (event.y - self._drag_y)
        root.geometry(f"+{x}+{y}")

    def _poll(self):
        """Drain the queue and update labels; re-schedule every 50 ms."""
        try:
            while True:
                msg, val = self._q.get_nowait()
                if msg == "quit":
                    self._root.destroy()
                    return
                elif msg == "status":
                    color = STATUS_COLORS.get(val, "#ffffff")
                    self._status_lbl.config(text=val, fg=color)
                elif msg == "command":
                    self._cmd_lbl.config(text=val)
                elif msg == "response":
                    self._resp_lbl.config(text=val)
        except queue.Empty:
            pass
        self._root.after(80, self._poll)


# ─── System tray ──────────────────────────────────────────────────────────────

def start_tray(pause_fn: Callable, resume_fn: Callable, quit_fn: Callable):
    """
    Start the system tray icon in a background thread.
    Falls back gracefully if pystray / Pillow are unavailable.
    """
    try:
        import pystray                           # type: ignore
        from PIL import Image, ImageDraw         # type: ignore

        def _make_icon():
            from pathlib import Path
            base_dir = Path(__file__).resolve().parent.parent
            for icon_candidate in (base_dir / "jarvis.png", base_dir / "jarvis.ico"):
                if icon_candidate.exists():
                    try:
                        return Image.open(icon_candidate).resize((64, 64))
                    except Exception:
                        pass
            img = Image.new("RGBA", (64, 64), (10, 10, 10, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], fill=(0, 229, 255, 255))
            d.polygon([(32, 12), (52, 52), (12, 52)], fill=(10, 10, 10, 255))
            return img

        menu = pystray.Menu(
            pystray.MenuItem("Pause",  lambda icon, item: pause_fn()),
            pystray.MenuItem("Resume", lambda icon, item: resume_fn()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",   lambda icon, item: (quit_fn(), icon.stop())),
        )
        icon = pystray.Icon("JARVIS", _make_icon(), "JARVIS Assistant", menu)

        t = threading.Thread(target=icon.run, daemon=True)
        t.start()
        return icon

    except Exception as e:
        logger.warning(f"System tray not available: {e}")
        return None
