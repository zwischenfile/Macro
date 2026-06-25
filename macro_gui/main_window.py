import json
import os
from datetime import datetime

from PyQt5.QtCore import QDateTime, QThread, Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDialog,
)

from .constants import DEFAULT_RUNTIME_STEP_DELAY, GLOBAL_HOTKEY_RUN
from .dependencies import RECORDER_IMPORT_ERROR, keyboard
from .dialogs import ActionDialog
from .recorder import MacroRecorderDialog
from .utils import build_action_label, default_script_folder, recorder_backend_available, sanitize_profile_name
from .workers import MacroWorker, SchedulerWorker

class MainWindow(QMainWindow):
    global_hotkey_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.action_clipboard = []
        self.macro_worker = None
        self.scheduler_worker = None
        self.macro_thread = None
        self.scheduler_thread = None
        self.current_file_path = None
        self.current_folder_path = default_script_folder()
        self.loaded_macros = {}
        self.recorder_dialog = None
        self.recording_session_active = False

        self.setup_ui()
        self._setup_global_hotkey()
        self._initialize_script_folder()

    def setup_ui(self):
        self.setWindowTitle("매크로 GUI")
        self.setGeometry(100, 100, 900, 620)
        self.menuBar().hide()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("<h3>매크로 선택</h3>"))

        profile_top_layout = QHBoxLayout()
        self.macro_profile_combo = QComboBox()
        self.new_macro_btn = QPushButton("새 매크로")
        self.refresh_btn = QPushButton("새로고침")
        self.recorder_btn = QPushButton("기록기 열기")
        profile_top_layout.addWidget(self.macro_profile_combo, 1)
        profile_top_layout.addWidget(self.new_macro_btn)
        profile_top_layout.addWidget(self.refresh_btn)
        profile_top_layout.addWidget(self.recorder_btn)
        right_layout.addLayout(profile_top_layout)

        self.profile_name_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        profile_form_layout = QFormLayout()
        profile_form_layout.addRow("프로필 이름:", self.profile_name_input)
        profile_form_layout.addRow("설명:", self.description_input)
        right_layout.addLayout(profile_form_layout)

        self.save_btn = QPushButton("저장")
        self.save_as_btn = QPushButton("다른 이름으로 저장")
        save_button_layout = QHBoxLayout()
        save_button_layout.addStretch(1)
        save_button_layout.addWidget(self.save_btn)
        save_button_layout.addWidget(self.save_as_btn)
        right_layout.addLayout(save_button_layout)

        actions_layout = QHBoxLayout()
        self.actions_list_widget = QListWidget()
        self.actions_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.actions_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        actions_layout.addWidget(self.actions_list_widget)

        action_buttons_layout = QVBoxLayout()
        self.add_btn = QPushButton("추가")
        self.edit_btn = QPushButton("수정")
        self.del_btn = QPushButton("삭제")
        self.up_btn = QPushButton("▲")
        self.down_btn = QPushButton("▼")
        action_buttons_layout.addWidget(self.add_btn)
        action_buttons_layout.addWidget(self.edit_btn)
        action_buttons_layout.addWidget(self.del_btn)
        action_buttons_layout.addStretch(1)
        action_buttons_layout.addWidget(self.up_btn)
        action_buttons_layout.addWidget(self.down_btn)
        actions_layout.addLayout(action_buttons_layout)
        right_layout.addLayout(actions_layout)

        schedule_layout = QHBoxLayout()
        self.schedule_datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.schedule_datetime_edit.setCalendarPopup(True)
        self.schedule_run_btn = QPushButton("예약 실행")
        schedule_layout.addWidget(self.schedule_datetime_edit)
        schedule_layout.addWidget(self.schedule_run_btn)
        right_layout.addLayout(schedule_layout)

        runtime_delay_layout = QHBoxLayout()
        runtime_delay_layout.addWidget(QLabel("실행 기본 텀:"))
        self.runtime_step_delay_spinbox = QDoubleSpinBox()
        self.runtime_step_delay_spinbox.setRange(0.0, 300.0)
        self.runtime_step_delay_spinbox.setSingleStep(0.1)
        self.runtime_step_delay_spinbox.setDecimals(2)
        self.runtime_step_delay_spinbox.setSuffix(" 초")
        self.runtime_step_delay_spinbox.setValue(DEFAULT_RUNTIME_STEP_DELAY)
        runtime_delay_layout.addWidget(self.runtime_step_delay_spinbox)
        runtime_delay_layout.addStretch(1)
        right_layout.addLayout(runtime_delay_layout)

        run_stop_layout = QHBoxLayout()
        run_stop_layout.addStretch(1)
        self.run_now_btn = QPushButton("즉시 실행")
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        run_stop_layout.addWidget(self.run_now_btn)
        run_stop_layout.addWidget(self.stop_btn)
        right_layout.addLayout(run_stop_layout)

        bottom_layout = QHBoxLayout()
        self.status_label = QLabel("상태: 초기화 중")
        self.always_on_top_checkbox = QCheckBox("항상 위에")
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.always_on_top_checkbox)
        right_layout.addLayout(bottom_layout)

        serial_panel = QWidget()
        serial_layout = QVBoxLayout(serial_panel)
        serial_layout.addWidget(QLabel("<h2>일련번호 입력</h2>"))

        serial_splitter = QSplitter(Qt.Vertical)
        todo_panel = QWidget()
        todo_layout = QVBoxLayout(todo_panel)
        todo_layout.setContentsMargins(0, 0, 0, 0)
        todo_layout.addWidget(QLabel("사용할 일련번호:"))
        self.serial_number_input_todo = QTextEdit()
        self.serial_number_input_todo.setPlaceholderText("abcdefg\n1234567\n...")
        todo_layout.addWidget(self.serial_number_input_todo)

        done_panel = QWidget()
        done_layout = QVBoxLayout(done_panel)
        done_layout.setContentsMargins(0, 0, 0, 0)
        done_layout.addWidget(QLabel("사용 완료 일련번호:"))
        self.serial_number_input_done = QTextEdit()
        done_layout.addWidget(self.serial_number_input_done)

        serial_splitter.addWidget(todo_panel)
        serial_splitter.addWidget(done_panel)
        serial_splitter.setSizes([400, 200])
        serial_layout.addWidget(serial_splitter)

        splitter.addWidget(right_panel)
        splitter.addWidget(serial_panel)
        splitter.setSizes([650, 250])
        main_layout.addWidget(splitter)

        self.macro_profile_combo.currentIndexChanged.connect(self._on_macro_selected)
        self.new_macro_btn.clicked.connect(self._create_new_macro)
        self.refresh_btn.clicked.connect(self._load_macro_folder)
        self.recorder_btn.clicked.connect(self.open_recorder_dialog)
        self.save_btn.clicked.connect(self.save_file)
        self.save_as_btn.clicked.connect(self.save_file_as)
        self.add_btn.clicked.connect(self.add_action)
        self.edit_btn.clicked.connect(self.edit_action)
        self.del_btn.clicked.connect(self.delete_actions)
        self.up_btn.clicked.connect(self.move_action_up)
        self.down_btn.clicked.connect(self.move_action_down)
        self.run_now_btn.clicked.connect(self.run_macro_now)
        self.schedule_run_btn.clicked.connect(self.schedule_macro)
        self.stop_btn.clicked.connect(self.stop_all_tasks)
        self.actions_list_widget.customContextMenuRequested.connect(self._show_action_context_menu)
        self.always_on_top_checkbox.stateChanged.connect(self._toggle_always_on_top)

    def _initialize_script_folder(self):
        os.makedirs(self.current_folder_path, exist_ok=True)
        self._load_macro_folder()

    def _setup_global_hotkey(self):
        self.global_hotkey_triggered.connect(self.run_macro_now)
        try:
            keyboard.add_hotkey(GLOBAL_HOTKEY_RUN, lambda: self.global_hotkey_triggered.emit())
            self.status_label.setText(f"상태: 대기 중 ({GLOBAL_HOTKEY_RUN} 단축키로 즉시 실행)")
        except Exception as exc:
            QMessageBox.warning(self, "단축키 등록 실패", f"전역 단축키 '{GLOBAL_HOTKEY_RUN}' 등록에 실패했습니다.\n\n오류: {exc}")

    def _update_serial_todo_box(self, text):
        self.serial_number_input_todo.setPlainText(text)

    def _update_serial_done_box(self, used_serial, current_done_text):
        if not used_serial:
            return
        new_text = current_done_text + "\n" + used_serial if current_done_text else used_serial
        self.serial_number_input_done.setPlainText(new_text)
        self.serial_number_input_done.verticalScrollBar().setValue(self.serial_number_input_done.verticalScrollBar().maximum())

    def _toggle_always_on_top(self, state):
        flags = self.windowFlags()
        if state == Qt.Checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def restore_after_recorder(self):
        if self.isVisible():
            return
        self.show()
        self.raise_()
        self.activateWindow()

    def keyPressEvent(self, event):
        if self.actions_list_widget.hasFocus():
            if event.matches(QKeySequence.Cut):
                self._cut_actions()
            elif event.matches(QKeySequence.Copy):
                self._copy_actions()
            elif event.matches(QKeySequence.Paste):
                self._paste_actions()
            elif event.key() == Qt.Key_Delete:
                self.delete_actions()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def _show_action_context_menu(self, position):
        menu = QMenu()
        cut_action = menu.addAction("잘라내기")
        copy_action = menu.addAction("복사")
        paste_action = menu.addAction("붙여넣기")
        delete_action = menu.addAction("삭제")

        cut_action.setShortcut(QKeySequence.Cut)
        copy_action.setShortcut(QKeySequence.Copy)
        paste_action.setShortcut(QKeySequence.Paste)
        delete_action.setShortcut(QKeySequence.Delete)

        cut_action.triggered.connect(self._cut_actions)
        copy_action.triggered.connect(self._copy_actions)
        paste_action.triggered.connect(self._paste_actions)
        delete_action.triggered.connect(self.delete_actions)

        has_selection = bool(self.actions_list_widget.selectedItems())
        cut_action.setEnabled(has_selection)
        copy_action.setEnabled(has_selection)
        delete_action.setEnabled(has_selection)
        paste_action.setEnabled(bool(self.action_clipboard))
        menu.exec_(self.actions_list_widget.mapToGlobal(position))

    def _cut_actions(self):
        self._copy_actions()
        self.delete_actions()

    def _copy_actions(self):
        self.action_clipboard = [item.data(Qt.UserRole) for item in self.actions_list_widget.selectedItems()]

    def _paste_actions(self):
        if not self.action_clipboard:
            return

        insert_row = self.actions_list_widget.currentRow()
        if insert_row == -1:
            insert_row = self.actions_list_widget.count() - 1

        for action_data in reversed(self.action_clipboard):
            copied_action = dict(action_data)
            copied_action["label"] = copied_action.get("label") or build_action_label(copied_action)
            item = QListWidgetItem(copied_action["label"])
            item.setData(Qt.UserRole, copied_action)
            self.actions_list_widget.insertItem(insert_row + 1, item)

    def delete_actions(self):
        for item in self.actions_list_widget.selectedItems():
            self.actions_list_widget.takeItem(self.actions_list_widget.row(item))

    def _load_macro_folder(self):
        dir_path = self.current_folder_path
        os.makedirs(dir_path, exist_ok=True)

        selected_path = self.current_file_path
        self.macro_profile_combo.blockSignals(True)
        self.macro_profile_combo.clear()
        self.loaded_macros.clear()
        self._display_macro_details({})
        self.profile_name_input.clear()
        self.description_input.clear()

        for filename in sorted(os.listdir(dir_path)):
            if not filename.endswith(".json"):
                continue
            file_path = os.path.join(dir_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                profile_name = data.get("profile_name", filename)
                self.loaded_macros[file_path] = data
                self.macro_profile_combo.addItem(profile_name, file_path)
            except Exception as exc:
                print(f"'{filename}' 파일 로드 오류: {exc}")

        self.macro_profile_combo.blockSignals(False)
        if self.macro_profile_combo.count() > 0:
            target_index = 0
            if selected_path:
                for index in range(self.macro_profile_combo.count()):
                    if self.macro_profile_combo.itemData(index) == selected_path:
                        target_index = index
                        break
            self.macro_profile_combo.setCurrentIndex(target_index)
            self._on_macro_selected(target_index)
            self.status_label.setText(f"상태: '{os.path.basename(dir_path)}' 폴더의 매크로를 불러왔습니다.")
        else:
            self.current_file_path = None
            self.status_label.setText("상태: _Script 폴더에 매크로가 없습니다. 새 매크로를 만들어 주세요.")

    def _create_new_macro(self):
        profile_name, ok = QInputDialog.getText(self, "새 매크로", "새 매크로 이름을 입력하세요:")
        if not ok:
            return

        profile_name = sanitize_profile_name(profile_name)
        if not profile_name:
            QMessageBox.warning(self, "입력 오류", "매크로 이름을 입력해 주세요.")
            return

        file_path = os.path.join(self.current_folder_path, f"{profile_name}.json")
        if os.path.exists(file_path):
            QMessageBox.warning(self, "생성 실패", f"'{profile_name}.json' 파일이 이미 존재합니다.")
            return

        new_macro_data = {"profile_name": profile_name, "description": "", "actions": []}
        if self._perform_save(file_path, data_to_save=new_macro_data):
            self._load_macro_folder()
            for index in range(self.macro_profile_combo.count()):
                if self.macro_profile_combo.itemData(index) == file_path:
                    self.macro_profile_combo.setCurrentIndex(index)
                    break
            self.status_label.setText(f"상태: '{profile_name}' 매크로를 생성했습니다.")

    def _on_macro_selected(self, index):
        if index == -1:
            self.current_file_path = None
            self._display_macro_details({})
            self.profile_name_input.clear()
            self.description_input.clear()
            return

        file_path = self.macro_profile_combo.itemData(index)
        macro_data = self.loaded_macros.get(file_path)
        if macro_data:
            self.current_file_path = file_path
            self._display_macro_details(macro_data)
            if self.recorder_dialog:
                self.recorder_dialog.set_target_profile(macro_data.get("profile_name", ""))
            self.status_label.setText(f"상태: '{macro_data.get('profile_name', '')}' 선택")

    def _display_macro_details(self, macro_data):
        self.profile_name_input.setText(macro_data.get("profile_name", ""))
        self.description_input.setPlainText(macro_data.get("description", ""))
        self.actions_list_widget.clear()
        for action_data in macro_data.get("actions", []):
            action_data["label"] = action_data.get("label") or build_action_label(action_data)
            item = QListWidgetItem(action_data["label"])
            item.setData(Qt.UserRole, action_data)
            self.actions_list_widget.addItem(item)

    def save_file_as(self):
        if not self.current_file_path:
            QMessageBox.warning(self, "오류", "먼저 저장할 매크로를 선택해 주세요.")
            return

        default_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        new_name, ok = QInputDialog.getText(self, "다른 이름으로 저장", "새 파일 이름을 입력하세요:", text=default_name)
        if not ok:
            return

        new_name = sanitize_profile_name(new_name)
        if not new_name:
            QMessageBox.warning(self, "입력 오류", "파일 이름을 입력해 주세요.")
            return

        file_path = os.path.join(self.current_folder_path, f"{new_name}.json")
        if os.path.exists(file_path) and file_path != self.current_file_path:
            if QMessageBox.question(self, "덮어쓰기 확인", f"'{new_name}.json' 파일이 이미 있습니다. 덮어쓰시겠습니까?") != QMessageBox.Yes:
                return
        self._perform_save(file_path)

    def save_file(self):
        if self.current_file_path:
            self._perform_save(self.current_file_path)
        else:
            QMessageBox.warning(self, "오류", "저장할 매크로를 먼저 선택하거나 생성해 주세요.")

    def _perform_save(self, file_path, data_to_save=None):
        if data_to_save is None:
            actions = [self.actions_list_widget.item(i).data(Qt.UserRole) for i in range(self.actions_list_widget.count())]
            for action in actions:
                action["label"] = action.get("label") or build_action_label(action)
            profile_name = self.profile_name_input.text().strip() or os.path.splitext(os.path.basename(file_path))[0]
            data = {
                "profile_name": profile_name,
                "description": self.description_input.toPlainText(),
                "actions": actions,
            }
        else:
            data = data_to_save

        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)

            self.loaded_macros[file_path] = data
            found_index = -1
            for index in range(self.macro_profile_combo.count()):
                if self.macro_profile_combo.itemData(index) == file_path:
                    found_index = index
                    break

            if found_index != -1:
                self.macro_profile_combo.setItemText(found_index, data["profile_name"])
            else:
                self.macro_profile_combo.addItem(data["profile_name"], file_path)
                found_index = self.macro_profile_combo.count() - 1

            self.macro_profile_combo.setCurrentIndex(found_index)
            self.current_file_path = file_path
            self.status_label.setText(f"상태: '{os.path.basename(file_path)}' 저장됨")
            return True
        except Exception as exc:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류가 발생했습니다: {exc}")
            return False

    def add_action(self):
        if not self.current_file_path:
            QMessageBox.warning(self, "선택 오류", "먼저 매크로를 선택해 주세요.")
            return
        dialog = ActionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            action_data = dialog.get_data()
            if action_data:
                item = QListWidgetItem(action_data["label"])
                item.setData(Qt.UserRole, action_data)
                self.actions_list_widget.addItem(item)

    def edit_action(self):
        if not self.current_file_path:
            QMessageBox.warning(self, "선택 오류", "먼저 매크로를 선택해 주세요.")
            return
        selected_item = self.actions_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "선택 오류", "수정할 동작을 선택해 주세요.")
            return
        action_data = selected_item.data(Qt.UserRole)
        dialog = ActionDialog(self, action_data)
        if dialog.exec_() == QDialog.Accepted:
            new_action_data = dialog.get_data()
            if new_action_data:
                selected_item.setText(new_action_data["label"])
                selected_item.setData(Qt.UserRole, new_action_data)

    def move_action_up(self):
        current_row = self.actions_list_widget.currentRow()
        if current_row > 0:
            item = self.actions_list_widget.takeItem(current_row)
            self.actions_list_widget.insertItem(current_row - 1, item)
            self.actions_list_widget.setCurrentRow(current_row - 1)

    def move_action_down(self):
        current_row = self.actions_list_widget.currentRow()
        if current_row < self.actions_list_widget.count() - 1:
            item = self.actions_list_widget.takeItem(current_row)
            self.actions_list_widget.insertItem(current_row + 1, item)
            self.actions_list_widget.setCurrentRow(current_row + 1)

    def open_recorder_dialog(self):
        if self.macro_worker and self.macro_worker.is_running:
            QMessageBox.warning(self, "실행 중", "매크로 실행 중에는 기록기를 열 수 없습니다.")
            return
        if not self.current_file_path:
            QMessageBox.warning(self, "선택 오류", "먼저 매크로를 선택하거나 새로 만들어 주세요.")
            return
        if not recorder_backend_available():
            QMessageBox.warning(
                self,
                "기록기 사용 불가",
                "입력 기록 기능에 필요한 'pynput' 패키지가 설치되어 있지 않습니다.\n\n"
                f"오류: {RECORDER_IMPORT_ERROR}",
            )
            return

        if self.recorder_dialog is None:
            self.recorder_dialog = MacroRecorderDialog(self)
            self.recorder_dialog.recording_finished.connect(self.apply_recorded_actions)
            self.recorder_dialog.recording_state_changed.connect(self._set_recording_mode)

        self.recorder_dialog.set_target_profile(self.profile_name_input.text())
        self.hide()
        self.recorder_dialog.show()
        self.recorder_dialog.raise_()
        self.recorder_dialog.activateWindow()

    def _set_recording_mode(self, is_recording):
        self.recording_session_active = is_recording
        widgets = [
            self.macro_profile_combo,
            self.new_macro_btn,
            self.refresh_btn,
            self.save_btn,
            self.save_as_btn,
            self.add_btn,
            self.edit_btn,
            self.del_btn,
            self.up_btn,
            self.down_btn,
            self.run_now_btn,
            self.schedule_run_btn,
        ]
        for widget in widgets:
            widget.setEnabled(not is_recording)
        self.recorder_btn.setEnabled(True)

        if is_recording:
            self.status_label.setText("상태: 기록 세션 진행 중")
        elif not (self.macro_worker and self.macro_worker.is_running):
            self.status_label.setText(f"상태: 대기 중 ({GLOBAL_HOTKEY_RUN} 단축키로 즉시 실행)")

    def apply_recorded_actions(self, recorded_actions, mode):
        if not recorded_actions:
            self.status_label.setText("상태: 기록된 동작이 없습니다.")
            return

        existing_actions = []
        if mode == "append":
            existing_actions = [
                self.actions_list_widget.item(i).data(Qt.UserRole)
                for i in range(self.actions_list_widget.count())
            ]

        final_actions = existing_actions + recorded_actions
        self.actions_list_widget.clear()
        for action_data in final_actions:
            action_data["label"] = action_data.get("label") or build_action_label(action_data)
            item = QListWidgetItem(action_data["label"])
            item.setData(Qt.UserRole, action_data)
            self.actions_list_widget.addItem(item)

        self.status_label.setText(f"상태: {len(recorded_actions)}개 동작을 기록했습니다.")
        if self.current_file_path:
            self.save_file()

    def run_macro_now(self):
        if self.recording_session_active:
            QMessageBox.warning(self, "기록 중", "기록 세션이 진행 중일 때는 실행할 수 없습니다.")
            return
        if self.macro_worker and self.macro_worker.is_running:
            QMessageBox.warning(self, "실행 중", "이미 매크로가 실행 중입니다.")
            return
        if not self.current_file_path:
            QMessageBox.warning(self, "선택 오류", "실행할 매크로를 먼저 선택해 주세요.")
            return

        actions = [self.actions_list_widget.item(i).data(Qt.UserRole) for i in range(self.actions_list_widget.count())]
        if not actions:
            QMessageBox.warning(self, "동작 없음", "실행할 동작이 없습니다.")
            return

        self.update_ui_for_run(True)
        self.status_label.setText("상태: 실행 중...")
        self.macro_thread = QThread()
        self.macro_worker = MacroWorker(
            actions,
            self.serial_number_input_todo,
            self.serial_number_input_done,
            self.profile_name_input.text(),
            self.current_folder_path,
            self.runtime_step_delay_spinbox.value(),
        )
        self.macro_worker.moveToThread(self.macro_thread)
        self.macro_worker.request_serial_todo_update.connect(self._update_serial_todo_box)
        self.macro_worker.request_serial_done_update.connect(self._update_serial_done_box)
        self.macro_thread.started.connect(self.macro_worker.run)
        self.macro_worker.finished.connect(self.on_macro_finished)
        self.macro_worker.progress_update.connect(self.update_list_selection)
        self.macro_worker.error_occurred.connect(self.on_macro_error)
        self.macro_thread.start()

    def schedule_macro(self):
        if self.recording_session_active:
            QMessageBox.warning(self, "기록 중", "기록 세션이 진행 중일 때는 예약할 수 없습니다.")
            return
        if not self.current_file_path:
            QMessageBox.warning(self, "선택 오류", "예약 실행할 매크로를 먼저 선택해 주세요.")
            return

        target_datetime = self.schedule_datetime_edit.dateTime().toPyDateTime()
        if target_datetime < datetime.now():
            QMessageBox.warning(self, "시간 오류", "예약 시간은 현재 시간 이후여야 합니다.")
            return

        self.update_ui_for_run(True)
        self.status_label.setText(f"상태: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')} 예약됨")
        self.scheduler_thread = QThread()
        self.scheduler_worker = SchedulerWorker(target_datetime)
        self.scheduler_worker.moveToThread(self.scheduler_thread)
        self.scheduler_thread.started.connect(self.scheduler_worker.run)
        self.scheduler_worker.trigger_macro.connect(self.run_macro_now)
        self.scheduler_worker.finished.connect(self.on_schedule_finished)
        self.scheduler_thread.start()

    def stop_all_tasks(self):
        if self.scheduler_worker:
            self.scheduler_worker.stop()
        if self.macro_worker:
            self.macro_worker.stop()
        self.status_label.setText("상태: 중지 요청 중...")

    def update_ui_for_run(self, is_running):
        self.run_now_btn.setEnabled(not is_running)
        self.schedule_run_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        self.recorder_btn.setEnabled(not is_running)
        self.runtime_step_delay_spinbox.setEnabled(not is_running)

    def on_macro_finished(self):
        self.status_label.setText(f"상태: 대기 중 ({GLOBAL_HOTKEY_RUN} 단축키로 즉시 실행)")
        self.update_ui_for_run(False)
        if self.macro_thread:
            self.macro_thread.quit()
            self.macro_thread.wait()
            self.macro_thread = None
            self.macro_worker = None

    def on_schedule_finished(self):
        if self.scheduler_thread:
            self.scheduler_thread.quit()
            self.scheduler_thread.wait()
            self.scheduler_thread = None
            self.scheduler_worker = None
        if "예약됨" in self.status_label.text():
            self.status_label.setText(f"상태: 대기 중 ({GLOBAL_HOTKEY_RUN} 단축키로 즉시 실행)")
            self.update_ui_for_run(False)

    def on_macro_error(self, error_message):
        QMessageBox.critical(self, "실행 오류", error_message)
        self.on_macro_finished()

    def update_list_selection(self, index):
        self.actions_list_widget.setCurrentRow(index)

    def closeEvent(self, event):
        if self.recorder_dialog is not None:
            self.recorder_dialog.close()
        self.stop_all_tasks()
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        event.accept