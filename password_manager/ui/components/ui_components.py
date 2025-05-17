#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI组件模块，提供自定义的UI控件
"""

import logging
from PyQt5.QtWidgets import QPushButton, QLineEdit, QLabel, QFrame, QMessageBox, QToolButton, QStyle, QDialog, QVBoxLayout, QHBoxLayout
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
        self._clear_button = None # 初始化清空按钮成员变量
        self._setup_style()

    def _setup_style(self):
        """
        设置输入框样式
        """
        self.setFont(QFont(FONT_FAMILY, 9))
        self.setPlaceholderText(self.placeholder)
        
        if self.password_mode:
            self.setEchoMode(QLineEdit.Password)
            
        # 基本样式，确保有足够的右内边距给按钮
        style = f"""
            QLineEdit {{
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 2px 36px 2px 6px; /* 右内边距调整为36px */
                background-color: {COLORS["light"]};
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS["primary"]};
            }}
        """
        self.setStyleSheet(style)

    def setClearButtonEnabled(self, enable):
        """
        重写setClearButtonEnabled以获取并存储清空按钮的引用。
        """
        super().setClearButtonEnabled(enable)
        if enable:
            # 尝试通过对象名称找到标准的清空按钮，如果失败再用类型查找
            button = self.findChild(QToolButton, "qt_QLineEdit_clearbutton")
            if not button:
                button = self.findChild(QToolButton)
            self._clear_button = button
            if self._clear_button:
                # 设置一个初始的、更可靠的图标
                self._clear_button.setIcon(self.style().standardIcon(QStyle.SP_LineEditClearButton))
                # 移除可能冲突的子控件样式，由resizeEvent控制
                self._clear_button.setStyleSheet("") 
        else:
            self._clear_button = None

    def resizeEvent(self, event):
        """
        重写尺寸变化事件处理器，调整清空按钮位置
        """
        super().resizeEvent(event)
        
        if self._clear_button and self.isClearButtonEnabled():
            # 按钮大小为输入框高度减去一定的垂直边距 (例如上下各4px)
            button_size = self.height() - 8 
            self._clear_button.setFixedSize(button_size, button_size)
            
            # 图标大小略小于按钮，使其有边距感
            self._clear_button.setIconSize(QSize(int(button_size * 0.65), int(button_size * 0.65)))
            
            # 将按钮的右边缘定位在距离输入框右边缘10px的位置
            # 按钮的x坐标 = 输入框宽度 - 按钮宽度 - 10px (右侧视觉边距)
            x = self.width() - button_size - 10
            y = (self.height() - button_size) // 2 # 垂直居中
            self._clear_button.move(x, y)
            
            # 可以保留或移除按钮的自定义样式，因为标准图标通常足够
            # 如果需要自定义背景等，可以在这里设置
            # self._clear_button.setStyleSheet("...")


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


class ModernErrorDialog(QMessageBox):
    """
    现代风格错误对话框
    
    自定义错误对话框外观和行为，提供美观的错误提示界面。
    """
    
    def __init__(self, parent=None, title="错误", message="发生错误", detailed_text=None):
        """
        初始化错误对话框
        
        Args:
            parent (QWidget, optional): 父控件. 默认为 None.
            title (str, optional): 对话框标题. 默认为 "错误".
            message (str, optional): 错误消息. 默认为 "发生错误".
            detailed_text (str, optional): 详细错误信息. 默认为 None.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setText(message)
        self.setIcon(QMessageBox.Critical)
        
        # 设置字体
        self.setFont(QFont(FONT_FAMILY, 9))
        
        # 如果有详细信息，则设置
        if detailed_text:
            self.setDetailedText(detailed_text)
        
        # 应用样式
        self._setup_style()
    
    def _setup_style(self):
        """设置对话框样式"""
        # 自定义对话框样式
        style = f"""
            QMessageBox {{
                background-color: white;
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
            }}
            QMessageBox QLabel {{
                color: {COLORS["text_dark"]};
                font-family: {FONT_FAMILY};
            }}
            QMessageBox QPushButton {{
                background-color: {COLORS["primary"]};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: {FONT_FAMILY};
            }}
            QMessageBox QPushButton:hover {{
                background-color: {self._lighten_color(COLORS["primary"])};
            }}
            QMessageBox QPushButton:pressed {{
                background-color: {self._darken_color(COLORS["primary"])};
            }}
            QMessageBox QTextEdit {{
                background-color: {COLORS["light"]};
                border: 1px solid {COLORS["border"]};
                font-family: {FONT_FAMILY};
            }}
        """
        self.setStyleSheet(style)
        
        # 设置最小宽度
        self.setMinimumWidth(400)
    
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


class ModernInputDialog(QDialog):
    """
    现代风格输入对话框
    
    自定义输入对话框外观和行为，提供与整个项目一致的风格。
    """
    
    def __init__(self, parent=None, title="输入", label_text="请输入:", default_text=""):
        """
        初始化输入对话框
        
        Args:
            parent (QWidget, optional): 父控件. 默认为 None.
            title (str, optional): 对话框标题. 默认为 "输入".
            label_text (str, optional): 标签文本. 默认为 "请输入:".
            default_text (str, optional): 默认文本. 默认为 "".
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumWidth(300)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 添加标签
        self.label = ModernLabel(label_text, self, font_size=10)
        layout.addWidget(self.label)
        
        # 添加输入框
        self.input_field = ModernLineEdit(self, placeholder="")
        self.input_field.setText(default_text)
        self.input_field.setMinimumHeight(30)
        layout.addWidget(self.input_field)
        
        layout.addSpacing(10)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 取消按钮
        self.cancel_button = ModernButton("取消", self, color=COLORS["secondary"])
        self.cancel_button.clicked.connect(self.reject)
        
        # 确认按钮
        self.ok_button = ModernButton("确定", self)
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        
        # 添加按钮到布局
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        # 设置样式
        self.setStyleSheet(f"""
            QDialog {{
                background-color: white;
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
            }}
        """)
        
        # 设置焦点
        self.input_field.setFocus()
    
    def get_input(self):
        """
        获取用户输入
        
        Returns:
            tuple: (输入文本, 是否点击了确定按钮)
        """
        result = self.exec_()
        return (self.input_field.text(), result == QDialog.Accepted)


def show_input_dialog(parent, title, label_text, default_text=""):
    """
    显示输入对话框
    
    Args:
        parent (QWidget): 父控件
        title (str): 对话框标题
        label_text (str): 标签文本
        default_text (str, optional): 默认文本. 默认为 "".
        
    Returns:
        tuple: (输入文本, 是否点击了确定按钮)
    """
    dialog = ModernInputDialog(parent, title, label_text, default_text)
    return dialog.get_input() 