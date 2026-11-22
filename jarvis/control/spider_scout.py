"""
control/spider_scout.py – Jarvis Autonomous Spider Vision Scout.

Autonomous screen perception and hands-free action executor:
1. Captures screen frames.
2. Uses Multimodal Vision (NVIDIA Vision NIM / OpenAI compatible / Windows OCR)
   to understand what application is active, what task needs doing, and where elements are.
3. Autonomously controls keyboard and mouse to perform the actions hands-free.
4. Triggers Spider Mech scanning animations (blue laser cone, 360 radar) and status bubbles.
5. Failsafe: moving mouse to corner or pressing ESC instantly stops autonomy.
"""

import os
import sys
import time
import json
import logging
import threading
from typing import Optional, Callable

import pyautogui

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_VISION_MODEL
from control.keyboard_mouse import ensure_desktop_attached, _clamp_coords
from control.vision import _take_screenshot, ocr_find_text_on_screen, uia_find_element

logger = logging.getLogger("jarvis.control.spider_scout")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.12


AUTONOMOUS_VISION_PROMPT = """
You are the JARVIS Autonomous Spider Scout with vision capabilities.
You are watching the user's computer screen to assist them hands-free without them touching mouse or keyboard.

User's goal/instruction: "{goal}"

Screen width: {width}, height: {height}.
Current active context on screen:
1. Identify the application, window, dialog, or webpage currently visible.
2. Determine if there is an actionable task, pending prompt, button to click, form to fill, or code/command to execute.
3. Return ONLY a valid JSON object in this exact format:
{{
  "task_state": "acting" | "observing" | "completed" | "waiting",
  "reasoning": "<Concise 1-sentence analysis of what is on screen and what action to take>",
  "actions": [
    {{
      "type": "click" | "double_click" | "right_click" | "type" | "hotkey" | "wait",
      "target_description": "<description of button or element to click or focus>",
      "text": "<text to type if type action>",
      "keys": ["<key1>", "<key2>"] // e.g. ["ctrl", "s"] or ["enter"]
    }}
  ],
  "speech": "<Short spoken update for the user, e.g. 'Clicking Run Code for you, sir.'>",
  "spider_animation": "scan" | "idea" | "happy" | "idle"
}}

If the task is completed or no action should be taken right now, set "actions": [] and "task_state": "observing" or "completed".
Output ONLY pure JSON. No markdown backticks.
"""


