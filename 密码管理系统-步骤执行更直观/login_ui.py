#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
登录界面模块，实现用户登录和注册功能
"""

import sys
import logging
from typing import Callable, Optional, Dict

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QCheckBox, 
    QDialog, QMessageBox, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap

from config import FONT_FAMILY, COLORS, VERSION
from user import user_manager
from ui_components import (
    ModernButton, ModernLineEdit, ModernLabel, 
    HorizontalLine, show_message
)

# 配置日志
logger = logging.getLogger(__name__)


class RegisterDialog(QDialog):
    """
    注册对话框
    
    提供用户注册界面，支持用户名和密码的输入和验证。
    """

    def __init__(self, parent=None):
        """
        初始化注册对话框
        
        Args:
            parent (QWidget, optional): 父控件. 默认为 None.
        """
        super().__init__(parent)
        self.setWindowTitle("注册新用户")
        self.setMinimumWidth(300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        
    def _setup_ui(self):
        """
        设置界面布局和控件
        """
        layout = QVBoxLayout()
        
        # 标题
        title_label = ModernLabel("创建新账户", font_size=14, bold=True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addSpacing(10)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 用户名
        self.username_edit = ModernLineEdit(placeholder="输入用户名")
        form_layout.addRow("用户名:", self.username_edit)
        
        # 密码
        self.password_edit = ModernLineEdit(placeholder="输入密码", password_mode=True)
        form_layout.addRow("密码:", self.password_edit)
        
        # 确认密码
        self.confirm_password_edit = ModernLineEdit(placeholder="再次输入密码", password_mode=True)
        form_layout.addRow("确认密码:", self.confirm_password_edit)
        
        layout.addLayout(form_layout)
        layout.addSpacing(20)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        self.register_button = ModernButton("注册", color=COLORS["success"])
        self.register_button.clicked.connect(self._register)
        
        self.cancel_button = ModernButton("取消", color=COLORS["secondary"])
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.register_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def _register(self):
        """
        处理注册操作
        
        验证用户输入并调用用户管理器的注册方法。
        """
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        # 验证输入
        if not username:
            show_message(self, "输入错误", "请输入用户名", QMessageBox.Warning)
            self.username_edit.setFocus()
            return
            
        if not password:
            show_message(self, "输入错误", "请输入密码", QMessageBox.Warning)
            self.password_edit.setFocus()
            return
            
        if password != confirm_password:
            show_message(self, "输入错误", "两次输入的密码不一致", QMessageBox.Warning)
            self.confirm_password_edit.setFocus()
            return
            
        # 调用注册方法
        success, message = user_manager.register(username, password)
        
        if success:
            show_message(self, "注册成功", "新用户已创建，现在您可以登录了")
            self.accept()
        else:
            show_message(self, "注册失败", message, QMessageBox.Warning)


class LoginUI(QWidget):
    """
    登录界面
    
    提供用户登录界面，支持记住密码和注册新用户。
    """

    # 定义登录成功信号
    login_success = pyqtSignal(str)

    def __init__(self):
        """
        初始化登录界面
        """
        super().__init__()
        self.setWindowTitle(f"密码管理系统 v{VERSION} - 登录")
        self.resize(400, 300)
        self._setup_ui()
        self.load_saved_credentials()
        
    def _setup_ui(self):
        """
        设置界面布局和控件
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = ModernLabel("密码管理系统", font_size=18, bold=True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        version_label = ModernLabel(f"v{VERSION}", font_size=8, color=COLORS["secondary"])
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        layout.addSpacing(20)
        
        # 用户名输入
        username_layout = QVBoxLayout()
        username_label = ModernLabel("用户名")
        self.username_edit = ModernLineEdit(placeholder="输入用户名")
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_edit)
        layout.addLayout(username_layout)
        
        layout.addSpacing(10)
        
        # 密码输入
        password_layout = QVBoxLayout()
        password_label = ModernLabel("密码")
        self.password_edit = ModernLineEdit(placeholder="输入密码", password_mode=True)
        self.password_edit.returnPressed.connect(self.login)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_edit)
        layout.addLayout(password_layout)
        
        layout.addSpacing(10)
        
        # 记住密码
        remember_layout = QHBoxLayout()
        self.remember_checkbox = QCheckBox("记住密码")
        self.remember_checkbox.setFont(QFont(FONT_FAMILY, 9))
        remember_layout.addWidget(self.remember_checkbox)
        remember_layout.addStretch()
        layout.addLayout(remember_layout)
        
        layout.addSpacing(20)
        
        # 登录按钮
        login_button = ModernButton("登录", color=COLORS["primary"])
        login_button.clicked.connect(self.login)
        layout.addWidget(login_button)
        
        layout.addSpacing(10)
        
        # 注册链接
        register_layout = QHBoxLayout()
        register_layout.addStretch()
        register_label = ModernLabel("还没有账号？")
        register_layout.addWidget(register_label)
        
        register_button = ModernButton("注册新用户", flat=True, color=COLORS["primary"])
        register_button.clicked.connect(self.register)
        register_layout.addWidget(register_button)
        register_layout.addStretch()
        
        layout.addLayout(register_layout)
        
        layout.addStretch()
        
        self.setLayout(layout)
        
    def login(self):
        """
        处理登录操作
        
        验证用户输入并调用用户管理器的登录方法。
        """
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not username or not password:
            show_message(self, "输入错误", "请输入用户名和密码", QMessageBox.Warning)
            return
            
        # 调用登录方法
        self._perform_login(username, password)
        
    def _perform_login(self, username: str, password: str):
        """
        执行登录操作
        
        Args:
            username (str): 用户名
            password (str): 密码
        """
        success, message = user_manager.login(username, password)
        
        if success:
            logger.info(f"用户 {username} 登录成功")
            
            # 处理记住密码
            if self.remember_checkbox.isChecked():
                user_manager.save_credentials(username, password)
            else:
                user_manager.clear_saved_credentials()
                
            # 发送登录成功信号
            self.login_success.emit(username)
        else:
            logger.warning(f"用户登录失败: {message}")
            show_message(self, "登录失败", message, QMessageBox.Warning)
            
    def register(self):
        """
        打开注册对话框
        """
        dialog = RegisterDialog(self)
        dialog.exec_()
        
    def load_saved_credentials(self):
        """
        加载保存的登录凭证
        """
        credentials = user_manager.load_saved_credentials()
        
        if credentials:
            username = credentials.get("username")
            password = credentials.get("password")
            
            if username and password:
                self.username_edit.setText(username)
                self.password_edit.setText(password)
                self.remember_checkbox.setChecked(True)
                
    def clear_password(self):
        """
        清除密码输入框
        """
        self.password_edit.clear()
        
    def run(self):
        """
        显示登录界面
        """
        self.show() 