#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理界面工具类模块，提供辅助功能
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from PyQt5.QtWidgets import QMessageBox, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush

from config import FONT_FAMILY, COLORS, PASSWORD_COLUMNS, REQUIRED_FIELDS
from ui_components import show_message, show_confirmation

# 配置日志
logger = logging.getLogger(__name__)


def create_table_item(text: str, editable: bool = False) -> QTableWidgetItem:
    """
    创建表格项
    
    Args:
        text (str): 项文本
        editable (bool, optional): 是否可编辑. 默认为 False.
        
    Returns:
        QTableWidgetItem: 表格项
    """
    item = QTableWidgetItem(str(text))
    item.setFont(QFont(FONT_FAMILY, 9))
    
    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        
    return item


def set_table_headers(table: QTableWidget, headers: List[str]) -> None:
    """
    设置表格标题，并使表格列宽随窗口缩放自动调整
    
    设置所有列为自动拉伸模式，使表格能够完全填充可用空间，
    同时根据各列的相对重要性和典型内容长度分配不同的初始宽度比例。
    
    Args:
        table (QTableWidget): 表格控件
        headers (List[str]): 标题列表
    """
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    
    # 设置标题样式
    header = table.horizontalHeader()
    header.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
    # 设置初始列宽比例 (总和为100)
    # 这些值将作为初始宽度，但在窗口缩放时，所有列都会按比例调整
    column_widths = {
        0: 150,  # 项目名称 (较重要)
        1: 180,  # 功能 (内容可能较长)
        2: 110,  # IP地址
        3: 100,  # 账户
        4: 100,  # 密码
        5: 90,   # 所在区域
        6: 90,   # 网络类型
        7: 150   # 其他账号 (可能有较长备注)
    }
    
    # 先设置每一列的初始宽度
    for col, width in column_widths.items():
        if col < len(headers):
            table.setColumnWidth(col, width)
    
    # 然后设置所有列都使用Stretch模式，这样就能在窗口调整大小时自动缩放
    for col in range(len(headers)):
        header.setSectionResizeMode(col, header.Stretch)
    
    # 启用表格的拉伸属性，确保表格完全填充可用空间
    header.setStretchLastSection(True)


def highlight_required_fields(table: QTableWidget, row: int) -> None:
    """
    高亮显示必填字段
    
    Args:
        table (QTableWidget): 表格控件
        row (int): 行索引
    """
    # 暂时存储并清除表格样式表，以避免样式冲突
    original_style = table.styleSheet()
    table.setStyleSheet("")
    
    # 使用更明显的颜色来突出显示必填字段
    required_bg_color = QColor("#ffecb3")  # 更明显的暖黄色背景
    
    for col in REQUIRED_FIELDS:
        if col < table.columnCount():
            item = table.item(row, col)
            if item:
                # 设置明显的背景色 - 尝试多种方法确保至少一种能生效
                item.setBackground(required_bg_color)
                item.setData(Qt.BackgroundRole, QBrush(required_bg_color))
                
                # 使用加粗字体增强视觉效果
                font = item.font()
                font.setBold(True)  # 加粗字体
                item.setFont(font)
                
                # 设置工具提示提醒用户这是必填字段
                field_name = PASSWORD_COLUMNS[col] if col < len(PASSWORD_COLUMNS) else ""
                item.setToolTip(f"必填字段: {field_name}")
                
                # 如果单元格为空，显示提示文本
                if not item.text():
                    # 设置为明显的红色文本作为提示
                    item.setForeground(QColor("#ff5252"))
                    item.setText(f"*请输入{field_name}")
                    # 用Data记录这是一个placeholder，方便编辑时清除
                    item.setData(Qt.UserRole, "placeholder")

    # 恢复原始样式表
    table.setStyleSheet(original_style)


def validate_password_entry(table: QTableWidget, row: int) -> bool:
    """
    验证密码记录
    
    检查必填字段是否已填写。
    
    Args:
        table (QTableWidget): 表格控件
        row (int): 行索引
        
    Returns:
        bool: 如果所有必填字段都已填写则返回True，否则返回False
    """
    for col in REQUIRED_FIELDS:
        if col < table.columnCount():
            item = table.item(row, col)
            if not item or not item.text().strip():
                field_name = PASSWORD_COLUMNS[col]
                show_message(table.parent(), "输入错误", f"请输入{field_name}", QMessageBox.Warning)
                table.setCurrentCell(row, col)
                return False
                
    return True


def get_row_data(table: QTableWidget, row: int) -> List[str]:
    """
    获取行数据
    
    Args:
        table (QTableWidget): 表格控件
        row (int): 行索引
        
    Returns:
        List[str]: 行数据列表
    """
    data = []
    
    # 只获取实际数据列的值（对应PASSWORD_COLUMNS中的列），不包括操作列
    for col in range(min(table.columnCount(), len(PASSWORD_COLUMNS))):
        item = table.item(row, col)
        text = item.text().strip() if item else ""
        data.append(text)
        
    return data


def confirm_delete(parent) -> bool:
    """
    确认删除操作
    
    Args:
        parent: 父控件
        
    Returns:
        bool: 如果用户确认删除返回True，否则返回False
    """
    return show_confirmation(parent, "确认删除", "确定要删除选中的密码记录吗？\n\n此操作不可撤销。")


def get_formatted_date() -> str:
    """
    获取格式化的当前日期时间
    
    Returns:
        str: 格式化的日期时间字符串
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S") 