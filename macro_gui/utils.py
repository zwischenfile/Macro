import os
import sys

from .constants import (
    ACTION_DISPLAY_NAMES,
    BUTTON_LABELS,
    KEYPRESS_MODIFIER_ORDER,
    PYNPUT_TO_PYAUTOGUI_KEY,
    VK_NUMPAD_MAP,
)
from .dependencies import pyautogui, pynput_keyboard, pynput_mouse

def default_script_folder():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_Script")


def normalize_delay(value):
    return round(max(float(value), 0.0), 2)


def sanitize_profile_name(name):
    return "".join(c for c in str(name).strip() if c not in '<>:"/\\|?*').strip()


def strip_wrapped_quotes(value):
    if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def normalize_recorded_key(listener, key):
    key_pressed = get_key_pressed(listener, key)
    if key_pressed is None:
        return None

    if ">" in key_pressed:
        key_pressed = VK_NUMPAD_MAP.get(key_pressed, key_pressed)

    key_pressed = PYNPUT_TO_PYAUTOGUI_KEY.get(key_pressed, key_pressed)
    if isinstance(key_pressed, str) and key_pressed.startswith("Key.f"):
        key_pressed = key_pressed.replace("Key.", "")
    elif isinstance(key_pressed, str) and key_pressed.startswith("Key."):
        key_pressed = key_pressed[4:]

    key_pressed = strip_wrapped_quotes(key_pressed)
    if key_pressed in pyautogui.KEYBOARD_KEYS:
        return key_pressed

    lowered = str(key_pressed).lower()
    return lowered if lowered in pyautogui.KEYBOARD_KEYS else None


def normalize_recorded_text(listener, key):
    key_pressed = get_key_pressed(listener, key)
    if key_pressed is None:
        return None

    if ">" in key_pressed:
        key_pressed = VK_NUMPAD_MAP.get(key_pressed, key_pressed)

    if key_pressed == "Key.space":
        return " "
    if isinstance(key_pressed, str) and key_pressed.startswith("Key."):
        return None

    text = strip_wrapped_quotes(key_pressed)
    if isinstance(text, str) and len(text) == 1 and text.isprintable():
        return text
    return None


def recorder_backend_available():
    return pynput_keyboard is not None and pynput_mouse is not None


def get_key_pressed(keyboard_listener, key):
    key_repr = str(key)
    if "Key." in key_repr:
        return key_repr

    if sys.platform.lower() == "win32":
        key_chars = list(str(keyboard_listener.canonical(key)))
    else:
        key_chars = list(key_repr)

    if key_chars and key_chars[0] != "<":
        key_chars[0] = ""
        key_chars[-1] = ""

    key_pressed = "".join(key_chars)
    if sys.platform.lower() == "darwin":
        if key_pressed == "\\x03":
            return "Key.enter"
        if key_pressed == "\\x1b":
            return None
    elif sys.platform.lower() == "linux" and key_pressed == "'^'":
        return "^"

    return key_pressed


def compute_effective_post_delay(recorded_delay, runtime_delay, delay_bypass):
    recorded_delay = normalize_delay(recorded_delay)
    runtime_delay = normalize_delay(runtime_delay)
    if delay_bypass:
        return recorded_delay
    return normalize_delay(max(recorded_delay, runtime_delay))


def split_keypress_parts(params):
    parts = []
    special_key = str(params.get("special_key", "") or "").strip()
    if special_key and special_key != "없음":
        parts.extend(part.strip() for part in special_key.split("+") if part.strip())

    key_name = str(params.get("key", "") or "").strip()
    if key_name:
        parts.append(key_name)
    return parts


def normalize_keypress_special_key(modifiers):
    ordered = []
    modifier_set = {str(modifier).strip() for modifier in modifiers if str(modifier).strip()}
    for modifier in KEYPRESS_MODIFIER_ORDER:
        if modifier in modifier_set:
            ordered.append(modifier)
    for modifier in sorted(modifier_set):
        if modifier not in ordered:
            ordered.append(modifier)
    return "+".join(ordered)


def format_keypress_label(params):
    parts = split_keypress_parts(params)
    if not parts:
        return ACTION_DISPLAY_NAMES["keypress"]

    label = "+".join(parts)
    presses = int(params.get("presses", 1) or 1)
    return f"{label} × {presses}" if presses > 1 else label


def build_action_label(action_data):
    action_type = action_data.get("action")

    if action_type == "label":
        text = action_data.get("text", "").strip()
        return f"라벨: {text}" if text else "라벨"

    if action_type == "click":
        button_name = action_data.get("button", "left")
        button_label = "클릭" if button_name == "left" else BUTTON_LABELS.get(button_name, "클릭")
        click_mode = action_data.get("click_mode", "single")
        if click_mode == "double":
            button_label = "더블클릭" if button_name == "left" else f"{button_label} 더블"
        return f"{button_label} ({action_data.get('x')}, {action_data.get('y')})"

    if action_type == "move":
        duration = action_data.get("duration", 0.0)
        duration_suffix = f", 이동 {duration}초" if duration else ""
        return f"{ACTION_DISPLAY_NAMES[action_type]} ({action_data.get('x')}, {action_data.get('y')}){duration_suffix}"

    if action_type in ["mouse_down", "mouse_up"]:
        button_label = BUTTON_LABELS.get(action_data.get("button", "left"), "마우스")
        state_label = "누름" if action_type == "mouse_down" else "뗌"
        return f"{button_label} {state_label} ({action_data.get('x')}, {action_data.get('y')})"

    if action_type == "scroll":
        return f"{ACTION_DISPLAY_NAMES[action_type]} (dx={action_data.get('dx', 0)}, dy={action_data.get('dy', 0)})"

    if action_type == "current_click":
        params = action_data.get("params", {})
        presses = params.get("presses", 1)
        return f"{ACTION_DISPLAY_NAMES[action_type]} × {presses}" if presses > 1 else ACTION_DISPLAY_NAMES[action_type]

    if action_type in ["type", "clipboard_paste"]:
        text = action_data.get("text", "")
        preview = text.replace("\n", "\\n")
        preview = preview[:20] + "..." if len(preview) > 20 else preview
        return f"텍스트: {preview}" if action_type == "type" else f"{ACTION_DISPLAY_NAMES[action_type]}: {preview}"

    if action_type == "keypress":
        return format_keypress_label(action_data.get("params", {}))

    if action_type in ["key_down", "key_up"]:
        state_label = "누름" if action_type == "key_down" else "뗌"
        return f"키 {state_label}: {action_data.get('key', '')}"

    if action_type == "dynamic_date":
        params = action_data.get("params", {})
        offset = params.get("offset", 0)
        offset_text = f"+{offset}" if offset >= 0 else str(offset)
        return f"{ACTION_DISPLAY_NAMES[action_type]}: 오늘 {offset_text}일 ({params.get('format', '%Y-%m-%d')})"

    if action_type == "serial_clipboard_copy":
        option = " (대문자)" if action_data.get("params", {}).get("uppercase") else ""
        return f"{ACTION_DISPLAY_NAMES[action_type]}{option}"

    if action_type in ["serial_input", "capture"]:
        return ACTION_DISPLAY_NAMES[action_type]

    if action_type == "wait":
        return f"{ACTION_DISPLAY_NAMES[action_type]} {action_data.get('seconds', 0)}초"

    return action_data.get("label", action_type or "동작")
