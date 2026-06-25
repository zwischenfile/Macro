import time

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .constants import (
    CLICK_DRAG_TOLERANCE,
    DEFAULT_ACTION_POST_DELAY,
    DEFAULT_RECORDER_WAIT_THRESHOLD,
    DOUBLE_CLICK_INTERVAL,
    GLOBAL_HOTKEY_RECORD_STOP,
    KEYPRESS_MODIFIER_ORDER,
    MERGEABLE_SPECIAL_KEYPRESS_KEYS,
    MODIFIER_KEYS,
)
from .dependencies import RECORDER_IMPORT_ERROR, pynput_keyboard, pynput_mouse
from .dialogs import ActionDialog, TextInsertDialog
from .utils import (
    build_action_label,
    normalize_delay,
    normalize_keypress_special_key,
    normalize_recorded_key,
    normalize_recorded_text,
    recorder_backend_available,
)


class MacroRecorderDialog(QDialog):
    recording_finished = pyqtSignal(list, str)
    recording_state_changed = pyqtSignal(bool)
    stop_requested = pyqtSignal()
    append_action_requested = pyqtSignal(object, float)

    def __init__(self, main_window):
        super().__init__(None)
        self.main_window = main_window
        self.setWindowTitle("기록기")
        self.setMinimumWidth(360)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.recording = False
        self.paused = False
        self.recorded_actions = []
        self.last_event_time = None
        self.mouse_press_positions = {}
        self.ignore_regions = []
        self.mouse_listener = None
        self.keyboard_listener = None
        self.resume_countdown = 0

        self.pressed_keys = set()
        self.held_modifiers = set()
        self.text_buffer = []
        self.last_click_info = None

        self.ignore_timer = QTimer(self)
        self.ignore_timer.setInterval(150)
        self.ignore_timer.timeout.connect(self._update_ignore_regions)

        self.target_label = QLabel("대상 매크로: -")
        self.status_label = QLabel(f"상태: 대기 중 (중지 단축키 {GLOBAL_HOTKEY_RECORD_STOP.upper()})")
        self.count_label = QLabel("기록 액션 수: 0")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("기존 액션 대체", "replace")
        self.mode_combo.addItem("기존 액션 뒤에 추가", "append")

        self.wait_threshold_spinbox = QDoubleSpinBox()
        self.wait_threshold_spinbox.setRange(0.1, 10.0)
        self.wait_threshold_spinbox.setSingleStep(0.1)
        self.wait_threshold_spinbox.setDecimals(2)
        self.wait_threshold_spinbox.setSuffix(" 초")
        self.wait_threshold_spinbox.setValue(DEFAULT_RECORDER_WAIT_THRESHOLD)

        self.start_btn = QPushButton("녹화 시작")
        self.stop_btn = QPushButton("녹화 중지")
        self.pause_btn = QPushButton("일시정지")
        self.resume_btn = QPushButton("재개")

        self.label_btn = QPushButton("라벨 추가")
        self.capture_btn = QPushButton("화면 캡쳐 추가")
        self.serial_input_btn = QPushButton("일련번호 입력 추가")
        self.serial_clipboard_btn = QPushButton("일련번호 복붙 추가")
        self.dynamic_date_btn = QPushButton("동적 날짜 추가")
        self.text_input_btn = QPushButton("텍스트 입력 추가")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.resume_btn)

        special_layout = QVBoxLayout()
        special_layout.addWidget(self.label_btn)
        special_layout.addWidget(self.text_input_btn)
        special_layout.addWidget(self.capture_btn)
        special_layout.addWidget(self.serial_input_btn)
        special_layout.addWidget(self.serial_clipboard_btn)
        special_layout.addWidget(self.dynamic_date_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.target_label)
        layout.addWidget(QLabel("기록 적용 방식:"))
        layout.addWidget(self.mode_combo)
        layout.addWidget(QLabel("대기 기록 기준:"))
        layout.addWidget(self.wait_threshold_spinbox)
        layout.addLayout(button_layout)
        layout.addLayout(special_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.count_label)
        self.setLayout(layout)

        self.start_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.pause_btn.clicked.connect(self.pause_recording)
        self.resume_btn.clicked.connect(self.resume_recording)
        self.label_btn.clicked.connect(self.insert_label_action)
        self.text_input_btn.clicked.connect(self.insert_text_action)
        self.capture_btn.clicked.connect(lambda: self.insert_special_action("capture"))
        self.serial_input_btn.clicked.connect(lambda: self.insert_special_action("serial_input"))
        self.serial_clipboard_btn.clicked.connect(lambda: self.insert_special_action("serial_clipboard_copy"))
        self.dynamic_date_btn.clicked.connect(lambda: self.insert_special_action("dynamic_date"))
        self.stop_requested.connect(self.stop_recording)
        self.append_action_requested.connect(self._append_action_from_thread)

        self._update_ui_state()
        self._update_ignore_regions()

    def set_target_profile(self, profile_name):
        self.target_label.setText(f"대상 매크로: {profile_name or '-'}")

    def _set_status(self, text):
        self.status_label.setText(f"상태: {text}")

    def _update_count_label(self):
        self.count_label.setText(f"기록 액션 수: {len(self.recorded_actions)}")

    def _update_ui_state(self):
        self.start_btn.setEnabled(not self.recording)
        self.stop_btn.setEnabled(self.recording)
        self.pause_btn.setEnabled(self.recording and not self.paused)
        self.resume_btn.setEnabled(self.recording and self.paused)
        for button in [
            self.label_btn,
            self.text_input_btn,
            self.capture_btn,
            self.serial_input_btn,
            self.serial_clipboard_btn,
            self.dynamic_date_btn,
        ]:
            button.setEnabled(self.recording)

    def _update_ignore_regions(self):
        widgets = [self, self.main_window]
        regions = []
        for widget in widgets:
            if widget is None or not widget.isVisible():
                continue
            rect = widget.frameGeometry()
            regions.append((rect.left(), rect.top(), rect.right(), rect.bottom()))
        self.ignore_regions = regions

    def _point_in_ignored_regions(self, x, y):
        for left, top, right, bottom in self.ignore_regions:
            if left <= x <= right and top <= y <= bottom:
                return True
        return False

    def _cleanup_listeners(self):
        for listener_name in ["mouse_listener", "keyboard_listener"]:
            listener = getattr(self, listener_name)
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
                setattr(self, listener_name, None)

    def _reset_intent_state(self):
        self.recorded_actions = []
        self.last_event_time = None
        self.mouse_press_positions.clear()
        self.pressed_keys.clear()
        self.held_modifiers.clear()
        self.text_buffer = []
        self.last_click_info = None

    def _wait_threshold(self):
        return normalize_delay(self.wait_threshold_spinbox.value())

    def _emit_action(self, payload, event_time=None):
        self.append_action_requested.emit(dict(payload), float(event_time or time.monotonic()))

    def _append_recorded_action(self, action, event_time=None, preserve_delay=False):
        action_copy = dict(action)
        action_copy.pop("_event", None)

        if not preserve_delay or action_copy.get("action") == "wait":
            action_copy.pop("post_delay", None)
        else:
            action_copy["post_delay"] = normalize_delay(action_copy.get("post_delay", 0.0))

        if action_copy.get("action") == "wait":
            action_copy["seconds"] = normalize_delay(action_copy.get("seconds", 0.0))

        action_copy["label"] = action_copy.get("label") or build_action_label(action_copy)
        self.recorded_actions.append(action_copy)
        if event_time is not None:
            self.last_event_time = event_time
        self._update_count_label()
        return len(self.recorded_actions) - 1

    def _append_wait_action(self, seconds):
        wait_seconds = normalize_delay(seconds)
        if wait_seconds <= 0:
            return

        if self.recorded_actions and self.recorded_actions[-1].get("action") == "wait":
            previous_action = self.recorded_actions[-1]
            previous_action["seconds"] = normalize_delay(previous_action.get("seconds", 0.0) + wait_seconds)
            previous_action["label"] = build_action_label(previous_action)
        else:
            self._append_recorded_action({"action": "wait", "seconds": wait_seconds})
        self.last_click_info = None

    def _flush_text_buffer(self):
        if not self.text_buffer:
            return

        text = "".join(self.text_buffer)
        self.text_buffer = []
        self._append_recorded_action({"action": "type", "text": text})
        self.last_click_info = None

    def _prepare_for_action(self, event_time, flush_text=True):
        if self.last_event_time is not None:
            idle_seconds = normalize_delay(event_time - self.last_event_time)
            if idle_seconds >= self._wait_threshold():
                self._flush_text_buffer()
                self._append_wait_action(idle_seconds)

        if flush_text:
            self._flush_text_buffer()

    def _can_merge_keypress(self, params):
        if not self.recorded_actions:
            return False

        previous_action = self.recorded_actions[-1]
        if previous_action.get("action") != "keypress":
            return False

        previous_params = previous_action.get("params", {})
        return (
            params.get("key") in MERGEABLE_SPECIAL_KEYPRESS_KEYS
            and previous_params.get("key") == params.get("key")
            and previous_params.get("special_key", "없음") == params.get("special_key", "없음")
        )

    def _record_keypress(self, key_name, event_time, modifiers=None):
        params = {
            "special_key": normalize_keypress_special_key(modifiers or []) or "없음",
            "key": key_name,
            "presses": 1,
            "interval": 0.0,
        }

        if self._can_merge_keypress(params):
            previous_action = self.recorded_actions[-1]
            previous_params = previous_action.setdefault("params", {})
            previous_params["presses"] = int(previous_params.get("presses", 1) or 1) + 1
            previous_params["interval"] = 0.0
            previous_action["label"] = build_action_label(previous_action)
        else:
            self._append_recorded_action({"action": "keypress", "params": params})

        self.last_event_time = event_time
        self.last_click_info = None

    def _record_scroll(self, dx, dy, event_time):
        if not dx and not dy:
            return

        self._prepare_for_action(event_time, flush_text=True)
        if self.recorded_actions and self.recorded_actions[-1].get("action") == "scroll":
            previous_action = self.recorded_actions[-1]
            previous_action["dx"] = int(previous_action.get("dx", 0)) + int(dx)
            previous_action["dy"] = int(previous_action.get("dy", 0)) + int(dy)
            previous_action["label"] = build_action_label(previous_action)
        else:
            self._append_recorded_action({
                "action": "scroll",
                "dx": int(dx),
                "dy": int(dy),
            })

        self.last_event_time = event_time
        self.last_click_info = None

    def _promote_to_double_click(self, x, y, button_name, event_time):
        if not self.last_click_info:
            return False

        if normalize_delay(event_time - self.last_click_info["event_time"]) > DOUBLE_CLICK_INTERVAL:
            return False
        if self.last_click_info["button"] != button_name:
            return False
        if abs(x - self.last_click_info["x"]) > CLICK_DRAG_TOLERANCE:
            return False
        if abs(y - self.last_click_info["y"]) > CLICK_DRAG_TOLERANCE:
            return False

        action_index = self.last_click_info["index"]
        if action_index >= len(self.recorded_actions):
            return False

        previous_action = self.recorded_actions[action_index]
        if previous_action.get("action") != "click" or previous_action.get("click_mode") != "single":
            return False

        previous_action["click_mode"] = "double"
        previous_action["x"] = x
        previous_action["y"] = y
        previous_action["label"] = build_action_label(previous_action)
        self.last_event_time = event_time
        self.last_click_info = {
            "index": action_index,
            "x": x,
            "y": y,
            "button": button_name,
            "event_time": event_time,
        }
        return True

    def _record_click(self, x, y, button_name, event_time):
        self._prepare_for_action(event_time, flush_text=True)
        if self._promote_to_double_click(x, y, button_name, event_time):
            return

        action_index = self._append_recorded_action({
            "action": "click",
            "x": x,
            "y": y,
            "button": button_name,
            "click_mode": "single",
        }, event_time=event_time)
        self.last_click_info = {
            "index": action_index,
            "x": x,
            "y": y,
            "button": button_name,
            "event_time": event_time,
        }

    def _ordered_modifiers(self):
        ordered = []
        for modifier in KEYPRESS_MODIFIER_ORDER:
            if modifier in self.held_modifiers:
                ordered.append(modifier)
        for modifier in sorted(self.held_modifiers):
            if modifier not in ordered:
                ordered.append(modifier)
        return ordered

    def _handle_key_press(self, key_name, typed_text, event_time):
        if key_name and key_name in self.pressed_keys:
            return
        if key_name:
            self.pressed_keys.add(key_name)

        if key_name in MODIFIER_KEYS:
            self.held_modifiers.add(key_name)
            return

        non_text_modifiers = {modifier for modifier in self.held_modifiers if modifier != "shift"}
        if typed_text is not None and not non_text_modifiers:
            self._prepare_for_action(event_time, flush_text=False)
            self.text_buffer.append(typed_text)
            self.last_event_time = event_time
            self.last_click_info = None
            return

        if not key_name:
            return

        self._prepare_for_action(event_time, flush_text=True)
        self._record_keypress(key_name, event_time, self._ordered_modifiers())

    def _handle_key_release(self, key_name):
        if not key_name:
            return
        self.pressed_keys.discard(key_name)
        if key_name in MODIFIER_KEYS:
            self.held_modifiers.discard(key_name)

    def _append_action_from_thread(self, payload, event_time):
        event_type = payload.get("_event")
        if not event_type:
            self._append_recorded_action(payload, event_time=event_time, preserve_delay=True)
            self.last_click_info = None
            return

        if event_type == "click":
            self._record_click(
                int(payload.get("x", 0)),
                int(payload.get("y", 0)),
                payload.get("button", "left"),
                event_time,
            )
            return

        if event_type == "scroll":
            self._record_scroll(
                int(payload.get("dx", 0)),
                int(payload.get("dy", 0)),
                event_time,
            )
            return

        if event_type == "key_press":
            self._handle_key_press(payload.get("key"), payload.get("text"), event_time)
            return

        if event_type == "key_release":
            self._handle_key_release(payload.get("key"))

    def _flush_before_pause_or_stop(self):
        self._flush_text_buffer()
        self.mouse_press_positions.clear()
        self.pressed_keys.clear()
        self.held_modifiers.clear()
        self.last_click_info = None

    def _begin_resume_countdown(self, prefix):
        self.paused = True
        self.resume_countdown = 3
        self._update_ui_state()

        def step():
            if not self.recording:
                return
            if self.resume_countdown <= 0:
                self.paused = False
                self.last_event_time = None
                self._update_ui_state()
                self._set_status(f"기록 중 ({GLOBAL_HOTKEY_RECORD_STOP.upper()} 로 중지)")
                return
            self._set_status(f"{prefix}: {self.resume_countdown}초 후 활성화")
            self.resume_countdown -= 1
            QTimer.singleShot(1000, step)

        step()

    def start_recording(self):
        if self.recording:
            return
        if not recorder_backend_available():
            QMessageBox.warning(
                self,
                "기록기 사용 불가",
                "입력 기록 기능에 필요한 'pynput' 패키지가 설치되어 있지 않습니다.\n\n"
                f"오류: {RECORDER_IMPORT_ERROR}",
            )
            return

        self._reset_intent_state()
        self.recording = True
        self.paused = True
        self.recording_state_changed.emit(True)
        self._update_count_label()
        self._update_ui_state()
        self._update_ignore_regions()
        self.ignore_timer.start()

        self.mouse_listener = pynput_mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
        self.keyboard_listener = pynput_keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self.mouse_listener.start()
        self.keyboard_listener.start()
        self.paused = False
        self._update_ui_state()
        self._set_status(f"기록 중 ({GLOBAL_HOTKEY_RECORD_STOP.upper()} 로 중지)")

    def pause_recording(self):
        if not self.recording or self.paused:
            return
        self._flush_before_pause_or_stop()
        self.paused = True
        self._update_ui_state()
        self._set_status("일시정지 중")

    def resume_recording(self):
        if not self.recording:
            return
        self._begin_resume_countdown("녹화 재개")

    def stop_recording(self):
        if not self.recording:
            return

        self.recording = False
        self.paused = False
        self.ignore_timer.stop()
        self._cleanup_listeners()
        self._flush_before_pause_or_stop()
        self._update_count_label()
        self._update_ui_state()
        self._set_status("기록 종료")
        self.recording_state_changed.emit(False)
        self.recording_finished.emit(list(self.recorded_actions), self.mode_combo.currentData())

    def insert_special_action(self, action_type):
        if not self.recording:
            QMessageBox.warning(self, "오류", "먼저 녹화를 시작해 주세요.")
            return

        self.pause_recording()
        dialog = ActionDialog(
            self,
            {"action": action_type, "post_delay": DEFAULT_ACTION_POST_DELAY},
            locked_action_type=action_type,
        )
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        if dialog.exec_() == QDialog.Accepted:
            action_data = dialog.get_data()
            if action_data:
                insert_time = self.last_event_time if self.last_event_time is not None else time.monotonic()
                self._append_action_from_thread(action_data, insert_time)
        self._begin_resume_countdown("특수 액션 삽입 후 재개")

    def insert_label_action(self):
        if not self.recording:
            QMessageBox.warning(self, "오류", "먼저 녹화를 시작해 주세요.")
            return

        self.pause_recording()
        dialog = ActionDialog(self, {"action": "label", "post_delay": 0.0}, locked_action_type="label")
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        if dialog.exec_() == QDialog.Accepted:
            action_data = dialog.get_data()
            if action_data:
                insert_time = self.last_event_time if self.last_event_time is not None else time.monotonic()
                self._append_action_from_thread(action_data, insert_time)
        self._begin_resume_countdown("라벨 삽입 후 재개")

    def insert_text_action(self):
        if not self.recording:
            QMessageBox.warning(self, "오류", "먼저 녹화를 시작해 주세요.")
            return

        self.pause_recording()
        dialog = TextInsertDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        if dialog.exec_() == QDialog.Accepted:
            action_data = dialog.get_data()
            insert_time = self.last_event_time if self.last_event_time is not None else time.monotonic()
            self._append_action_from_thread(action_data, insert_time)
        self._begin_resume_countdown("텍스트 액션 삽입 후 재개")

    def _on_click(self, x, y, button, pressed):
        if not self.recording or self.paused:
            return

        button_name = {
            pynput_mouse.Button.left: "left",
            pynput_mouse.Button.right: "right",
            pynput_mouse.Button.middle: "middle",
        }.get(button)
        if not button_name:
            return

        x = int(x)
        y = int(y)
        if pressed:
            if self._point_in_ignored_regions(x, y):
                return
            self.mouse_press_positions[button_name] = (x, y)
            return

        press_position = self.mouse_press_positions.pop(button_name, None)
        if press_position is None or self._point_in_ignored_regions(x, y):
            return

        moved_x = abs(x - press_position[0])
        moved_y = abs(y - press_position[1])
        if moved_x > CLICK_DRAG_TOLERANCE or moved_y > CLICK_DRAG_TOLERANCE:
            return

        self._emit_action({
            "_event": "click",
            "x": x,
            "y": y,
            "button": button_name,
        }, time.monotonic())

    def _on_scroll(self, x, y, dx, dy):
        if not self.recording or self.paused or self._point_in_ignored_regions(x, y):
            return
        self._emit_action({
            "_event": "scroll",
            "dx": int(dx),
            "dy": int(dy),
        }, time.monotonic())

    def _on_press(self, key):
        if not self.recording:
            return

        key_name = normalize_recorded_key(self.keyboard_listener, key)
        typed_text = normalize_recorded_text(self.keyboard_listener, key)
        if key_name == GLOBAL_HOTKEY_RECORD_STOP:
            self.stop_requested.emit()
            return
        if self.paused:
            return
        if not key_name and typed_text is None:
            return

        self._emit_action({
            "_event": "key_press",
            "key": key_name,
            "text": typed_text,
        }, time.monotonic())

    def _on_release(self, key):
        if not self.recording or self.paused:
            return

        key_name = normalize_recorded_key(self.keyboard_listener, key)
        if not key_name or key_name == GLOBAL_HOTKEY_RECORD_STOP:
            return

        self._emit_action({
            "_event": "key_release",
            "key": key_name,
        }, time.monotonic())

    def closeEvent(self, event):
        if self.recording:
            self.stop_recording()
        self._cleanup_listeners()
        self.recording_state_changed.emit(False)
        if self.main_window is not None:
            self.main_window.restore_after_recorder()
        super().closeEvent(event)
