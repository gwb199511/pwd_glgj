#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理基础表格类模块
处理表格的基础设置、初始化和样式
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu, QAction
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
        
        # 用于保存初始数据顺序，用于重置排序
        self.initial_data = []
        
        # 设置表格的table_manager属性，方便引导功能直接访问
        self.table.setProperty("table_manager", self)
        
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
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)  # 设置为单元格选择模式，允许选择单个单元格
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 允许多选
        
        # 确保表格可以正确处理复制操作
        self.table.setProperty("copyAvailable", True)  # 设置copyAvailable属性
        
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 默认不可编辑（在编辑模式下会改为SingleClicked）
        
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
        self.table.setColumnWidth(3, 120)
        
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
                background-color: #4a6fa5;
                color: white;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #3a5a8c;
                border-right: 1px solid #3a5a8c;
                font-size: 12px;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #5580b9;
            }
        """)
        
        # 设置表格的滚动条行为
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        # 设置表头可以点击排序
        self.table.setSortingEnabled(True)
        
        # 设置水平表头右键菜单策略
        self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self._show_header_context_menu)
    
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
        
    def _show_header_context_menu(self, position):
        """
        显示表头右键菜单
        
        Args:
            position: 鼠标位置
        """
        # 创建菜单
        menu = QMenu(self.table)
        
        # 添加重置排序选项
        reset_sort_action = QAction("重置排序", self.table)
        reset_sort_action.triggered.connect(self._reset_sorting)
        menu.addAction(reset_sort_action)
        
        # 显示菜单
        menu.exec_(self.table.horizontalHeader().mapToGlobal(position))
    
    def _reset_sorting(self):
        """
        重置表格排序到初始状态
        """
        # 如果没有保存初始数据，则无法重置
        if not hasattr(self, 'initial_data') or not self.initial_data:
            logger.warning("没有保存初始数据，无法重置排序")
            return
            
        # 临时禁用排序，以避免在数据重组时触发排序
        old_sort_state = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        
        # 清空表格
        self.table.setRowCount(0)
        
        # 使用初始数据重新填充表格
        for row_data in self.initial_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                self.table.setItem(row, col, item)
        
        # 重要：清除表头排序指示器
        header = self.table.horizontalHeader()
        header.setSortIndicator(-1, Qt.AscendingOrder)  # 设置为-1表示无排序指示器
        
        # 恢复排序状态
        self.table.setSortingEnabled(old_sort_state)
        
        # 记录日志
        logger.info("已重置表格排序到初始顺序")
        
    def reset_initial_data(self):
        """
        重置初始数据
        
        在刷新或重新加载数据时调用，清除保存的初始数据
        """
        self.initial_data = []
        logger.info("已重置初始数据") 