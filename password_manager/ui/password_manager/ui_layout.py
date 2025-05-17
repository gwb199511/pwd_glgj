#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理界面布局类模块，处理界面布局
"""

import logging
from typing import List, Dict, Any, Callable

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QListWidget, QListWidgetItem, QLabel, QLineEdit,
    QToolBar, QAction, QMainWindow, QStatusBar,
    QTableWidget, QAbstractItemView, QFrame, QSizePolicy,
    QToolButton, QMenu
)
from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtGui import QFont, QIcon, QPainter, QPixmap, QColor

from config import FONT_FAMILY, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT
from ui.components.ui_components import ModernLabel, ModernLineEdit, HorizontalLine
from utils.icon_manager import IconManager

# 配置日志
logger = logging.getLogger(__name__)


class PasswordManagerLayout:
    """
    密码管理界面布局类
    
    管理密码管理界面的整体布局，包括工具栏、状态栏、人员列表和密码表格等。
    """

    def __init__(self, parent_window: QMainWindow):
        """
        初始化密码管理界面布局
        
        Args:
            parent_window (QMainWindow): 父窗口
        """
        self.parent = parent_window
        self.widget = QWidget()
        self.current_owner = None
        
        # 初始化图标管理器
        self.icon_manager = IconManager()
        
        self._create_status_bar()
        self._create_toolbar()
        self._setup_layout()
        
    def _create_toolbar(self):
        """
        创建工具栏和搜索框
        
        将菜单按钮和搜索框放置在工具栏中
        """
        # 创建工具栏
        self.toolbar = self.parent.addToolBar("工具栏")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setFont(QFont(FONT_FAMILY, 9))
        
        # 创建菜单按钮字体 - 更大的字体
        menu_button_font = QFont(FONT_FAMILY, 11)
        menu_button_font.setBold(True)
        
        # 创建菜单按钮
        # 文件菜单按钮
        self.file_button = QToolButton(self.parent)
        self.file_button.setText("文件")  # 移除□前缀，只在图标映射中使用
        self.file_button.setPopupMode(QToolButton.InstantPopup)
        self.file_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # 修改为文本旁显示图标
        self.file_button.setFont(menu_button_font)
        self.file_menu = QMenu(self.parent)
        self.file_button.setMenu(self.file_menu)
        
        # 设置文件菜单按钮图标
        file_icon = self.icon_manager.get_icon("□文件")  # 仍然使用带□前缀的图标映射
        if file_icon:
            self.file_button.setIcon(file_icon)
        
        # 工具菜单按钮
        self.tools_button = QToolButton(self.parent)
        self.tools_button.setText("工具")  # 移除□前缀，只在图标映射中使用
        self.tools_button.setPopupMode(QToolButton.InstantPopup)
        self.tools_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.tools_button.setFont(menu_button_font)
        self.tools_menu = QMenu(self.parent)
        self.tools_button.setMenu(self.tools_menu)
        
        # 设置工具菜单按钮图标
        tools_icon = self.icon_manager.get_icon("□工具")  # 仍然使用带□前缀的图标映射
        if tools_icon:
            self.tools_button.setIcon(tools_icon)
        
        # 帮助菜单按钮
        self.help_button = QToolButton(self.parent)
        self.help_button.setText("帮助")  # 移除□前缀，只在图标映射中使用
        self.help_button.setPopupMode(QToolButton.InstantPopup)
        self.help_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.help_button.setFont(menu_button_font)
        self.help_menu = QMenu(self.parent)
        self.help_button.setMenu(self.help_menu)
        
        # 设置帮助菜单按钮图标
        help_icon = self.icon_manager.get_icon("□帮助")  # 仍然使用带□前缀的图标映射
        if help_icon:
            self.help_button.setIcon(help_icon)
        
        # 添加默认菜单项，稍后会被替换
        self.file_menu.addAction("默认文件菜单项")
        self.tools_menu.addAction("默认工具菜单项")
        self.help_menu.addAction("默认帮助菜单项")
        
        # 设置下拉菜单的字体
        menu_font = QFont(FONT_FAMILY, 10)
        self.file_menu.setFont(menu_font)
        self.tools_menu.setFont(menu_font)
        self.help_menu.setFont(menu_font)
        
        # 添加按钮到工具栏
        self.toolbar.addWidget(self.file_button)
        self.toolbar.addWidget(self.tools_button)
        self.toolbar.addWidget(self.help_button)
        
        # 设置菜单按钮的样式 - 修改为支持图标
        menu_button_style = """
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 6px 8px 6px 5px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #f0f0f0;
                border-radius: 3px;
            }
            QToolButton:pressed, QToolButton:checked {
                background-color: #e0e0e0;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """
        
        self.file_button.setStyleSheet(menu_button_style)
        self.tools_button.setStyleSheet(menu_button_style)
        self.help_button.setStyleSheet(menu_button_style)
        
        # 添加一个伸缩器，将搜索框推到右侧
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # 添加搜索标签
        search_label = QLabel("搜索:")
        search_label.setFont(QFont(FONT_FAMILY, 9))
        self.toolbar.addWidget(search_label)
        
        # 创建搜索框
        self.search_edit = ModernLineEdit(placeholder="输入关键词搜索...")
        self.search_edit.setFixedWidth(200)
        self.search_edit.setFont(QFont(FONT_FAMILY, 9))
        
        # 使用Qt的内置清空按钮
        self.search_edit.setClearButtonEnabled(True)
        
        # 设置搜索框样式 - 现在清空按钮样式由ModernLineEdit类控制
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                background-color: #ffffff;
                padding: 2px 5px;
                margin: 3px 10px 3px 5px;
            }
            QLineEdit:focus {
                border-color: #4a6fa5;
            }
        """)
        
        # 添加搜索框到工具栏
        self.toolbar.addWidget(self.search_edit)
        
        # 确保工具栏可见
        self.toolbar.setVisible(True)
        
    def _create_status_bar(self):
        """
        创建状态栏
        """
        self.status_bar = QStatusBar()
        self.parent.setStatusBar(self.status_bar)
        self.status_bar.setFont(QFont(FONT_FAMILY, 9))
        
    def _setup_layout(self):
        """
        设置界面布局
        """
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 左侧人员列表
        self.owner_list_widget = QListWidget()
        self.owner_list_widget.setFont(QFont(FONT_FAMILY, 9))
        self.owner_list_widget.setMinimumWidth(80)  # 减小最小宽度
        self.owner_list_widget.setMaximumWidth(100)  # 减小最大宽度
        
        # 创建标题标签
        owner_title = ModernLabel("人员列表", font_size=10, bold=True)
        owner_title.setAlignment(Qt.AlignCenter)
        
        # 创建左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(owner_title)
        left_layout.addWidget(HorizontalLine())
        left_layout.addWidget(self.owner_list_widget)
        
        # 右侧密码表格
        self.password_table = QTableWidget()
        self.password_table.setFont(QFont(FONT_FAMILY, 9))
        self.password_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.password_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.password_table.setAlternatingRowColors(True)
        self.password_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.password_table.verticalHeader().setVisible(False)
        
        # 设置表格选中行的样式，使用更柔和的背景色
        self.password_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #e6f0f9;  /* 柔和的浅蓝色 */
                color: #333333;  /* 深灰色文字，确保可读性 */
            }
            QTableWidget::item:selected:!active {
                background-color: #f0f5fa;  /* 非激活状态时更浅的背景色 */
                color: #333333;
            }
        """)
        
        # 添加到分割器
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.password_table)
        self.splitter.setStretchFactor(0, 1)  # 左侧列表占更少空间
        self.splitter.setStretchFactor(1, 8)  # 右侧表格占更多空间
        
        main_layout.addWidget(self.splitter)
        self.widget.setLayout(main_layout)
        
        # 设置主窗口中心控件
        self.parent.setCentralWidget(self.widget)
        
    def resize_to_default(self):
        """
        将窗口大小调整为默认值
        """
        self.parent.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
    def update_status(self, message: str):
        """
        更新状态栏信息
        
        Args:
            message (str): 状态消息
        """
        self.status_bar.showMessage(message, 3000)  # 显示3秒
        
    def setup_connections(self, callbacks: Dict[str, Callable]):
        """
        设置信号连接
        
        Args:
            callbacks (Dict[str, Callable]): 回调函数字典
        """
        # 人员列表
        if "owner_selected" in callbacks:
            self.owner_list_widget.itemClicked.connect(callbacks["owner_selected"])
            
        # 搜索
        if "search_changed" in callbacks:
            self.search_edit.textChanged.connect(callbacks["search_changed"])
            
        # 注意：已禁用表格双击编辑功能
            
    def update_owner_list(self, owners: List[str], current_owner: str = None):
        """
        更新人员列表，固定显示三个指定人员
        
        Args:
            owners (List[str]): 人员列表（不再使用，仅保留参数兼容性）
            current_owner (str, optional): 当前选中的人员. 默认为 None.
        """
        self.owner_list_widget.clear()
        
        # 固定显示三个人员
        fixed_owners = ["徐国明", "高文彬", "石帆"]
        
        for owner in fixed_owners:
            item = QListWidgetItem(owner)
            item.setFont(QFont(FONT_FAMILY, 9))
            self.owner_list_widget.addItem(item)
            
        # 如果指定了当前人员，则选中它
        if current_owner and current_owner in fixed_owners:
            items = self.owner_list_widget.findItems(current_owner, Qt.MatchExactly)
            if items:
                self.owner_list_widget.setCurrentItem(items[0])
                self.current_owner = current_owner
        else:
            # 默认选中第一个人员
            self.owner_list_widget.setCurrentRow(0)
            self.current_owner = fixed_owners[0]
        
    def get_selected_owner(self) -> str:
        """
        获取选中的人员
        
        Returns:
            str: 选中的人员名称，如果没有选中则返回None
        """
        item = self.owner_list_widget.currentItem()
        if item:
            return item.text()
        return None 