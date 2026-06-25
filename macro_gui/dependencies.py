import keyboard
import pyautogui

try:
    from pynput import keyboard as pynput_keyboard
    from pynput import mouse as pynput_mouse
    RECORDER_IMPORT_ERROR = None
except ImportError as exc:
    pynput_keyboard = None
    pynput_mouse = None
    RECORDER_IMPORT_ERROR = exc

try:
    import pyperclip
except ImportError:
    pyperclip = None