"""
control/files.py – Sandboxed file operations.
All file I/O is restricted to ALLOWED_FILE_DIR (~/JarvisFiles) for safety.
"""

import logging
import os
import shutil
from pathlib import Path

from config import ALLOWED_FILE_DIR

logger = logging.getLogger("jarvis.control.files")


def _safe_path(relative_or_abs: str) -> Path:
    """
    Resolve the path and ensure it's inside ALLOWED_FILE_DIR.
    Raises ValueError if it escapes the sandbox.
    """
    p = Path(relative_or_abs)
    if not p.is_absolute():
        p = ALLOWED_FILE_DIR / p
    p = p.resolve()
    # Ensure it's within the allowed directory
    try:
        p.relative_to(ALLOWED_FILE_DIR.resolve())
    except ValueError:
        raise ValueError(
            f"Path '{relative_or_abs}' is outside the allowed directory "
            f"({ALLOWED_FILE_DIR}). I can only access files inside ~/JarvisFiles."
        )
    return p


def create_file(relative_path: str, content: str = "") -> str:
    """Create a file (and parent dirs) inside ~/JarvisFiles."""
    try:
        p = _safe_path(relative_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.info(f"Created file: {p}")
        return f"File created: {p}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error creating file: {e}"


def read_file(relative_path: str) -> str:
    """Read and return the content of a file."""
    try:
        p = _safe_path(relative_path)
        if not p.exists():
            return f"File not found: {p}"
        content = p.read_text(encoding="utf-8")
        logger.info(f"Read file: {p}")
        return content
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(relative_path: str, content: str) -> str:
    """Overwrite (or create) a file with the given content."""
    try:
        p = _safe_path(relative_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.info(f"Wrote file: {p}")
        return f"File saved: {p}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error writing file: {e}"


def append_file(relative_path: str, content: str) -> str:
    """Append content to an existing file."""
    try:
        p = _safe_path(relative_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to file: {p}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error appending to file: {e}"


def delete_file(relative_path: str) -> str:
    """Delete a file. Caller MUST obtain confirmation before calling."""
    try:
        p = _safe_path(relative_path)
        if not p.exists():
            return f"File not found: {p}"
        if p.is_dir():
            shutil.rmtree(p)
            return f"Deleted directory: {p}"
        p.unlink()
        logger.info(f"Deleted: {p}")
        return f"Deleted: {p}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error deleting: {e}"


def move_file(src: str, dst: str) -> str:
    """Move/rename a file within the sandbox."""
    try:
        src_p = _safe_path(src)
        dst_p = _safe_path(dst)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_p), str(dst_p))
        return f"Moved {src_p.name} → {dst_p}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error moving file: {e}"


def list_files(relative_path: str = ".") -> str:
    """List files in a directory inside the sandbox."""
    try:
        p = _safe_path(relative_path)
        if not p.exists():
            return f"Directory not found: {p}"
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = [f"Contents of {p}:"]
        for entry in entries[:50]:
            icon = "📁" if entry.is_dir() else "📄"
            lines.append(f"  {icon} {entry.name}")
        return "\n".join(lines)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error listing directory: {e}"


def create_folder(relative_path: str) -> str:
    try:
        p = _safe_path(relative_path)
        p.mkdir(parents=True, exist_ok=True)
        return f"Folder created: {p}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error creating folder: {e}"
