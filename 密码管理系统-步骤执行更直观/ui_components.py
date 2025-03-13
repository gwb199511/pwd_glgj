#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI组件模块，提供自定义的UI控件
"""

import logging
from PyQt5.QtWidgets import QPushButton, QLineEdit, QLabel, QFrame, QMessageBox
from PyQt5.QtCore import Qt, QSize, QEvent, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap

from config import COLORS, FONT_FAMILY

# 配置日志
logger = logging.getLogger(__name__)


class ModernButton(QPushButton):
    """
    现代风格按钮
    
    自定义按钮外观和行为，支持不同颜色和风格。
    """

    def __init__(self, text="", parent=None, color=COLORS["primary"], flat=False):
        """
        初始化按钮
        
        Args:
            text (str, optional): 按钮文本. 默认为 "".
            parent (QWidget, optional): 父控件. 默认为 None.
            color (str, optional): 按钮颜色. 默认为 COLORS["primary"].
            flat (bool, optional): 是否为扁平风格. 默认为 False.
        """
        super().__init__(text, parent)
        self.color = color
        self.flat_style = flat
        self._setup_style()
        
    def _setup_style(self):
        """
        设置按钮样式
        """
        self.setFont(QFont(FONT_FAMILY, 9))
        
        if self.flat_style:
            style = f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {self.color};
                    padding: 5px 10px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: #f0f0f0;
                    border-radius: 4px;
                }}
                QPushButton:pressed {{
                    background-color: #e0e0e0;
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background-color: {self.color};
                    border: none;
                    color: white;
                    padding: 8px 16px;
                    text-align: center;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {self._lighten_color(self.color, 0.1)};
                }}
                QPushButton:pressed {{
                    background-color: {self._darken_color(self.color, 0.1)};
                }}
                QPushButton:disabled {{
                    background-color: #cccccc;
                    color: #666666;
                }}
            """
        
        self.setStyleSheet(style)
        
    def _lighten_color(self, color, factor=0.1):
        """
        使颜色变亮
        
        Args:
            color (str): 颜色代码，格式为"#RRGGBB"
            factor (float, optional): 变亮因子. 默认为 0.1.
            
        Returns:
            str: 变亮后的颜色代码
        """
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def _darken_color(self, color, factor=0.1):
        """
        使颜色变暗
        
        Args:
            color (str): 颜色代码，格式为"#RRGGBB"
            factor (float, optional): 变暗因子. 默认为 0.1.
            
        Returns:
            str: 变暗后的颜色代码
        """
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        
        return f"#{r:02x}{g:02x}{b:02x}"


class ModernLineEdit(QLineEdit):
    """
    现代风格输入框
    
    自定义输入框外观和行为，支持不同的输入模式。
    """

    def __init__(self, parent=None, placeholder="", password_mode=False):
        """
        初始化输入框
        
        Args:
            parent (QWidget, optional): 父控件. 默认为 None.
            placeholder (str, optional): 占位符文本. 默认为 "".
            password_mode (bool, optional): 是否为密码模式. 默认为 False.
        """
        super().__init__(parent)
        self.placeholder = placeholder
        self.password_mode = password_mode
        self._setup_style()
        
    def _setup_style(self):
        """
        设置输入框样式
        """
        self.setFont(QFont(FONT_FAMILY, 9))
        self.setPlaceholderText(self.placeholder)
        
        if self.password_mode:
            self.setEchoMode(QLineEdit.Password)
            
        style = f"""
            QLineEdit {{
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 2px 6px;
                background-color: {COLORS["light"]};
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS["primary"]};
            }}
        """
        
        self.setStyleSheet(style)


class ModernLabel(QLabel):
    """
    现代风格标签
    
    自定义标签外观，支持不同的字体大小和颜色。
    """

    def __init__(self, text="", parent=None, font_size=9, color=COLORS["text_dark"], bold=False):
        """
        初始化标签
        
        Args:
            text (str, optional): 标签文本. 默认为 "".
            parent (QWidget, optional): 父控件. 默认为 None.
            font_size (int, optional): 字体大小. 默认为 9.
            color (str, optional): 文本颜色. 默认为 COLORS["text_dark"].
            bold (bool, optional): 是否为粗体. 默认为 False.
        """
        super().__init__(text, parent)
        self.font_size = font_size
        self.text_color = color
        self.is_bold = bold
        self._setup_style()
        
    def _setup_style(self):
        """
        设置标签样式
        """
        font = QFont(FONT_FAMILY, self.font_size)
        if self.is_bold:
            font.setBold(True)
        self.setFont(font)
        
        style = f"""
            QLabel {{
                color: {self.text_color};
            }}
        """
        
        self.setStyleSheet(style)


class HorizontalLine(QFrame):
    """
    水平分隔线
    
    自定义水平分隔线外观。
    """

    def __init__(self, parent=None, color=COLORS["border"]):
        """
        初始化水平分隔线
        
        Args:
            parent (QWidget, optional): 父控件. 默认为 None.
            color (str, optional): 分隔线颜色. 默认为 COLORS["border"].
        """
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
        
        style = f"""
            QFrame {{
                border: 1px solid {color};
                border-radius: 0px;
                max-height: 1px;
            }}
        """
        
        self.setStyleSheet(style)


def show_message(parent, title, message, icon=QMessageBox.Information):
    """
    显示消息对话框
    
    Args:
        parent (QWidget): 父控件
        title (str): 对话框标题
        message (str): 消息内容
        icon (QMessageBox.Icon, optional): 消息图标. 默认为 QMessageBox.Information.
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setFont(QFont(FONT_FAMILY, 9))
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()


def show_confirmation(parent, title, message):
    """
    显示确认对话框
    
    Args:
        parent (QWidget): 父控件
        title (str): 对话框标题
        message (str): 消息内容
        
    Returns:
        bool: 如果用户点击确认按钮返回True，否则返回False
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setFont(QFont(FONT_FAMILY, 9))
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg_box.setDefaultButton(QMessageBox.No)
    
    return msg_box.exec_() == QMessageBox.Yes 