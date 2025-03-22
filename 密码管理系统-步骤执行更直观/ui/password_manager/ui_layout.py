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
    QTableWidget, QAbstractItemView, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon

from config import FONT_FAMILY, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT
from ui_components import ModernLabel, ModernLineEdit, HorizontalLine

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
        
        self._create_status_bar()
        self._create_toolbar()
        self._setup_layout()
        
    def _create_toolbar(self):
        """
        创建工具栏和搜索框
        
        注意：搜索框现在位于菜单栏，工具栏仅作为预留位置保留
        """
        # 创建一个新的工具栏，但暂时不显示
        # 仅保留这段代码以备将来需要在工具栏上添加其他工具
        self.toolbar = self.parent.addToolBar("工具栏")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setFont(QFont(FONT_FAMILY, 9))
        # 隐藏工具栏，因为现在搜索框已移至菜单栏
        self.toolbar.setVisible(False)
        
        # 将搜索框添加到菜单栏
        menubar = self.parent.menuBar()
        
        # 添加搜索框
        self.search_edit = ModernLineEdit(placeholder="输入关键词搜索...")
        self.search_edit.setFixedWidth(180)
        # 调整搜索框的高度以匹配菜单栏高度
        self.search_edit.setFixedHeight(22)
        self.search_edit.setFont(QFont(FONT_FAMILY, 9))
        self.search_edit.setClearButtonEnabled(True)
        # 设置样式使其与菜单栏更协调
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                background-color: #ffffff;
                padding: 1px 18px 1px 3px;
                margin-top: 1px;
            }
        """)
        
        # 创建一个包含搜索框的容器部件
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 10, 0)  # 右侧留一点间距
        search_layout.setSpacing(0)
        search_layout.addWidget(self.search_edit)
        
        # 将搜索框容器设置为右上角部件
        menubar.setCornerWidget(search_container, Qt.TopRightCorner)
        
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
        self.owner_list_widget.setMinimumWidth(100)  # 减小最小宽度
        self.owner_list_widget.setMaximumWidth(150)  # 减小最大宽度
        
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
        self.splitter.setStretchFactor(1, 5)  # 右侧表格占更多空间
        
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