#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志窗口模块，用于显示程序启动过程中的实时日志
"""

import sys
import logging
import queue
import threading
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QTextEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QFont, QTextCursor, QColor, QIcon

from config import FONT_FAMILY, COLORS
from ui.components.ui_components import ModernButton, ModernLabel, HorizontalLine


class LogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到队列"""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put((record.levelno, msg, record))
        except Exception:
            self.handleError(record)


class LogSignals(QObject):
    """日志信号类，用于在线程间传递日志消息"""
    new_log = pyqtSignal(int, str, object)


class LogWindow(QMainWindow):
    """日志窗口类，显示实时日志"""
    
    def __init__(self, title="程序启动日志", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 550)
        
        # 设置窗口标志，使其始终显示在最上层
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.log_queue = queue.Queue()
        self.log_signals = LogSignals()
        self.log_signals.new_log.connect(self.append_log)
        self.setup_ui()
        self.setup_logger()
        self.start_timer()
        
        # 自动滚动标志
        self.auto_scroll = True
        
        # 数据库连接状态
        self.db_connection_status = "未知"
        self.db_status_color = COLORS["secondary"]
        
        # 设置窗口样式
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: white;
            }}
            QTextEdit {{
                background-color: {COLORS["light"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
                selection-background-color: {COLORS["primary"]};
                font-family: {FONT_FAMILY};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {COLORS["light"]};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS["secondary"]};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QGroupBox {{
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                margin-top: 12px;
                font-weight: bold;
                font-family: {FONT_FAMILY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                font-weight: bold;
                color: {COLORS["primary"]};
            }}
        """)
        
    def setup_ui(self):
        """设置界面"""
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        central_widget.setLayout(main_layout)
        
        # 标题标签
        title_layout = QHBoxLayout()
        title_label = ModernLabel("系统启动日志", font_size=14, bold=True, color=COLORS["primary"])
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)
        main_layout.addLayout(title_layout)
        
        # 分隔线
        main_layout.addWidget(HorizontalLine())
        main_layout.addSpacing(10)
        
        # 状态信息区域
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        # 数据库连接状态
        db_status_layout = QHBoxLayout()
        db_status_label = ModernLabel("数据库连接:", font_size=9, bold=True)
        self.db_status_value = ModernLabel("正在检查...", font_size=9, color=COLORS["secondary"])
        
        db_status_layout.addWidget(db_status_label)
        db_status_layout.addWidget(self.db_status_value)
        db_status_layout.addStretch()
        
        # 添加到状态布局
        status_layout.addLayout(db_status_layout)
        
        # 说明文本
        desc_label = ModernLabel("以下是系统启动过程中的日志信息，包括数据库连接状态和初始化过程。", font_size=9)
        desc_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(desc_label)
        
        # 添加状态组到主布局
        main_layout.addWidget(status_group)
        main_layout.addSpacing(10)
        
        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont(FONT_FAMILY, 9))
        self.log_display.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.log_display)
        
        # 控制区域布局
        control_layout = QVBoxLayout()
        
        # 分隔线
        control_layout.addWidget(HorizontalLine())
        control_layout.addSpacing(10)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 状态标签
        self.status_label = ModernLabel("正在加载日志信息...", color=COLORS["secondary"])
        button_layout.addWidget(self.status_label)
        
        button_layout.addStretch()
        
        # 自动滚动按钮
        self.auto_scroll_button = ModernButton("暂停自动滚动", color=COLORS["secondary"])
        self.auto_scroll_button.setCheckable(True)
        self.auto_scroll_button.clicked.connect(self.toggle_auto_scroll)
        button_layout.addWidget(self.auto_scroll_button)
        
        # 清除按钮
        clear_button = ModernButton("清除日志", color=COLORS["warning"])
        clear_button.clicked.connect(self.clear_logs)
        button_layout.addWidget(clear_button)
        
        # 关闭按钮
        close_button = ModernButton("关闭窗口", color=COLORS["primary"])
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        control_layout.addLayout(button_layout)
        main_layout.addLayout(control_layout)
        
    def setup_logger(self):
        """设置日志处理器"""
        # 创建自定义处理器
        handler = LogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # 获取根日志记录器并添加处理器
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        
    def start_timer(self):
        """启动定时器，定期检查日志队列"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_logs)
        self.timer.start(100)  # 每100毫秒检查一次
        
    def check_logs(self):
        """检查日志队列并发送信号"""
        try:
            count = 0
            while not self.log_queue.empty() and count < 100:  # 限制每次处理的条数
                level, msg, record = self.log_queue.get_nowait()
                self.log_signals.new_log.emit(level, msg, record)
                count += 1
                
            if count > 0:
                self.status_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"检查日志队列时出错: {str(e)}")
            
    def append_log(self, level, msg, record):
        """添加日志到显示区域"""
        # 设置不同级别的颜色
        color = QColor(COLORS["text_dark"])  # 默认颜色
        
        if level >= logging.ERROR:
            color = QColor(COLORS["danger"])
        elif level >= logging.WARNING:
            color = QColor(COLORS["warning"])
        elif level >= logging.INFO:
            color = QColor(COLORS["primary"])
        
        # 保存当前光标位置
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 设置文本颜色
        cursor.insertBlock()
        self.log_display.setTextColor(color)
        
        # 插入文本
        self.log_display.insertPlainText(msg)
        
        # 检查是否包含数据库连接相关信息
        message = getattr(record, 'message', '').lower()
        if '数据库连接成功' in message or '已连接到mysql数据库' in message:
            self.update_db_status("已连接", COLORS["success"])
        elif '数据库连接失败' in message or '无法连接到数据库' in message or '连接mysql数据库时出错' in message:
            self.update_db_status("连接失败", COLORS["danger"])
        elif '正在尝试连接数据库' in message:
            self.update_db_status("正在连接...", COLORS["warning"])
        elif '数据库自动连接已禁用' in message:
            self.update_db_status("自动连接已禁用", COLORS["secondary"])
        
        # 自动滚动到底部
        if self.auto_scroll:
            self.log_display.moveCursor(QTextCursor.End)
    
    def update_db_status(self, status, color):
        """更新数据库连接状态显示"""
        self.db_connection_status = status
        self.db_status_color = color
        self.db_status_value.setText(status)
        self.db_status_value.setStyleSheet(f"color: {color};")
    
    def toggle_auto_scroll(self, checked):
        """切换自动滚动状态"""
        self.auto_scroll = not checked
        if checked:
            self.auto_scroll_button.setText("恢复自动滚动")
        else:
            self.auto_scroll_button.setText("暂停自动滚动")
            # 恢复自动滚动时，先滚动到底部
            self.log_display.moveCursor(QTextCursor.End)
    
    def clear_logs(self):
        """清除日志显示"""
        self.log_display.clear()
        self.status_label.setText("日志已清除")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止定时器
        self.timer.stop()
        
        # 从根日志记录器中移除处理器
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, LogHandler) and handler.log_queue == self.log_queue:
                root_logger.removeHandler(handler)
                
        event.accept()


def show_log_window():
    """显示日志窗口"""
    log_window = LogWindow()
    log_window.show()
    log_window.raise_()  # 确保窗口显示在最前端
    log_window.activateWindow()  # 激活窗口，使其获得焦点
    return log_window 