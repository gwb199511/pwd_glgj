#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理操作类模块，处理添加、编辑和删除操作
"""

import logging
from typing import Dict, Any, Callable, Optional, List

from PyQt5.QtWidgets import QMainWindow, QTableWidget, QMessageBox
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QBrush, QColor

from ui.password_manager.ui_utils import get_row_data, confirm_delete
from ui.password_manager.ui_table import PasswordTable
from ui.components.ui_components import show_message
from core.password import password_manager

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

    def handle_add_owner(self) -> bool:
        """
        处理添加人员事件
        
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        # 获取人员名称
        new_owner = self.main_window.layout_manager.add_owner_dialog()
        if not new_owner:
            return False
            
        # 获取所有人员列表
        owners = password_manager.get_all_owners()
        
        # 检查人员名称是否已存在
        if new_owner in owners:
            show_message(
                self.main_window,
                "添加失败",
                f"人员\"{new_owner}\"已存在",
                QMessageBox.Warning
            )
            return False
            
        # 添加人员
        try:
            # 创建一条默认记录，确保人员能够被查询到
            # 格式为: [项目名称, 功能, IP地址, 账户, 密码, 所在区域, 网络类型, 其他账号]
            default_record = [
                "示例项目", 
                "示例功能", 
                "127.0.0.1", 
                "username", 
                "password", 
                "默认区域", 
                "内网", 
                "备注信息"
            ]
            
            # 为新人员创建包含默认记录的列表
            password_manager.db.set(new_owner, [default_record])
            logger.info(f"已添加新人员: {new_owner}，并创建了默认记录")
            
            # 重新加载人员列表
            self._refresh_owner_list(new_owner)
            
            self.main_window.statusBar().showMessage(f"已添加新人员: {new_owner}")
            return True
        except Exception as e:
            logger.error(f"添加人员时出错: {str(e)}")
            show_message(
                self.main_window,
                "添加失败",
                f"无法添加人员: {str(e)}",
                QMessageBox.Warning
            )
            return False
    
    def handle_edit_owner(self) -> bool:
        """
        处理编辑人员名称事件
        
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        # 获取当前选中的人员
        current_owner = self.main_window.layout_manager.get_selected_owner()
        if not current_owner:
            show_message(
                self.main_window,
                "编辑失败",
                "请先选择一个人员",
                QMessageBox.Warning
            )
            return False
            
        # 获取新名称
        new_name = self.main_window.layout_manager.edit_owner_dialog(current_owner)
        if not new_name:
            return False
            
        # 获取所有人员列表
        owners = password_manager.get_all_owners()
        
        # 检查新名称是否已存在
        if new_name in owners:
            show_message(
                self.main_window,
                "编辑失败",
                f"人员\"{new_name}\"已存在",
                QMessageBox.Warning
            )
            return False
            
        # 修改人员名称
        try:
            # 获取当前人员的密码记录
            passwords = password_manager.db.get(current_owner)
            
            # 删除原人员记录
            password_manager.db.delete(current_owner)
            
            # 创建新人员记录
            password_manager.db.set(new_name, passwords)
            
            logger.info(f"已将人员\"{current_owner}\"重命名为\"{new_name}\"")
            
            # 重新加载人员列表
            self._refresh_owner_list(new_name)
            
            self.main_window.statusBar().showMessage(f"已将人员\"{current_owner}\"重命名为\"{new_name}\"")
            return True
        except Exception as e:
            logger.error(f"编辑人员名称时出错: {str(e)}")
            show_message(
                self.main_window,
                "编辑失败",
                f"无法修改人员名称: {str(e)}",
                QMessageBox.Warning
            )
            return False
    
    def handle_delete_owner(self) -> bool:
        """
        处理删除人员事件
        
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        # 获取当前选中的人员
        current_owner = self.main_window.layout_manager.get_selected_owner()
        if not current_owner:
            show_message(
                self.main_window,
                "删除失败",
                "请先选择一个人员",
                QMessageBox.Warning
            )
            return False
            
        # 确认删除
        if not self.main_window.layout_manager.confirm_delete_owner(current_owner):
            return False
            
        # 删除人员
        try:
            # 删除人员的密码记录
            password_manager.db.delete(current_owner)
            logger.info(f"已删除人员: {current_owner}")
            
            # 重新加载人员列表
            owners = password_manager.get_all_owners()
            self._refresh_owner_list(owners[0] if owners else None)
            
            self.main_window.statusBar().showMessage(f"已删除人员: {current_owner}")
            return True
        except Exception as e:
            logger.error(f"删除人员时出错: {str(e)}")
            show_message(
                self.main_window,
                "删除失败",
                f"无法删除人员: {str(e)}",
                QMessageBox.Warning
            )
            return False
    
    def _refresh_owner_list(self, select_owner: str = None):
        """
        刷新人员列表
        
        Args:
            select_owner (str, optional): 刷新后选中的人员. 默认为 None.
        """
        try:
            # 尝试先清空数据缓存，确保从数据库获取最新数据
            # 对于MySQL存储，这会强制重新查询数据库
            password_manager.db.data = {}
            
            # 获取所有人员列表
            owners = password_manager.get_all_owners()
            logger.info(f"刷新人员列表: {owners}")
            
            # 更新人员列表
            self.main_window.layout_manager.update_owner_list(owners, select_owner)
            
            # 如果指定了选中人员，则加载该人员的密码记录
            if select_owner:
                # 触发选择事件
                items = self.main_window.layout_manager.owner_list_widget.findItems(select_owner, Qt.MatchExactly)
                if items:
                    self.handle_owner_selection(items[0])
            else:
                # 默认选中第一个人员
                current_item = self.main_window.layout_manager.owner_list_widget.currentItem()
                if current_item:
                    self.handle_owner_selection(current_item)
        except Exception as e:
            logger.error(f"刷新人员列表时出错: {str(e)}")
            show_message(
                self.main_window,
                "刷新失败",
                f"无法刷新人员列表: {str(e)}",
                QMessageBox.Warning
            )