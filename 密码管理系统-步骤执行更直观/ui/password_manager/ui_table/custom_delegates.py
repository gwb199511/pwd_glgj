#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自定义表格委托模块
实现表格中特殊单元格的自定义渲染
"""

import logging
from PyQt5.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QColor, QBrush, QPainter, QPen, QFont

from config import REQUIRED_FIELDS, PASSWORD_COLUMNS

# 配置日志
logger = logging.getLogger(__name__)


class RequiredFieldDelegate(QStyledItemDelegate):
    """
    必填字段委托类
    
    通过重写绘制方法，为必填字段提供醒目的黄色背景显示
    仅在编辑模式下显示高亮背景
    """
    
    def __init__(self, parent=None):
        """
        初始化委托
        
        Args:
            parent: 父对象
        """
        super(RequiredFieldDelegate, self).__init__(parent)
        # 使用与编辑行相同的蓝色作为必填字段背景色
        self.required_bg_color = QColor("#008C8C")  # 蓝色背景
        self.required_text_color = QColor(255, 0, 0)   # 红色警示文本颜色
        self.empty_text_format = "*必填: {}"
        
        # 跟踪编辑模式状态，默认为非编辑模式
        self.editing_mode = False
        # 当前正在编辑的行，-1表示没有正在编辑的行
        self.editing_row = -1
        
    def set_editing_mode(self, is_editing, row=-1):
        """
        设置编辑模式状态
        
        Args:
            is_editing (bool): 是否处于编辑模式
            row (int): 正在编辑的行索引，默认为-1表示没有正在编辑的行
        """
        self.editing_mode = is_editing
        self.editing_row = row
        # 通知视图更新，刷新显示
        if self.parent():
            self.parent().viewport().update()
        
    def paint(self, painter, option, index):
        """
        绘制单元格
        
        Args:
            painter: QPainter对象
            option: 单元格样式选项
            index: 单元格索引
        """
        # 保存绘制器状态
        painter.save()
        
        # 获取单元格的行和列
        row = index.row()
        column = index.column()
        
        # 判断是否是必填字段
        is_required = column in REQUIRED_FIELDS
        
        # 判断是否需要高亮显示（仅在编辑模式且是当前编辑行或未指定编辑行时高亮）
        is_editing_row = self.editing_mode and (self.editing_row == -1 or self.editing_row == row)
        
        if is_editing_row:
            # 为编辑行的所有单元格设置蓝色背景
            painter.fillRect(option.rect, self.required_bg_color)
            
            # 设置文本选项
            text_option = QStyleOptionViewItem(option)
            text_option.state &= ~QStyle.State_Selected
            
            # 获取单元格文本内容
            text = index.data(Qt.DisplayRole)
            
            if is_required and (not text or text.startswith("*必填:")):
                # 获取字段名称
                field_name = PASSWORD_COLUMNS[column] if column < len(PASSWORD_COLUMNS) else ""
                display_text = self.empty_text_format.format(field_name)
                
                # 设置红色文本
                painter.setPen(QPen(self.required_text_color))
                
                # 设置加粗字体
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                
                # 绘制文本
                text_rect = option.rect.adjusted(4, 0, -4, 0)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)
                
            elif is_required and text:
                # 必填字段有内容时，使用红色文本
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                
                painter.setPen(QPen(self.required_text_color))
                text_rect = option.rect.adjusted(4, 0, -4, 0)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
                
            else:
                # 非必填字段，使用白色文本
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                
                painter.setPen(QPen(Qt.white))
                text_rect = option.rect.adjusted(4, 0, -4, 0)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text if text else "")
                
            # 如果是选中状态，绘制半透明的选中框
            if option.state & QStyle.State_Selected:
                selection_color = QColor(100, 150, 230, 50)  # 半透明蓝色
                painter.fillRect(option.rect, selection_color)
        else:
            # 非编辑模式，使用默认渲染
            QStyledItemDelegate.paint(self, painter, option, index)
        
        # 恢复绘制器状态
        painter.restore() 