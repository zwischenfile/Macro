GLOBAL_HOTKEY_RUN = "ctrl+1"
GLOBAL_HOTKEY_RECORD_STOP = "f8"
CLICK_DRAG_TOLERANCE = 5
DOUBLE_CLICK_INTERVAL = 0.35
DEFAULT_ACTION_POST_DELAY = 0.0
DEFAULT_RUNTIME_STEP_DELAY = 0.5
DEFAULT_RECORDER_WAIT_THRESHOLD = 0.7
DELAY_BYPASS_KEYS = {"alt", "ctrl"}
MODIFIER_KEYS = {"ctrl", "alt", "shift", "win"}
KEYPRESS_MODIFIER_ORDER = ("ctrl", "alt", "shift", "win")
MERGEABLE_SPECIAL_KEYPRESS_KEYS = {
    "backspace",
    "delete",
    "down",
    "end",
    "enter",
    "home",
    "left",
    "pagedown",
    "pageup",
    "right",
    "tab",
    "up",
}

VK_NUMPAD_MAP = {
    "<96>": "0",
    "<97>": "1",
    "<98>": "2",
    "<99>": "3",
    "<100>": "4",
    "<101>": "5",
    "<102>": "6",
    "<103>": "7",
    "<104>": "8",
    "<105>": "9",
    "<65437>": "5",
    "<110>": ".",
}

ACTION_DISPLAY_NAMES = {
    "label": "라벨",
    "click": "클릭 (좌표)",
    "move": "마우스 이동 (좌표)",
    "mouse_down": "마우스 누름",
    "mouse_up": "마우스 뗌",
    "scroll": "스크롤",
    "current_click": "클릭 (현재 위치)",
    "type": "텍스트 입력",
    "keypress": "단축키 실행",
    "key_down": "키 누름",
    "key_up": "키 뗌",
    "dynamic_date": "동적 날짜 입력",
    "serial_input": "일련번호 입력 (타이핑)",
    "serial_clipboard_copy": "일련번호 복사 및 붙여넣기",
    "clipboard_paste": "붙여넣기 (클립보드)",
    "capture": "화면 캡쳐",
    "wait": "대기",
}

BUTTON_LABELS = {
    "left": "좌클릭",
    "right": "우클릭",
    "middle": "중클릭",
}

EDITOR_ACTION_TYPES = [
    "label",
    "click",
    "scroll",
    "current_click",
    "type",
    "keypress",
    "key_down",
    "key_up",
    "dynamic_date",
    "serial_input",
    "serial_clipboard_copy",
    "clipboard_paste",
    "capture",
    "wait",
]

PYNPUT_TO_PYAUTOGUI_KEY = {
    "Key.alt": "alt",
    "Key.alt_l": "alt",
    "Key.alt_r": "alt",
    "Key.alt_gr": "alt",
    "Key.backspace": "backspace",
    "Key.caps_lock": "capslock",
    "Key.cmd": "win",
    "Key.cmd_l": "win",
    "Key.cmd_r": "win",
    "Key.ctrl": "ctrl",
    "Key.ctrl_l": "ctrl",
    "Key.ctrl_r": "ctrl",
    "Key.delete": "delete",
    "Key.down": "down",
    "Key.end": "end",
    "Key.enter": "enter",
    "Key.esc": "esc",
    "Key.home": "home",
    "Key.insert": "insert",
    "Key.left": "left",
    "Key.menu": "apps",
    "Key.num_lock": "numlock",
    "Key.page_down": "pagedown",
    "Key.page_up": "pageup",
    "Key.pause": "pause",
    "Key.print_screen": "printscreen",
    "Key.right": "right",
    "Key.scroll_lock": "scrolllock",
    "Key.shift": "shift",
    "Key.shift_l": "shift",
    "Key.shift_r": "shift",
    "Key.space": "space",
    "Key.tab": "tab",
    "Key.up": "up",
}
