#!/usr/bin/env python3
"""
Speech Recognition GUI - PyQt5 Version
"""
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox, 
                             QWidget, QMessageBox, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import threading

# Import functions from init.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from init import process, check_ffmpeg, USE_CPU
except ImportError:
    print("Error: Please make sure init.py is in the same directory")
    sys.exit(1)

class WorkerThread(QThread):
    finished = pyqtSignal(str)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, url, use_cpu):
        super().__init__()
        self.url = url
        self.use_cpu = use_cpu
    
    def run(self):
        try:
            global USE_CPU
            USE_CPU = self.use_cpu
            
            # 模拟状态更新（实际需要在init.py中添加状态回调）
            self.status.emit("开始处理...")
            self.status.emit("检查输入文件/URL...")
            
            result = process(self.url)
            self.status.emit("处理完成!")
            self.finished.emit(result)
            
        except Exception as e:
            self.status.emit(f"发生错误: {str(e)}")
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("语音识别工具")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Input field
        main_layout.addWidget(QLabel("输入URL或文件路径:"))
        self.input_entry = QLineEdit()
        main_layout.addWidget(self.input_entry)
        
        # Checkbox and button
        h_layout = QHBoxLayout()
        self.cpu_checkbox = QCheckBox("CPU模式")
        h_layout.addWidget(self.cpu_checkbox)
        
        self.process_btn = QPushButton("开始处理")
        self.process_btn.clicked.connect(self.start_process)
        h_layout.addWidget(self.process_btn)
        
        main_layout.addLayout(h_layout)
        
        # Create splitter for status and output
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # Status area (top)
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.addWidget(QLabel("运行状态:"))
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)  # Limit height for status area
        status_layout.addWidget(self.status_text)
        splitter.addWidget(status_widget)
        
        # Output area (bottom)
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.addWidget(QLabel("识别结果:"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        splitter.addWidget(output_widget)
        
        # Set splitter proportions (status: 30%, output: 70%)
        splitter.setSizes([180, 420])
    
    def start_process(self):
        url = self.input_entry.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入URL或文件路径")
            return
        
        self.process_btn.setEnabled(False)
        self.status_text.clear()
        self.output_text.clear()
        
        self.worker = WorkerThread(url, self.cpu_checkbox.isChecked())
        self.worker.finished.connect(self.on_finished)
        self.worker.status.connect(self.on_status)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_status(self, status_msg):
        """更新状态信息"""
        self.status_text.append(f"• {status_msg}")
        # Auto scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.End)
        self.status_text.setTextCursor(cursor)
    
    def on_finished(self, result):
        """处理完成，显示最终结果"""
        self.output_text.setPlainText(result)
        self.on_status("结果已输出到输出框！")
        self.process_btn.setEnabled(True)
    
    def on_error(self, error_msg):
        """处理错误"""
        self.on_status(f"❌ 错误: {error_msg}")
        self.output_text.setPlainText(f"处理过程中发生错误:\n{error_msg}")
        self.process_btn.setEnabled(True)

def main():
    # Check ffmpeg
    try:
        check_ffmpeg()
    except:
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "Error", "请先安装ffmpeg")
        return
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
