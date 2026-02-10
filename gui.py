import sys
import os
import shutil
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QProgressBar,
    QGroupBox,
    QMessageBox,
    QSplitter,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor


class TranscriptionWorker(QThread):
    log_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    transcription_completed = pyqtSignal(list)
    transcription_failed = pyqtSignal(str)

    def __init__(self, input_media_path, output_format_type, enable_cpu_mode):
        super().__init__()
        self.media_input_path = input_media_path
        self.selected_output_format = output_format_type
        self.should_use_cpu = enable_cpu_mode

    def execute_transcription(self):
        try:
            import importlib.util

            module_spec = importlib.util.spec_from_file_location(
                "transcription_module", "init.py"
            )
            transcription_module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(transcription_module)

            transcription_module.FORCE_CPU_INFERENCE = self.should_use_cpu

            def log_callback(message):
                self.log_updated.emit(message)

            transcription_results = (
                transcription_module.run_full_transcription_pipeline(
                    self.media_input_path,
                    self.selected_output_format,
                    logger_callback=log_callback,
                )
            )

            self.transcription_completed.emit(transcription_results)

        except Exception as processing_error:
            self.transcription_failed.emit(str(processing_error))

    def run(self):
        self.execute_transcription()


class TranscriptionApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_worker_thread = None
        self.generated_files_list = []
        self.initialize_interface()

    def initialize_interface(self):
        self.setWindowTitle("语音转文字工具")
        self.setGeometry(100, 100, 1000, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        primary_layout = QVBoxLayout(main_widget)

        # 输入设置区域
        input_configuration_group = QGroupBox("输入设置")
        input_configuration_layout = QVBoxLayout(input_configuration_group)

        file_selection_layout = QHBoxLayout()
        file_selection_layout.addWidget(QLabel("输入路径:"))
        self.media_path_input = QLineEdit()
        self.media_path_input.setPlaceholderText("请输入本地文件路径或在线视频URL")
        file_selection_layout.addWidget(self.media_path_input)

        self.file_browser_button = QPushButton("浏览文件")
        self.file_browser_button.clicked.connect(self.browse_for_media_file)
        file_selection_layout.addWidget(self.file_browser_button)

        input_configuration_layout.addLayout(file_selection_layout)

        # 输出设置区域
        output_configuration_group = QGroupBox("输出设置")
        output_configuration_layout = QHBoxLayout(output_configuration_group)
        output_configuration_layout.addWidget(QLabel("使用CPU:"))
        self.cpu_mode_checkbox = QCheckBox()
        output_configuration_layout.addWidget(self.cpu_mode_checkbox)
        output_configuration_layout.addStretch()

        # 控制按钮区域
        control_buttons_layout = QHBoxLayout()
        self.start_transcription_button = QPushButton("开始转录")
        self.start_transcription_button.clicked.connect(
            self.initiate_transcription_process
        )

        self.terminate_transcription_button = QPushButton("停止")
        self.terminate_transcription_button.clicked.connect(
            self.terminate_transcription_process
        )
        self.terminate_transcription_button.setEnabled(False)

        self.clear_logs_button = QPushButton("清空日志")
        self.clear_logs_button.clicked.connect(self.clear_all_logs)

        control_buttons_layout.addWidget(self.start_transcription_button)
        control_buttons_layout.addWidget(self.terminate_transcription_button)
        control_buttons_layout.addWidget(self.clear_logs_button)
        control_buttons_layout.addStretch()

        # 文件操作按钮区域
        file_operations_layout = QHBoxLayout()
        self.open_selected_file_button = QPushButton("打开文件")
        self.open_selected_file_button.clicked.connect(self.open_current_file)
        self.open_selected_file_button.setEnabled(False)

        self.open_file_directory_button = QPushButton("打开文件目录")
        self.open_file_directory_button.clicked.connect(self.open_containing_directory)
        self.open_file_directory_button.setEnabled(False)

        self.copy_file_path_button = QPushButton("复制文件")
        self.copy_file_path_button.clicked.connect(self.copy_file_path_to_clipboard)
        self.copy_file_path_button.setEnabled(False)

        self.copy_file_contents_button = QPushButton("复制文件内容")
        self.copy_file_contents_button.clicked.connect(
            self.copy_file_contents_to_clipboard
        )
        self.copy_file_contents_button.setEnabled(False)

        file_operations_layout.addWidget(self.open_selected_file_button)
        file_operations_layout.addWidget(self.open_file_directory_button)
        file_operations_layout.addWidget(self.copy_file_path_button)
        file_operations_layout.addWidget(self.copy_file_contents_button)
        file_operations_layout.addStretch()

        # 进度显示
        self.progress_indicator = QProgressBar()
        self.progress_indicator.setVisible(False)

        # 主内容分割器
        content_splitter = QSplitter(Qt.Vertical)

        # 日志显示区域
        log_display_group = QGroupBox("执行日志")
        log_display_layout = QVBoxLayout(log_display_group)
        self.log_display_area = QTextEdit()
        self.log_display_area.setReadOnly(True)
        self.log_display_area.setFont(QFont("Consolas", 9))
        log_display_layout.addWidget(self.log_display_area)

        # 内容预览区域
        preview_display_group = QGroupBox("输出预览")
        preview_display_layout = QVBoxLayout(preview_display_group)

        preview_controls_layout = QHBoxLayout()
        preview_controls_layout.addWidget(QLabel("预览文件:"))

        self.preview_file_selector = QComboBox()
        self.preview_file_selector.currentTextChanged.connect(self.update_file_preview)
        preview_controls_layout.addWidget(self.preview_file_selector)

        self.refresh_preview_button = QPushButton("刷新预览")
        self.refresh_preview_button.clicked.connect(self.refresh_file_preview)
        preview_controls_layout.addWidget(self.refresh_preview_button)

        preview_controls_layout.addStretch()
        preview_display_layout.addLayout(preview_controls_layout)

        self.preview_text_area = QTextEdit()
        self.preview_text_area.setReadOnly(True)
        self.preview_text_area.setFont(QFont("Consolas", 9))
        self.preview_text_area.setPlaceholderText("预览将在此显示...")
        preview_display_layout.addWidget(self.preview_text_area)

        # 组装分割器
        log_widget_container = QWidget()
        log_widget_container.setLayout(QVBoxLayout())
        log_widget_container.layout().addWidget(log_display_group)
        content_splitter.addWidget(log_widget_container)

        preview_widget_container = QWidget()
        preview_widget_container.setLayout(QVBoxLayout())
        preview_widget_container.layout().addWidget(preview_display_group)
        content_splitter.addWidget(preview_widget_container)

        content_splitter.setSizes([400, 300])

        # 组装主界面
        primary_layout.addWidget(input_configuration_group)
        primary_layout.addWidget(output_configuration_group)
        primary_layout.addLayout(control_buttons_layout)
        primary_layout.addLayout(file_operations_layout)
        primary_layout.addWidget(self.progress_indicator)
        primary_layout.addWidget(content_splitter, 1)

    def browse_for_media_file(self):
        selected_file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频/视频文件",
            "",
            "媒体文件 (*.mp3 *.wav *.mp4 *.avi *.mov *.flv);;所有文件 (*.*)",
        )
        if selected_file_path:
            self.media_path_input.setText(selected_file_path)

    def append_log_message(self, message_text):
        timestamp_string = datetime.now().strftime("%H:%M:%S")
        formatted_log_entry = f"[{timestamp_string}] {message_text}"
        self.log_display_area.append(formatted_log_entry)
        cursor_position = self.log_display_area.textCursor()
        cursor_position.movePosition(QTextCursor.End)
        self.log_display_area.setTextCursor(cursor_position)

    def clear_all_logs(self):
        self.log_display_area.clear()

    def initiate_transcription_process(self):
        input_media_path = self.media_path_input.text().strip()
        if not input_media_path:
            QMessageBox.warning(self, "警告", "请输入文件路径或URL")
            return

        if not input_media_path.startswith(("http://", "https://", "www.")):
            if not Path(input_media_path).exists():
                QMessageBox.warning(self, "警告", "指定的本地文件不存在")
                return

        self.start_transcription_button.setEnabled(False)
        self.terminate_transcription_button.setEnabled(True)
        self.progress_indicator.setVisible(True)
        self.progress_indicator.setRange(0, 0)

        self.set_file_operations_state(False)

        self.append_log_message("开始转录任务...")
        self.append_log_message(f"输入路径: {input_media_path}")
        self.append_log_message(
            f"使用CPU: {'是' if self.cpu_mode_checkbox.isChecked() else '否'}"
        )

        self.generated_files_list = []
        self.preview_file_selector.clear()
        self.preview_text_area.clear()

        self.current_worker_thread = TranscriptionWorker(
            input_media_path, "both", self.cpu_mode_checkbox.isChecked()
        )

        self.current_worker_thread.log_updated.connect(self.append_log_message)
        self.current_worker_thread.transcription_completed.connect(
            self.handle_transcription_completion
        )
        self.current_worker_thread.transcription_failed.connect(
            self.handle_transcription_failure
        )

        self.current_worker_thread.start()

    def terminate_transcription_process(self):
        if self.current_worker_thread and self.current_worker_thread.isRunning():
            self.current_worker_thread.terminate()
            self.current_worker_thread.wait()
            self.append_log_message("转录任务已停止")

        self.reset_interface_state()

    def handle_transcription_completion(self, result_files):
        self.append_log_message("转录任务完成！")
        self.append_log_message("生成的文件:")

        self.generated_files_list = result_files

        self.preview_file_selector.clear()
        for file_path in result_files:
            file_name = Path(file_path).name
            self.preview_file_selector.addItem(file_name)
            self.append_log_message(f"  - {file_path}")

        self.set_file_operations_state(True)

        if result_files:
            self.update_file_preview()

        QMessageBox.information(
            self, "完成", f"转录完成！生成了 {len(result_files)} 个文件"
        )

        self.reset_interface_state()

    def handle_transcription_failure(self, error_message):
        self.append_log_message(f"错误: {error_message}")
        QMessageBox.critical(self, "错误", f"转录过程中发生错误:\n{error_message}")
        self.reset_interface_state()

    def reset_interface_state(self):
        self.start_transcription_button.setEnabled(True)
        self.terminate_transcription_button.setEnabled(False)
        self.progress_indicator.setVisible(False)
        self.progress_indicator.setRange(0, 100)

    def set_file_operations_state(self, enable_state):
        self.open_selected_file_button.setEnabled(
            enable_state and len(self.generated_files_list) > 0
        )
        self.open_file_directory_button.setEnabled(
            enable_state and len(self.generated_files_list) > 0
        )
        self.copy_file_path_button.setEnabled(
            enable_state and len(self.generated_files_list) > 0
        )
        self.copy_file_contents_button.setEnabled(
            enable_state and len(self.generated_files_list) > 0
        )

    def get_selected_preview_file_path(self):
        if not self.generated_files_list:
            return None

        selected_index = self.preview_file_selector.currentIndex()
        if 0 <= selected_index < len(self.generated_files_list):
            return self.generated_files_list[selected_index]
        return None

    def update_file_preview(self):
        target_file_path = self.get_selected_preview_file_path()
        if not target_file_path or not Path(target_file_path).exists():
            self.preview_text_area.clear()
            return

        try:
            with open(target_file_path, "r", encoding="utf-8") as file_handle:
                file_contents = file_handle.read()
            self.preview_text_area.setPlainText(file_contents)
        except Exception as read_error:
            self.preview_text_area.setPlainText(f"读取文件错误: {read_error}")

    def refresh_file_preview(self):
        self.update_file_preview()

    def open_current_file(self):
        target_file_path = self.get_selected_preview_file_path()
        if target_file_path and Path(target_file_path).exists():
            try:
                if sys.platform == "win32":
                    os.startfile(target_file_path)
                elif sys.platform == "darwin":
                    os.system(f"open '{target_file_path}'")
                else:
                    os.system(f"xdg-open '{target_file_path}'")
            except Exception as open_error:
                QMessageBox.warning(self, "错误", f"无法打开文件: {open_error}")
        else:
            QMessageBox.warning(self, "警告", "文件不存在")

    def open_containing_directory(self):
        target_file_path = self.get_selected_preview_file_path()
        if target_file_path and Path(target_file_path).exists():
            try:
                parent_directory = str(Path(target_file_path).parent)
                if sys.platform == "win32":
                    os.startfile(parent_directory)
                elif sys.platform == "darwin":
                    os.system(f"open '{parent_directory}'")
                else:
                    os.system(f"xdg-open '{parent_directory}'")
            except Exception as directory_error:
                QMessageBox.warning(self, "错误", f"无法打开目录: {directory_error}")
        else:
            QMessageBox.warning(self, "警告", "文件不存在")

    def copy_file_path_to_clipboard(self):
        target_file_path = self.get_selected_preview_file_path()
        if target_file_path and Path(target_file_path).exists():
            try:
                system_clipboard = QApplication.clipboard()
                system_clipboard.setText(str(target_file_path))
                QMessageBox.information(self, "成功", "文件路径已复制到剪贴板")
            except Exception as copy_error:
                QMessageBox.warning(self, "错误", f"复制失败: {copy_error}")
        else:
            QMessageBox.warning(self, "警告", "文件不存在")

    def copy_file_contents_to_clipboard(self):
        target_file_path = self.get_selected_preview_file_path()
        if target_file_path and Path(target_file_path).exists():
            try:
                with open(target_file_path, "r", encoding="utf-8") as file_handle:
                    file_contents = file_handle.read()
                system_clipboard = QApplication.clipboard()
                system_clipboard.setText(file_contents)
                QMessageBox.information(self, "成功", "文件内容已复制到剪贴板")
            except Exception as copy_error:
                QMessageBox.warning(self, "错误", f"复制失败: {copy_error}")
        else:
            QMessageBox.warning(self, "警告", "文件不存在")


def launch_application():
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("请先安装PyQt5: pip install pyqt5")
        return

    if not Path("init.py").exists():
        print("错误: 未找到 init.py 文件")
        return

    qt_application = QApplication(sys.argv)
    qt_application.setApplicationName("语音转文字工具")
    qt_application.setStyle("Fusion")

    main_application_window = TranscriptionApplication()
    main_application_window.show()

    sys.exit(qt_application.exec_())


if __name__ == "__main__":
    launch_application()
