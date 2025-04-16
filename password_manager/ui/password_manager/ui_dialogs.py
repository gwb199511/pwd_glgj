#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理系统对话框模块
提供各种对话框界面
"""

import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QDialogButtonBox, QLineEdit, QLabel
from PyQt5.QtCore import Qt

from ui_components import ModernLineEdit, ModernButton, ModernLabel
from config import COLORS

# 配置日志
logger = logging.getLogger(__name__)

class PasswordConfirmDialog(QDialog):
    """
    密码确认对话框
    
    在修改密码前要求用户输入当前密码进行确认
    """
    
    def __init__(self, parent=None):
        """
        初始化密码确认对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("安全验证")
        self.resize(350, 150)
        self.setModal(True)
        self.password = ""
        self._setup_ui()
        
    def _setup_ui(self):
        """
        设置界面布局和控件
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = ModernLabel("请输入当前密码进行验证", font_size=12, bold=True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        description = ModernLabel("为了保护您的账户安全，在修改密码前需要验证身份", color=COLORS["secondary"])
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        layout.addSpacing(15)
        
        # 密码输入
        form_layout = QFormLayout()
        self.password_edit = ModernLineEdit(placeholder="请输入当前密码", password_mode=True)
        self.password_edit.returnPressed.connect(self.accept)
        form_layout.addRow("密码:", self.password_edit)
        layout.addLayout(form_layout)
        layout.addSpacing(15)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = ModernButton("取消", color=COLORS["secondary"])
        self.cancel_button.clicked.connect(self.reject)
        
        self.confirm_button = ModernButton("确认", color=COLORS["primary"])
        self.confirm_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.confirm_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_password(self):
        """
        获取用户输入的密码
        
        Returns:
            str: 用户输入的密码
        """
        return self.password_edit.text() 