class SpiderScout:
    """Singleton Autonomous Spider Vision Scout."""

    _instance: Optional["SpiderScout"] = None

    @classmethod
    def instance(cls) -> "SpiderScout":
        if cls._instance is None:
            cls._instance = SpiderScout()
        return cls._instance

    def __init__(self):
        self.is_active = False
        self._thread: Optional[threading.Thread] = None
        self._goal = "Assist the user with their current desktop task hands-free"
        self._status_callback: Optional[Callable[[str], None]] = None
        self._speak_callback: Optional[Callable[[str], None]] = None
        self._pet_callback: Optional[Callable[[str], None]] = None

        # Setup client
        from openai import OpenAI
        self.client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)

    def set_callbacks(
        self,
        status_fn: Optional[Callable[[str], None]] = None,
        speak_fn: Optional[Callable[[str], None]] = None,
        pet_anim_fn: Optional[Callable[[str], None]] = None,
    ):
        """Connect UI and speech callbacks."""
        self._status_callback = status_fn
        self._speak_callback = speak_fn
        self._pet_callback = pet_anim_fn

    def start_scout(self, goal: str = "Assist user with current on-screen task"):
        """Activates autonomous vision loop."""
        if self.is_active:
            self._goal = goal
            logger.info(f"Spider Scout goal updated: {goal}")
            return "Spider Scout is already active. Updated objective."

        self.is_active = True
        self._goal = goal
        self._thread = threading.Thread(target=self._scout_loop, daemon=True)
        self._thread.start()
        logger.info(f"Spider Scout activated for goal: {goal}")
        
        if self._pet_callback:
            self._pet_callback("scan")

        return f"Autonomous Spider Scout deployed. I will scan your screen and perform actions hands-free."

    def stop_scout(self):
        """Deactivates autonomous scout."""
        self.is_active = False
        if self._pet_callback:
            self._pet_callback("idle")
        if self._status_callback:
            self._status_callback("Spider Scout Idle")
        logger.info("Spider Scout stopped.")
        return "Spider Scout has stood down."

    def scan_once_and_act(self, goal: str = "Analyze screen and assist") -> str:
        """Runs a single perception-action cycle immediately."""
        self._goal = goal
        return self._execute_cycle()

    def _execute_cycle(self) -> str:
        """Captures screen, asks Vision model, and executes actions."""
        ensure_desktop_attached()
        if self._pet_callback:
            self._pet_callback("scan")

        if self._status_callback:
            self._status_callback("Spider Scout: Scanning screen...")

        # 1. Take screenshot
        scaled_img, b64, (orig_w, orig_h), (screen_w, screen_h) = _take_screenshot()
        if not scaled_img or not b64:
            return "Unable to capture screen."

        # 2. Query Multimodal Vision
        prompt = AUTONOMOUS_VISION_PROMPT.format(
            goal=self._goal,
            width=screen_w,
            height=screen_h
        )

        try:
            response = self.client.chat.completions.create(
                model=NVIDIA_VISION_MODEL,
                temperature=0.1,
                max_tokens=600,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            raw = response.choices[0].message.content.strip()
            # Clean possible markdown or preamble wrap
            from brain.agent import _extract_first_json_object
            data = _extract_first_json_object(raw)
            if not data:
                if raw.startswith("```json"):
                    raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
                elif raw.startswith("```"):
                    raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
                data = json.loads(raw)
        except Exception as e:
            logger.error(f"Vision cycle error: {e}")
            if self._pet_callback:
                self._pet_callback("idle")
            return f"Vision scan failed: {e}"

        reasoning = data.get("reasoning", "")
        speech = data.get("speech", "")
        actions = data.get("actions", [])
        anim = data.get("spider_animation", "idle")
        task_state = data.get("task_state", "observing")

        logger.info(f"Spider Reason: {reasoning}")
        if self._status_callback:
            self._status_callback(f"Spider: {reasoning}")

        if speech and self._speak_callback:
            self._speak_callback(speech)

        # 3. Execute actions hands-free
        if actions:
            if self._pet_callback:
                self._pet_callback("work")

            for act in actions:
                if not self.is_active:
                    break
                self._dispatch_action(act, screen_w, screen_h)

        # 4. Handle state transition
        if task_state == "completed":
            if self._pet_callback:
                self._pet_callback("happy")
            return f"Spider completed the task: {reasoning}"
        else:
            if self._pet_callback:
                self._pet_callback(anim)
            return f"Spider observation: {reasoning}"

    def _dispatch_action(self, act: dict, screen_w: int, screen_h: int):
        act_type = act.get("type")
        target_desc = act.get("target_description", "")
        text = act.get("text", "")
        keys = act.get("keys", [])

        # Find coordinates if target element is specified
        target_pt = None
        if target_desc:
            # Try Windows OCR first
            target_pt = ocr_find_text_on_screen(target_desc)
            if not target_pt:
                # Try UIAutomation
                target_pt = uia_find_element(target_desc)

        if act_type in ("click", "double_click", "right_click"):
            if target_pt:
                cx, cy = target_pt
                try:
                    from control.spider_drone_client import spider_walk_and_scan, spider_celebrate
                    spider_walk_and_scan(cx, cy, desc=target_desc, action=act_type)
                except Exception:
                    pass
                pyautogui.moveTo(cx, cy, duration=0.45, tween=pyautogui.easeOutQuad)
                time.sleep(0.08)
                if act_type == "click":
                    pyautogui.click()
                elif act_type == "double_click":
                    pyautogui.doubleClick()
                elif act_type == "right_click":
                    pyautogui.rightClick()
                try:
                    spider_celebrate()
                except Exception:
                    pass
                logger.info(f"Spider executed {act_type} on '{target_desc}' at ({cx}, {cy})")
            elif target_desc:
                # Fallback to full 3-tier vision locator (OCR + UIA + AI Vision)
                from control.vision import click_element_by_description
                logger.info(f"Spider dispatching to vision locator for '{target_desc}'")
                click_element_by_description(target_desc)

        elif act_type == "type":
            if target_pt:
                cx, cy = target_pt
                try:
                    from control.spider_drone_client import spider_walk_and_scan
                    spider_walk_and_scan(cx, cy, desc=target_desc, action="type")
                except Exception:
                    pass
                pyautogui.click(cx, cy)
                time.sleep(0.1)
            if text:
                pyautogui.write(text, interval=0.035)
                logger.info(f"Spider typed: '{text}'")

        elif act_type == "hotkey" and keys:
            pyautogui.hotkey(*keys)
            logger.info(f"Spider pressed hotkey: {keys}")

        elif act_type == "wait":
            time.sleep(act.get("duration", 1.0))

    def _scout_loop(self):
        """Continuous background autonomous assistance loop."""
        while self.is_active:
            try:
                self._execute_cycle()
                # Cooldown between scans
                time.sleep(3.5)
            except pyautogui.FailSafeException:
                logger.warning("PyAutoGUI Failsafe triggered! Halting Spider Scout.")
                self.stop_scout()
                if self._speak_callback:
                    self._speak_callback("Failsafe detected. Spider Scout deactivated.")
                break
            except Exception as e:
                logger.error(f"Error in scout loop: {e}")
                time.sleep(4.0)

