#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理操作类模块，处理添加、编辑和删除操作
"""

import logging
from typing import Dict, Any, Callable, Optional

from PyQt5.QtWidgets import QMainWindow, QTableWidget, QMessageBox
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QBrush, QColor

from ui.password_manager.ui_utils import get_row_data, confirm_delete
from ui.password_manager.ui_table import PasswordTable
from ui.components.ui_components import show_message

# 配置日志
logger = logging.getLogger(__name__)


class PasswordOperations:
    """
    密码管理操作类
    
    处理密码的添加、编辑和删除等操作，管理表格的编辑状态。
    """

    def __init__(self, main_window: QMainWindow, table_manager: PasswordTable):
        """
        初始化密码操作
        
        Args:
            main_window (QMainWindow): 主窗口
            table_manager (PasswordTable): 表格管理器
        """
        self.main_window = main_window
        self.table_manager = table_manager
        
    def delete_password(self) -> bool:
        """
        删除密码
        
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        # 获取选中行
        row = self.table_manager.get_selected_row()
        
        if row < 0:
            show_message(self.main_window, "操作错误", "请先选择一个密码记录", QMessageBox.Warning)
            return False
            
        # 确认删除
        if not confirm_delete(self.main_window):
            return False
            
        # 执行删除
        if self.table_manager.delete_row(row):
            self.main_window.statusBar().showMessage(f"密码记录已删除")
            return True
            
        show_message(self.main_window, "删除失败", "无法删除所选密码记录", QMessageBox.Warning)
        return False
        
    def handle_table_double_click(self, index: QModelIndex) -> bool:
        """
        处理表格双击事件
        
        Args:
            index (QModelIndex): 单元格索引
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        # 如果正在编辑，不响应双击
        if self.table_manager.editing_row >= 0:
            return False
            
        # 开始编辑双击的行
        return self.edit_password()
        
    def handle_owner_selection(self, item) -> bool:
        """
        处理所有者选择事件
        
        Args:
            item: 列表项
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        # 如果正在编辑，先询问是否取消编辑
        if self.table_manager.editing_row >= 0:
            if QMessageBox.question(
                self.main_window, 
                "取消编辑", 
                "当前正在编辑，切换人员将取消编辑，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.No:
                return False
                
            self.table_manager.cancel_editing()
            
        # 获取选中的所有者
        owner = item.text()
        
        # 加载所有者的密码
        if self.table_manager.load_passwords(owner):
            self.main_window.statusBar().showMessage(f"已加载 {owner} 的密码记录")
            return True
            
        show_message(self.main_window, "加载失败", f"无法加载 {owner} 的密码记录", QMessageBox.Warning)
        return False
        
    def handle_search(self, keyword: str) -> bool:
        """
        处理搜索
        
        Args:
            keyword (str): 搜索关键词
            
        Returns:
            bool: 搜索成功返回True，否则返回False
        """
        # 如果正在编辑，不执行搜索
        if self.table_manager.editing_row >= 0:
            return False
            
        # 执行搜索
        if self.table_manager.search(keyword):
            if keyword:
                count = self.table_manager.table.rowCount()
                self.main_window.statusBar().showMessage(f"搜索结果: {count} 条记录")
            else:
                self.main_window.statusBar().showMessage(f"搜索已清除")
            return True
            
        return False
        
    def clear_search(self) -> bool:
        """
        清除搜索
        
        Returns:
            bool: 清除成功返回True，否则返回False
        """
        # 如果正在编辑，不清除搜索
        if self.table_manager.editing_row >= 0:
            return False
            
        # 清除搜索框
        from ui.password_manager.ui_layout import PasswordManagerLayout
        if hasattr(self.main_window, "layout_manager") and isinstance(self.main_window.layout_manager, PasswordManagerLayout):
            self.main_window.layout_manager.search_edit.clear()
            
        # 清除搜索结果
        if self.table_manager.clear_search():
            self.main_window.statusBar().showMessage(f"搜索已清除")
            return True
            
        return False