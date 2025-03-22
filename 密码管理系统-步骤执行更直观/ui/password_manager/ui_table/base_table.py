#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理基础表格类模块
处理表格的基础设置、初始化和样式
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from config import PASSWORD_COLUMNS
from ui.password_manager.ui_utils import set_table_headers
from ui.password_manager.ui_table.custom_delegates import RequiredFieldDelegate

# 配置日志
logger = logging.getLogger(__name__)


class BasePasswordTable:
    """
    密码表格基础类
    
    管理密码表格的基础功能，包括表格设置、样式、菜单等。
    """

    def __init__(self, table_widget: QTableWidget):
        """
        初始化密码表格
        
        Args:
            table_widget (QTableWidget): 表格控件
        """
        self.table = table_widget
        self.current_owner = None
        self.search_results = None
        self.search_mode = False
        self.editing_row = -1  # 当前正在编辑的行，-1表示没有正在编辑的行
        
        self._setup_table()
        self._setup_custom_delegates()  # 设置自定义委托
        self._setup_context_menu()  # 设置右键菜单
        
        # 连接单元格点击信号，处理占位符文本
        self.table.itemClicked.connect(self._handle_item_clicked)
    
    def _handle_item_clicked(self, item):
        """
        处理单元格点击事件
        
        Args:
            item (QTableWidgetItem): 被点击的单元格项
        """
        # 如果单元格是"<双击添加>"，则开始编辑
        if item and item.text() == "<双击添加>" and self.editing_row == -1:
            row = item.row()
            col = item.column()
            item.setText("")
            self.table.editItem(item)
    
    def _setup_table(self):
        """
        设置表格属性和样式
        """
        # 设置表格属性
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)  # 允许选择单元格
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 允许多选
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 默认不可编辑
        
        # 美化表格整体外观
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d8d8d8;
                background-color: white;
                alternate-background-color: #f9f9f9;
                selection-background-color: #e3f2fd;
                selection-color: #333333;
            }
            QTableWidget::item {
                padding: 2.5px;
                border: none;
            }
            /* 被选中项的样式 - 降低不透明度以便看到背景色 */
            QTableWidget::item:selected {
                background-color: rgba(227, 242, 253, 180); /* 半透明的选中色 */
                color: #333333;
            }
            /* 移除必填字段的背景色样式，由委托类负责处理 */
        """)
        
        # 设置表格列和列宽
        set_table_headers(self.table, PASSWORD_COLUMNS)
        
        # 启用垂直表头作为序号
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(30)  # 设置行高
        self.table.verticalHeader().setMinimumWidth(15)  # 设置最小宽度
        self.table.verticalHeader().setMaximumWidth(25)  # 设置最大宽度，防止占用过多空间
        
        # 设置列宽
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # 项目名称列宽一点
        self.table.setColumnWidth(0, 150)
        
        # IP地址列宽一点
        self.table.setColumnWidth(1, 120)
        
        # 用户名列宽一点
        self.table.setColumnWidth(2, 120)
        
        # 备注列宽一点
        self.table.setColumnWidth(3, 200)
        
        # 密码列宽一点
        self.table.setColumnWidth(4, 200)  # 设置最大宽度，防止占用过多空间
        
        # 美化行号UI
        self.table.verticalHeader().setStyleSheet("""
            QHeaderView::section { 
                background-color: #f2f2f2; 
                color: #555555;
                border: none;
                border-right: 1px solid #cccccc;
                font-size: 11px;
                font-weight: bold;
                padding-left: 4px;
                padding-right: 4px;
                border-radius: 0px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #e6e6e6;
            }
        """)
        
        # 美化列表头
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #f2f2f2;
                color: #333333;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #cccccc;
                border-right: 1px solid #cccccc;
                font-size: 12px;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #e6e6e6;
            }
        """)
        
        # 设置表格的滚动条行为
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        # 设置表头可以点击排序
        self.table.setSortingEnabled(True)
    
    def _setup_custom_delegates(self):
        """
        设置自定义委托
        
        为表格添加自定义的单元格委托，实现必填字段黄色背景等特殊效果
        """
        # 创建并设置必填字段委托
        self.required_field_delegate = RequiredFieldDelegate(self.table)
        self.table.setItemDelegate(self.required_field_delegate)
        
        logger.info("已设置必填字段自定义委托")
    
    def _setup_context_menu(self):
        """
        设置表格右键菜单
        """
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        # 连接信号在子类中实现 