"""
Offscreen YouTube Video Frame Streamer (isolated subprocess).
Runs QWebEngineView with WA_DontShowOnScreen so main.py never loads Chromium
and minimized/background YouTube tabs still stream live frames to Origin Island & Phone App.
"""
import json
import struct
import sys
import threading

from PySide6.QtCore import Qt, QTimer, QUrl, Signal, QObject
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
import PySide6.QtWebEngineWidgets  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402


class CommandBridge(QObject):
    load_video = Signal(str, int)
    quit_app = Signal()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    wv = QWebEngineView(None)
    wv.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
    wv.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    wv.resize(480, 270)
    wv.show()

    current_vid = [""]

    def _inject_clean(ok: bool):
        if not ok:
            return
        js = (
            "(function(){"
            "if(window.__ytCleanApplied)return; window.__ytCleanApplied=true;"
            "var s=document.createElement('style');"
            "s.textContent='html,body{overflow:hidden!important;background:#000!important;} "
            "ytd-masthead,#masthead-container,#secondary,#below,#comments,.ytp-chrome-top,.ytp-chrome-bottom,.ytp-watermark,.ytp-pause-overlay{display:none!important;} "
            "video{position:fixed!important;top:0!important;left:0!important;width:100vw!important;height:100vh!important;object-fit:cover!important;z-index:999999!important;}';"
            "if(document.head)document.head.appendChild(s);"
            "setInterval(function(){"
            "  var v=document.querySelector('video');"
            "  if(v){v.muted=true;if(v.paused)v.play().catch(function(){});}"
            "  var skip=document.querySelector('.ytp-skip-ad-button,.ytp-ad-skip-button');"
            "  if(skip)skip.click();"
            "},400);"
            "})();"
        )
        try:
            wv.page().runJavaScript(js)
        except Exception:
            pass

    wv.loadFinished.connect(_inject_clean)

    bridge = CommandBridge()

    def _on_load(vid: str, pos: int):
        if not vid:
            current_vid[0] = ""
            wv.setUrl(QUrl("about:blank"))
            return
        if vid != current_vid[0]:
            current_vid[0] = vid
            wv.setUrl(QUrl(f"https://www.youtube.com/watch?v={vid}&t={max(0, pos)}s"))

    bridge.load_video.connect(_on_load)
    bridge.quit_app.connect(app.quit)

    def _stdin_loop():
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    cmd = json.loads(line)
                    if cmd.get("quit"):
                        break
                    vid = str(cmd.get("video_id", "")).strip()
                    pos = int(cmd.get("pos", 0))
                    bridge.load_video.emit(vid, pos)
                except Exception:
                    pass
        except Exception:
            pass
        bridge.quit_app.emit()

    threading.Thread(target=_stdin_loop, daemon=True).start()

    out = sys.stdout.buffer

    def _grab_frame():
        if not current_vid[0]:
            return
        try:
            pix = wv.grab()
            if pix.isNull():
                return
            img = pix.toImage().convertToFormat(QImage.Format.Format_RGB888)
            w, h = img.width(), img.height()
            if w <= 0 or h <= 0:
                return
            # Copy tightly packed RGB rows (Qt QImage lines may have stride padding)
            bpl = img.bytesPerLine()
            ptr = img.constBits()
            raw = bytes(ptr)
            if bpl == w * 3:
                rgb = raw[: w * h * 3]
            else:
                rgb = b"".join(raw[y * bpl : y * bpl + w * 3] for y in range(h))
            hdr = struct.pack("<4sIII", b"YTFM", w, h, len(rgb))
            out.write(hdr + rgb)
            out.flush()
        except Exception:
            pass

    timer = QTimer()
    timer.setInterval(66)  # ~15 FPS
    timer.timeout.connect(_grab_frame)
    timer.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
