"""
memory.py – Persistent user memory (name, preferences) and session history.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

from config import MEMORY_FILE

logger = logging.getLogger("jarvis.memory")

# ─── Default memory schema ────────────────────────────────────────────────────
_DEFAULT: dict[str, Any] = {
    "user_name":    "friend",
    "preferences":  {},
    "facts":        [],         # ["User likes dark mode", ...]
    "created_at":   "",
    "last_seen":    "",
}


class Memory:
    """
    Thin wrapper around a JSON file for persistent facts,
    plus an in-process session message history for Claude.
    """

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._session_messages: list[dict] = []   # Claude conversation turns
        self.load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def load(self):
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info("Memory loaded from disk.")
            except Exception as e:
                logger.warning(f"Could not load memory: {e}. Starting fresh.")
                self._data = dict(_DEFAULT)
        else:
            self._data = dict(_DEFAULT)
            self._data["created_at"] = datetime.now().isoformat()

        self._data["last_seen"] = datetime.now().isoformat()
        self.save()

    def save(self):
        try:
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save memory: {e}")

    # ── Getters / setters ─────────────────────────────────────────────────────

    @property
    def user_name(self) -> str:
        return self._data.get("user_name", "friend")

    @user_name.setter
    def user_name(self, name: str):
        self._data["user_name"] = name
        self.save()

    def get_preference(self, key: str, default=None):
        return self._data.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value):
        self._data.setdefault("preferences", {})[key] = value
        self.save()

    def add_fact(self, fact: str):
        """Remember an arbitrary fact about the user."""
        facts = self._data.setdefault("facts", [])
        if fact not in facts:
            facts.append(fact)
            self.save()

    def get_facts(self) -> list[str]:
        return self._data.get("facts", [])

    def summary_for_system_prompt(self) -> str:
        """Return a brief string to inject into the Claude system prompt."""
        name = self.user_name
        facts = self.get_facts()
        lines = [f"The user's name is {name}."]
        if facts:
            lines.append("Known facts about the user:")
            for f in facts:
                lines.append(f"  - {f}")
        return "\n".join(lines)

    # ── Session message history ────────────────────────────────────────────────

    def add_turn(self, role: str, content):
        """
        Append a message to the in-session history.

        Accepts two calling conventions:
          1. add_turn("user", "some text")
             → stores {"role": "user", "content": "some text"}

          2. add_turn("assistant", {full dict with tool_calls etc.})
             → stores the dict directly (the dict already has "role" inside)

          3. add_turn("tool", {tool_result dict})
             → stores the dict directly
        """
        if isinstance(content, dict) and "role" in content:
            # Full message dict already — store as-is
            msg = content
        elif isinstance(content, list):
            # List of tool-result dicts (used in some older patterns)
            # Wrap each one individually
            for item in content:
                if isinstance(item, dict) and "role" in item:
                    self._session_messages.append(item)
                else:
                    self._session_messages.append({"role": role, "content": item})
            self._trim()
            return
        else:
            msg = {"role": role, "content": content}

        self._session_messages.append(msg)
        self._trim()

    def _trim(self):
        """Keep last 40 messages to avoid token overflow."""
        if len(self._session_messages) > 40:
            self._session_messages = self._session_messages[-40:]

    def get_session_messages(self) -> list[dict]:
        return list(self._session_messages)

    def clear_session(self):
        self._session_messages.clear()
        logger.info("Session history cleared.")
