#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统日志查看器模块，提供独立的系统日志监控和查看功能
"""

import sys
import os
import logging
import queue
import threading
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QTextEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QGroupBox, QToolBar, QAction, QMenu, QSystemTrayIcon,
    QSplitter, QTreeWidget, QTreeWidgetItem, QFileDialog, QCheckBox,
    QComboBox, QLineEdit, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QFont, QTextCursor, QColor, QIcon

from config import FONT_FAMILY, COLORS, LOG_DIR
from ui.components.ui_components import ModernButton, ModernLabel, HorizontalLine, ModernLineEdit


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


class SystemLogViewer(QMainWindow):
    """系统日志查看器类，提供独立的日志查看功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统日志查看器")
        self.resize(900, 600)
        
        # 设置窗口图标
        try:
            # 尝试设置应用图标
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon("icons/log.png"))
        except:
            pass
        
        # 日志队列和信号
        self.log_queue = queue.Queue()
        self.log_signals = LogSignals()
        self.log_signals.new_log.connect(self.append_log)
        
        # 自动滚动标志
        self.auto_scroll = True
        
        # 系统状态
        self.system_status = {}
        
        # 设置UI
        self.setup_ui()
        self.setup_logger()
        self.start_timer()
        
        # 设置窗口样式
        self.setup_style()
        
        # 显示初始信息
        self.status_bar.showMessage("日志查看器已启动")
        
    def setup_ui(self):
        """设置界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 工具栏
        self.create_toolbar()
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        # 左侧区域 - 日志类别和过滤器
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 日志过滤区域
        filter_group = QGroupBox("日志过滤")
        filter_layout = QVBoxLayout(filter_group)
        
        # 日志级别过滤
        level_layout = QHBoxLayout()
        level_layout.addWidget(ModernLabel("日志级别:", font_size=9))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.currentTextChanged.connect(self.apply_filters)
        level_layout.addWidget(self.level_combo)
        filter_layout.addLayout(level_layout)
        
        # 搜索过滤
        search_layout = QHBoxLayout()
        search_layout.addWidget(ModernLabel("搜索:", font_size=9))
        self.search_edit = ModernLineEdit(placeholder="输入搜索关键词")
        self.search_edit.textChanged.connect(self.apply_filters)
        search_layout.addWidget(self.search_edit)
        filter_layout.addLayout(search_layout)
        
        # 模块过滤
        module_layout = QVBoxLayout()
        module_layout.addWidget(ModernLabel("模块:", font_size=9))
        self.db_check = QCheckBox("数据库")
        self.ui_check = QCheckBox("用户界面")
        self.auth_check = QCheckBox("认证")
        self.system_check = QCheckBox("系统")
        self.db_check.setChecked(True)
        self.ui_check.setChecked(True)
        self.auth_check.setChecked(True)
        self.system_check.setChecked(True)
        
        for check in [self.db_check, self.ui_check, self.auth_check, self.system_check]:
            module_layout.addWidget(check)
            check.stateChanged.connect(self.apply_filters)
        
        filter_layout.addLayout(module_layout)
        left_layout.addWidget(filter_group)
        
        # 系统状态区域
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        # 数据库连接状态
        db_status_layout = QHBoxLayout()
        db_status_layout.addWidget(ModernLabel("数据库连接:", font_size=9, bold=True))
        self.db_status_value = ModernLabel("未知", font_size=9, color=COLORS["secondary"])
        db_status_layout.addWidget(self.db_status_value)
        status_layout.addLayout(db_status_layout)
        
        # 其他系统状态可以在这里添加
        # ...
        
        left_layout.addWidget(status_group)
        left_layout.addStretch()
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        
        # 右侧区域 - 日志显示
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 日志显示区域
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont(FONT_FAMILY, 9))
        self.log_display.setLineWrapMode(QTextEdit.NoWrap)
        log_layout.addWidget(self.log_display)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        # 自动滚动按钮
        self.auto_scroll_button = ModernButton("暂停自动滚动", color=COLORS["secondary"], flat=True)
        self.auto_scroll_button.setCheckable(True)
        self.auto_scroll_button.clicked.connect(self.toggle_auto_scroll)
        control_layout.addWidget(self.auto_scroll_button)
        
        control_layout.addStretch()
        
        # 清除按钮
        clear_button = ModernButton("清除日志", color=COLORS["warning"], flat=True)
        clear_button.clicked.connect(self.clear_logs)
        control_layout.addWidget(clear_button)
        
        # 保存按钮
        save_button = ModernButton("保存日志", color=COLORS["primary"], flat=True)
        save_button.clicked.connect(self.save_logs)
        control_layout.addWidget(save_button)
        
        log_layout.addLayout(control_layout)
        right_layout.addWidget(log_group)
        
        # 添加到分割器
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([250, 650])
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
    def create_toolbar(self):
        """创建工具栏"""
        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)
        
        # 创建刷新按钮
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_logs)
        self.toolbar.addAction(refresh_action)
        
        self.toolbar.addSeparator()
        
        # 创建最小化到系统托盘按钮
        minimize_action = QAction("最小化到托盘", self)
        minimize_action.triggered.connect(self.hide)
        self.toolbar.addAction(minimize_action)
        
        # 创建关闭按钮
        close_action = QAction("关闭", self)
        close_action.triggered.connect(self.close)
        self.toolbar.addAction(close_action)
    
    def setup_style(self):
        """设置窗口样式"""
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: white;
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
            QCheckBox {{
                font-family: {FONT_FAMILY};
            }}
            QComboBox {{
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 2px 6px;
                background-color: white;
                font-family: {FONT_FAMILY};
            }}
            QToolBar {{
                border: none;
                background-color: {COLORS["light"]};
                spacing: 5px;
            }}
            QToolButton {{
                border: none;
                border-radius: 4px;
                padding: 3px;
            }}
            QToolButton:hover {{
                background-color: #e0e0e0;
            }}
            QStatusBar {{
                border-top: 1px solid {COLORS["border"]};
                font-family: {FONT_FAMILY};
                font-size: 9pt;
            }}
        """)
        
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
                self.status_bar.showMessage(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"检查日志队列时出错: {str(e)}")
            
    def append_log(self, level, msg, record):
        """添加日志到显示区域"""
        # 检查是否需要应用过滤
        if not self.should_show_log(level, msg, record):
            return
            
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
    
    def should_show_log(self, level, msg, record):
        """检查日志是否应该显示（基于过滤器）"""
        # 级别过滤
        level_text = self.level_combo.currentText()
        if level_text != "全部":
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            if level < level_map.get(level_text, 0):
                return False
        
        # 关键词过滤
        search_text = self.search_edit.text().strip().lower()
        if search_text and search_text not in msg.lower():
            return False
        
        # 模块过滤
        module_name = getattr(record, 'name', '').lower()
        message = getattr(record, 'message', '').lower()
        
        # 如果数据库相关模块被取消选中
        if not self.db_check.isChecked() and ('db_manager' in module_name or 'database' in message or 'mysql' in message):
            return False
            
        # 如果UI相关模块被取消选中
        if not self.ui_check.isChecked() and ('ui' in module_name or 'window' in message or 'dialog' in message):
            return False
            
        # 如果认证相关模块被取消选中
        if not self.auth_check.isChecked() and ('auth' in module_name or 'login' in message or 'user' in message):
            return False
            
        # 如果系统相关模块被取消选中
        if not self.system_check.isChecked() and ('system' in module_name or 'config' in message or 'startup' in message):
            return False
            
        return True
    
    def update_db_status(self, status, color):
        """更新数据库连接状态显示"""
        self.system_status["database"] = status
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
        self.status_bar.showMessage("日志已清除")
    
    def refresh_logs(self):
        """刷新日志显示"""
        self.status_bar.showMessage("正在刷新日志...")
        self.apply_filters()
        self.status_bar.showMessage("日志已刷新")
    
    def apply_filters(self):
        """应用过滤器"""
        # 这里重新加载日志并应用过滤器
        # 由于我们不保存所有日志，只能清除并显示新的日志
        self.status_bar.showMessage("应用过滤器...")
        # 实际应用中，可能需要保存所有日志并重新过滤
    
    def save_logs(self):
        """保存日志到文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", os.path.join(LOG_DIR, f"system_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_display.toPlainText())
                self.status_bar.showMessage(f"日志已保存到: {file_path}")
            except Exception as e:
                self.status_bar.showMessage(f"保存日志时出错: {str(e)}")
    
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


def show_system_log_viewer():
    """显示系统日志查看器"""
    log_viewer = SystemLogViewer()
    log_viewer.show()
    log_viewer.raise_()
    log_viewer.activateWindow()
    return log_viewer 