from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .constants import ACTION_DISPLAY_NAMES, DEFAULT_ACTION_POST_DELAY, EDITOR_ACTION_TYPES
from .dependencies import pyautogui, pyperclip
from .utils import build_action_label, normalize_delay

class ActionDialog(QDialog):
    def __init__(self, parent=None, action_data=None, locked_action_type=None):
        super().__init__(parent)
        self.setWindowTitle("동작 추가/수정")
        self.setMinimumWidth(500)
        self.locked_action_type = locked_action_type
        self.action_map = {action: ACTION_DISPLAY_NAMES[action] for action in EDITOR_ACTION_TYPES}
        if action_data:
            legacy_action_type = action_data.get("action")
            if legacy_action_type in ACTION_DISPLAY_NAMES and legacy_action_type not in self.action_map:
                self.action_map[legacy_action_type] = ACTION_DISPLAY_NAMES[legacy_action_type]
        if self.locked_action_type and self.locked_action_type not in self.action_map:
            self.action_map[self.locked_action_type] = ACTION_DISPLAY_NAMES[self.locked_action_type]
        self.reverse_action_map = {value: key for key, value in self.action_map.items()}

        self.form_layout = QFormLayout()
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(self.action_map.values())

        self.label_input = QLineEdit()

        self.post_delay_spinbox = QDoubleSpinBox()
        self.post_delay_spinbox.setRange(0.0, 300.0)
        self.post_delay_spinbox.setSingleStep(0.1)
        self.post_delay_spinbox.setDecimals(2)
        self.post_delay_spinbox.setSuffix(" 초")
        self.post_delay_spinbox.setValue(DEFAULT_ACTION_POST_DELAY)

        self.x_input = QSpinBox()
        self.x_input.setRange(0, 99999)
        self.y_input = QSpinBox()
        self.y_input.setRange(0, 99999)

        self.coord_label = QLabel("현재 마우스 위치: (0, 0)")
        self.get_coord_btn = QPushButton("현재 위치 가져오기")
        self.get_coord_btn.clicked.connect(self._capture_mouse_pos)
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(self.coord_label)
        coord_layout.addStretch()
        coord_layout.addWidget(self.get_coord_btn)
        self.coord_widget = QWidget()
        self.coord_widget.setLayout(coord_layout)
        self.coord_timer = QTimer(self)
        self.coord_timer.setInterval(100)
        self.coord_timer.timeout.connect(self._update_mouse_pos)

        self.mouse_button_combo = QComboBox()
        self.mouse_button_combo.addItems(["left", "right", "middle"])

        self.click_mode_combo = QComboBox()
        self.click_mode_combo.addItem("single", "single")
        self.click_mode_combo.addItem("double", "double")

        self.move_duration_spinbox = QDoubleSpinBox()
        self.move_duration_spinbox.setRange(0.0, 30.0)
        self.move_duration_spinbox.setSingleStep(0.05)
        self.move_duration_spinbox.setDecimals(2)
        self.move_duration_spinbox.setSuffix(" 초")
        self.move_duration_spinbox.setValue(0.25)

        self.scroll_dx_spinbox = QSpinBox()
        self.scroll_dx_spinbox.setRange(-1000, 1000)
        self.scroll_dy_spinbox = QSpinBox()
        self.scroll_dy_spinbox.setRange(-1000, 1000)
        scroll_layout = QHBoxLayout()
        scroll_layout.addWidget(QLabel("DX"))
        scroll_layout.addWidget(self.scroll_dx_spinbox)
        scroll_layout.addWidget(QLabel("DY"))
        scroll_layout.addWidget(self.scroll_dy_spinbox)
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(scroll_layout)

        self.text_input = QLineEdit()

        self.single_key_combo = QComboBox()
        self.single_key_combo.setEditable(True)
        self.single_key_combo.addItems(sorted(pyautogui.KEYBOARD_KEYS))

        priority_keys = [
            "ctrl", "alt", "shift", "enter", "esc", "tab", "backspace", "delete",
            "space", "win", "home", "end", "pageup", "pagedown", "up", "down",
            "left", "right",
        ] + [f"f{i}" for i in range(1, 13)]
        ordered_keys = priority_keys + [key for key in sorted(pyautogui.KEYBOARD_KEYS) if key not in priority_keys]
        self.special_key_combo = QComboBox()
        self.special_key_combo.setEditable(True)
        self.special_key_combo.addItem("없음")
        self.special_key_combo.addItems(ordered_keys)

        self.additional_key_input = QLineEdit()
        self.additional_key_input.setPlaceholderText("추가 키 (예: c)")

        self.keypress_count_spinbox = QSpinBox()
        self.keypress_count_spinbox.setRange(1, 1000)
        self.keypress_count_spinbox.setSuffix(" 회")
        self.keypress_count_spinbox.setValue(1)

        self.repetition_interval_spinbox = QDoubleSpinBox()
        self.repetition_interval_spinbox.setRange(0.0, 300.0)
        self.repetition_interval_spinbox.setSingleStep(0.1)
        self.repetition_interval_spinbox.setDecimals(2)
        self.repetition_interval_spinbox.setSuffix(" 초")
        self.repetition_interval_spinbox.setValue(0.1)

        keypress_layout = QHBoxLayout()
        keypress_layout.addWidget(self.special_key_combo)
        keypress_layout.addWidget(self.additional_key_input)
        keypress_layout.addWidget(self.keypress_count_spinbox)
        self.keypress_widget = QWidget()
        self.keypress_widget.setLayout(keypress_layout)

        self.current_click_count_spinbox = QSpinBox()
        self.current_click_count_spinbox.setRange(1, 1000)
        self.current_click_count_spinbox.setSuffix(" 회")
        self.current_click_count_spinbox.setValue(1)

        self.date_offset_spinbox = QSpinBox()
        self.date_offset_spinbox.setRange(-3650, 3650)
        self.date_offset_spinbox.setSuffix(" 일")
        self.date_format_input = QLineEdit("%Y-%m-%d")
        date_layout = QVBoxLayout()
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.addWidget(self.date_offset_spinbox)
        date_layout.addWidget(self.date_format_input)
        self.dynamic_date_widget = QWidget()
        self.dynamic_date_widget.setLayout(date_layout)

        self.seconds_input = QDoubleSpinBox()
        self.seconds_input.setRange(0.0, 3600.0)
        self.seconds_input.setSingleStep(0.1)
        self.seconds_input.setDecimals(2)
        self.seconds_input.setSuffix(" 초")
        self.seconds_input.setValue(0.5)

        self.uppercase_checkbox = QCheckBox("대문자로 변환")

        self.form_layout.addRow("동작 유형:", self.action_type_combo)
        self.form_layout.addRow("레이블:", self.label_input)
        self.form_layout.addRow("실행 후 지연:", self.post_delay_spinbox)
        self.form_layout.addRow("X 좌표:", self.x_input)
        self.form_layout.addRow("Y 좌표:", self.y_input)
        self.form_layout.addRow(self.coord_widget)
        self.form_layout.addRow("마우스 버튼:", self.mouse_button_combo)
        self.form_layout.addRow("클릭 방식:", self.click_mode_combo)
        self.form_layout.addRow("이동 시간:", self.move_duration_spinbox)
        self.form_layout.addRow("스크롤:", self.scroll_widget)
        self.form_layout.addRow("텍스트:", self.text_input)
        self.form_layout.addRow("단일 키:", self.single_key_combo)
        self.form_layout.addRow("단축키:", self.keypress_widget)
        self.form_layout.addRow("반복 간격:", self.repetition_interval_spinbox)
        self.form_layout.addRow("현재 위치 클릭 횟수:", self.current_click_count_spinbox)
        self.form_layout.addRow("날짜 설정:", self.dynamic_date_widget)
        self.form_layout.addRow("대기 시간:", self.seconds_input)
        self.form_layout.addRow("옵션:", self.uppercase_checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(self.form_layout)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.action_type_combo.currentIndexChanged.connect(self.update_ui_for_action)

        if action_data:
            self.set_data(action_data)
        else:
            self.update_ui_for_action()

        if self.locked_action_type:
            self.action_type_combo.setCurrentText(self.action_map[self.locked_action_type])
            self.action_type_combo.setEnabled(False)

    def _set_row_visible(self, widget, visible):
        label = self.form_layout.labelForField(widget)
        if label:
            label.setVisible(visible)
        widget.setVisible(visible)

    def _update_mouse_pos(self):
        try:
            x, y = pyautogui.position()
            self.coord_label.setText(f"현재 마우스 위치: ({x}, {y})")
        except pyautogui.FailSafeException:
            pass

    def _capture_mouse_pos(self):
        try:
            x, y = pyautogui.position()
            self.x_input.setValue(int(x))
            self.y_input.setValue(int(y))
        except pyautogui.FailSafeException:
            QMessageBox.warning(self, "오류", "마우스 좌표를 가져올 수 없습니다.")

    def showEvent(self, event):
        super().showEvent(event)
        self.coord_timer.start()

    def closeEvent(self, event):
        self.coord_timer.stop()
        super().closeEvent(event)

    def update_ui_for_action(self):
        action_type = self.reverse_action_map.get(self.action_type_combo.currentText(), "click")
        is_coord_action = action_type in ["click", "move", "mouse_down", "mouse_up"]
        is_repeatable = action_type in ["current_click", "keypress"]

        self._set_row_visible(self.post_delay_spinbox, action_type not in ["wait", "label"])
        self._set_row_visible(self.x_input, is_coord_action)
        self._set_row_visible(self.y_input, is_coord_action)
        self.coord_widget.setVisible(is_coord_action)
        self._set_row_visible(self.mouse_button_combo, action_type in ["click", "mouse_down", "mouse_up"])
        self._set_row_visible(self.click_mode_combo, action_type == "click")
        self._set_row_visible(self.move_duration_spinbox, action_type == "move")
        self._set_row_visible(self.scroll_widget, action_type == "scroll")
        self._set_row_visible(self.text_input, action_type in ["label", "type", "clipboard_paste"])
        self._set_row_visible(self.single_key_combo, action_type in ["key_down", "key_up"])
        self._set_row_visible(self.keypress_widget, action_type == "keypress")
        self._set_row_visible(self.repetition_interval_spinbox, is_repeatable)
        self._set_row_visible(self.current_click_count_spinbox, action_type == "current_click")
        self._set_row_visible(self.dynamic_date_widget, action_type == "dynamic_date")
        self._set_row_visible(self.seconds_input, action_type == "wait")
        self._set_row_visible(self.uppercase_checkbox, action_type == "serial_clipboard_copy")

    def set_data(self, data):
        action_type = data.get("action", "click")
        self.action_type_combo.setCurrentText(self.action_map.get(action_type, self.action_map["click"]))
        self.label_input.setText(data.get("label", ""))
        self.post_delay_spinbox.setValue(float(data.get("post_delay", DEFAULT_ACTION_POST_DELAY)))
        self.x_input.setValue(int(data.get("x", 0)))
        self.y_input.setValue(int(data.get("y", 0)))
        self.mouse_button_combo.setCurrentText(data.get("button", "left"))
        self.click_mode_combo.setCurrentIndex(1 if data.get("click_mode") == "double" else 0)
        self.move_duration_spinbox.setValue(float(data.get("duration", 0.25)))
        self.scroll_dx_spinbox.setValue(int(data.get("dx", 0)))
        self.scroll_dy_spinbox.setValue(int(data.get("dy", 0)))
        self.text_input.setText(data.get("text", ""))
        self.single_key_combo.setCurrentText(data.get("key", ""))
        self.seconds_input.setValue(float(data.get("seconds", 0.5)))

        params = data.get("params", {})
        self.special_key_combo.setCurrentText(params.get("special_key", "없음"))
        self.additional_key_input.setText(params.get("key", ""))
        self.keypress_count_spinbox.setValue(int(params.get("presses", 1)))
        self.repetition_interval_spinbox.setValue(float(params.get("interval", 0.1)))
        self.current_click_count_spinbox.setValue(int(params.get("presses", 1)))
        self.date_offset_spinbox.setValue(int(params.get("offset", 0)))
        self.date_format_input.setText(params.get("format", "%Y-%m-%d"))
        self.uppercase_checkbox.setChecked(bool(params.get("uppercase", False)))

        self.update_ui_for_action()

    def get_data(self):
        action_type = self.reverse_action_map.get(self.action_type_combo.currentText(), "click")
        data = {
            "action": action_type,
            "label": self.label_input.text().strip(),
            "post_delay": normalize_delay(self.post_delay_spinbox.value()),
        }

        if action_type == "label":
            text_value = self.text_input.text().strip()
            if not text_value:
                QMessageBox.warning(self, "입력 오류", "라벨 내용을 입력해 주세요.")
                return None
            data["text"] = text_value
            data["post_delay"] = 0.0
        elif action_type == "click":
            data.update({
                "x": int(self.x_input.value()),
                "y": int(self.y_input.value()),
                "button": self.mouse_button_combo.currentText(),
                "click_mode": self.click_mode_combo.currentData(),
            })
        elif action_type == "move":
            data.update({
                "x": int(self.x_input.value()),
                "y": int(self.y_input.value()),
                "duration": normalize_delay(self.move_duration_spinbox.value()),
            })
        elif action_type in ["mouse_down", "mouse_up"]:
            data.update({
                "x": int(self.x_input.value()),
                "y": int(self.y_input.value()),
                "button": self.mouse_button_combo.currentText(),
            })
        elif action_type == "scroll":
            data.update({
                "dx": int(self.scroll_dx_spinbox.value()),
                "dy": int(self.scroll_dy_spinbox.value()),
            })
        elif action_type in ["type", "clipboard_paste"]:
            data["text"] = self.text_input.text()
        elif action_type in ["key_down", "key_up"]:
            key_name = self.single_key_combo.currentText().strip()
            if not key_name:
                QMessageBox.warning(self, "입력 오류", "키 값을 입력해 주세요.")
                return None
            data["key"] = key_name
        elif action_type == "keypress":
            special_key = self.special_key_combo.currentText().strip() or "없음"
            params = {
                "special_key": special_key,
                "key": self.additional_key_input.text().strip(),
                "presses": int(self.keypress_count_spinbox.value()),
                "interval": normalize_delay(self.repetition_interval_spinbox.value()),
            }
            if params["special_key"] == "없음" and not params["key"]:
                QMessageBox.warning(self, "입력 오류", "단축키 값을 입력해 주세요.")
                return None
            data["params"] = params
        elif action_type == "current_click":
            data["params"] = {
                "presses": int(self.current_click_count_spinbox.value()),
                "interval": normalize_delay(self.repetition_interval_spinbox.value()),
            }
        elif action_type == "dynamic_date":
            data["params"] = {
                "offset": int(self.date_offset_spinbox.value()),
                "format": self.date_format_input.text().strip() or "%Y-%m-%d",
            }
        elif action_type == "serial_clipboard_copy":
            data["params"] = {"uppercase": self.uppercase_checkbox.isChecked()}
        elif action_type == "wait":
            data["seconds"] = normalize_delay(self.seconds_input.value())
            data.pop("post_delay", None)

        if not data["label"]:
            data["label"] = build_action_label(data)
        return data


class TextInsertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("텍스트 입력 추가")
        self.setMinimumWidth(460)

        self.mode_combo = QComboBox()
        if pyperclip is not None:
            self.mode_combo.addItem("정확 입력 (클립보드 붙여넣기)", "clipboard_paste")
        self.mode_combo.addItem("키 입력처럼 입력", "type")

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("입력할 텍스트를 그대로 넣어 주세요.")

        self.post_delay_spinbox = QDoubleSpinBox()
        self.post_delay_spinbox.setRange(0.0, 300.0)
        self.post_delay_spinbox.setSingleStep(0.1)
        self.post_delay_spinbox.setDecimals(2)
        self.post_delay_spinbox.setSuffix(" 초")
        self.post_delay_spinbox.setValue(DEFAULT_ACTION_POST_DELAY)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_if_valid)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("입력 방식:"))
        layout.addWidget(self.mode_combo)
        layout.addWidget(QLabel("텍스트:"))
        layout.addWidget(self.text_edit)
        layout.addWidget(QLabel("실행 후 지연:"))
        layout.addWidget(self.post_delay_spinbox)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def _accept_if_valid(self):
        if not self.text_edit.toPlainText():
            QMessageBox.warning(self, "입력 오류", "텍스트를 입력해 주세요.")
            return
        self.accept()

    def get_data(self):
        data = {
            "action": self.mode_combo.currentData(),
            "text": self.text_edit.toPlainText(),
            "post_delay": normalize_delay(self.post_delay_spinbox.value()),
        }
        data["label"] = build_action_label(data)
        return data
