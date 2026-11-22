"""
control/spider_drone_client.py – Client interface connecting Jarvis to the 3D Spider Recon Drone.

Uses file-based IPC (no HTTP port issues on Windows):
  - Writes JSON command to %TEMP%/jarvis_spider_cmd.json
  - Drone polls this file every 200ms and executes the command
  - Checks %TEMP%/jarvis_spider_status.json to know if drone is alive
"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("jarvis.control.spider_drone_client")

# IPC files (must match paths in app.py)
_TEMP = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")))
IPC_CMD_FILE    = _TEMP / "jarvis_spider_cmd.json"
IPC_STATUS_FILE = _TEMP / "jarvis_spider_status.json"


# ── Drone status ─────────────────────────────────────────────────────────────

def is_drone_running() -> bool:
    return False


def ensure_drone_running() -> bool:
    # Permanently disabled - user requested clean screen scanning without tactical spider drone
    return False


def _send_cmd(cmd: dict):
    pass


def spider_walk_and_scan(
    target_x: int,
    target_y: int,
    desc: str = "",
    action: str = "click",
    wait_ms: int = 0,
):
    pass


def spider_scan_screen(desc: str = "Analyzing Screen Tasks"):
    pass


def spider_celebrate():
    pass


def spider_set_status(msg: str):
    pass
