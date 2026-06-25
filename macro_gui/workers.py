import os
import time
from datetime import datetime, timedelta

from PyQt5.QtCore import QObject, pyqtSignal

from .constants import DEFAULT_RUNTIME_STEP_DELAY, DELAY_BYPASS_KEYS
from .dependencies import pyautogui, pyperclip
from .utils import (
    compute_effective_post_delay,
    normalize_delay,
    sanitize_profile_name,
    split_keypress_parts,
)

class MacroWorker(QObject):
    finished = pyqtSignal()
    progress_update = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    request_serial_todo_update = pyqtSignal(str)
    request_serial_done_update = pyqtSignal(str, str)

    def __init__(
        self,
        actions,
        serial_todo_widget,
        serial_done_widget,
        profile_name="",
        base_path="",
        runtime_step_delay=DEFAULT_RUNTIME_STEP_DELAY,
    ):
        super().__init__()
        self.actions = actions
        self.serial_todo_widget = serial_todo_widget
        self.serial_done_widget = serial_done_widget
        self.profile_name = profile_name
        self.base_path = base_path
        self.runtime_step_delay = normalize_delay(runtime_step_delay)
        self.held_delay_bypass_keys = set()
        self.is_running = False
        self.stop_flag = False

    def run(self):
        self.is_running = True
        self.stop_flag = False

        for index, action_data in enumerate(self.actions):
            if self.stop_flag:
                break

            self.progress_update.emit(index)
            action_type = action_data.get("action")
            try:
                self._run_action(action_data)
            except Exception as exc:
                self.error_occurred.emit(f"{index + 1}번째 동작({action_type}) 실행 중 오류: {exc}")
                break

            delay_bypass = self._update_delay_bypass_state(action_data)
            post_delay = self._compute_action_post_delay(action_data, delay_bypass)
            if post_delay > 0:
                self._interruptible_sleep(post_delay)

        self.progress_update.emit(-1)
        self.is_running = False
        self.finished.emit()

    def _run_action(self, action_data):
        action_type = action_data.get("action")

        if action_type == "label":
            return

        if action_type == "click":
            pyautogui.click(
                x=action_data["x"],
                y=action_data["y"],
                button=action_data.get("button", "left"),
                clicks=2 if action_data.get("click_mode") == "double" else 1,
            )
            return

        if action_type == "move":
            pyautogui.moveTo(
                x=action_data["x"],
                y=action_data["y"],
                duration=max(float(action_data.get("duration", 0.25)), 0.0),
            )
            return

        if action_type == "mouse_down":
            pyautogui.mouseDown(
                x=action_data["x"],
                y=action_data["y"],
                button=action_data.get("button", "left"),
            )
            return

        if action_type == "mouse_up":
            pyautogui.mouseUp(
                x=action_data["x"],
                y=action_data["y"],
                button=action_data.get("button", "left"),
            )
            return

        if action_type == "scroll":
            dx = int(action_data.get("dx", 0))
            dy = int(action_data.get("dy", 0))
            if dy:
                pyautogui.scroll(dy)
            if dx and hasattr(pyautogui, "hscroll"):
                pyautogui.hscroll(dx)
            return

        if action_type == "type":
            pyautogui.typewrite(action_data.get("text", ""), interval=0.01)
            return

        if action_type == "wait":
            self._interruptible_sleep(float(action_data.get("seconds", 0)))
            return

        if action_type == "clipboard_paste":
            if pyperclip is None:
                raise RuntimeError("'pyperclip' 라이브러리가 설치되지 않았습니다.")
            pyperclip.copy(action_data.get("text", ""))
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
            return

        if action_type == "capture":
            save_dir = os.path.join(self.base_path, "Capture")
            os.makedirs(save_dir, exist_ok=True)
            now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_name = sanitize_profile_name(self.profile_name) or "Macro"
            pyautogui.screenshot(os.path.join(save_dir, f"{safe_name}-{now_str}.png"))
            return

        if action_type == "serial_input":
            todo_full_text = self.serial_todo_widget.toPlainText()
            done_full_text = self.serial_done_widget.toPlainText()
            lines = todo_full_text.splitlines()
            if not lines:
                return
            serial_to_type = lines.pop(0).strip()
            if serial_to_type:
                pyautogui.typewrite(serial_to_type, interval=0.01)
            self.request_serial_todo_update.emit("\n".join(lines))
            self.request_serial_done_update.emit(serial_to_type, done_full_text)
            time.sleep(0.1)
            return

        if action_type == "serial_clipboard_copy":
            if pyperclip is None:
                raise RuntimeError("'pyperclip' 라이브러리가 설치되지 않았습니다.")
            todo_full_text = self.serial_todo_widget.toPlainText()
            done_full_text = self.serial_done_widget.toPlainText()
            lines = todo_full_text.splitlines()
            if not lines:
                return
            serial_value = lines.pop(0).strip()
            if serial_value and action_data.get("params", {}).get("uppercase", False):
                serial_value = serial_value.upper()
            if serial_value:
                pyperclip.copy(serial_value)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
            self.request_serial_todo_update.emit("\n".join(lines))
            self.request_serial_done_update.emit(serial_value, done_full_text)
            time.sleep(0.1)
            return

        if action_type == "current_click":
            params = action_data.get("params", {})
            presses = int(params.get("presses", 1))
            interval = normalize_delay(params.get("interval", 0))
            for press_index in range(presses):
                if self.stop_flag:
                    break
                pyautogui.click()
                if press_index < presses - 1 and interval > 0:
                    self._interruptible_sleep(interval)
            return

        if action_type == "keypress":
            params = action_data.get("params", {})
            keys_to_press = split_keypress_parts(params)
            if not keys_to_press:
                return

            presses = int(params.get("presses", 1))
            interval = normalize_delay(params.get("interval", 0))
            for press_index in range(presses):
                if self.stop_flag:
                    break
                pyautogui.hotkey(*keys_to_press)
                if press_index < presses - 1 and interval > 0:
                    self._interruptible_sleep(interval)
            return

        if action_type == "key_down":
            key_name = action_data.get("key")
            if key_name:
                pyautogui.keyDown(key_name)
            return

        if action_type == "key_up":
            key_name = action_data.get("key")
            if key_name:
                pyautogui.keyUp(key_name)
            return

        if action_type == "dynamic_date":
            params = action_data.get("params", {})
            offset = int(params.get("offset", 0))
            date_format = params.get("format", "%Y-%m-%d")
            target_date = datetime.now() + timedelta(days=offset)
            pyautogui.typewrite(target_date.strftime(date_format), interval=0.01)
            return

        raise ValueError(f"지원하지 않는 액션 타입입니다: {action_type}")

    def _update_delay_bypass_state(self, action_data):
        action_type = action_data.get("action")
        if action_type == "key_down":
            key_name = action_data.get("key")
            if key_name in DELAY_BYPASS_KEYS:
                self.held_delay_bypass_keys.add(key_name)
        elif action_type == "key_up":
            key_name = action_data.get("key")
            if key_name in DELAY_BYPASS_KEYS:
                self.held_delay_bypass_keys.discard(key_name)
        return bool(self.held_delay_bypass_keys)

    def _compute_action_post_delay(self, action_data, delay_bypass):
        action_type = action_data.get("action")
        recorded_delay = normalize_delay(action_data.get("post_delay", 0.0))
        if action_type in ["label", "wait"]:
            return recorded_delay
        return compute_effective_post_delay(recorded_delay, self.runtime_step_delay, delay_bypass)

    def _interruptible_sleep(self, duration):
        sleep_end_time = time.time() + max(duration, 0.0)
        while time.time() < sleep_end_time:
            if self.stop_flag:
                break
            time.sleep(0.05)

    def stop(self):
        self.stop_flag = True


class SchedulerWorker(QObject):
    trigger_macro = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, target_datetime):
        super().__init__()
        self.target_datetime = target_datetime
        self.stop_flag = False

    def run(self):
        while not self.stop_flag:
            if datetime.now() >= self.target_datetime:
                self.trigger_macro.emit()
                break
            time.sleep(1)
        self.finished.emit()

    def stop(self):
        self.stop_flag = True
