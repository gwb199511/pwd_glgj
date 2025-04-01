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
from ui_components import show_message

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
        
    def export_data(self) -> bool:
        """
        导出密码数据
        
        Returns:
            bool: 导出成功返回True，否则返回False
        """
        try:
            # 如果正在编辑，不执行导出
            if self.table_manager.editing_row >= 0:
                show_message(
                    self.main_window, 
                    "无法导出", 
                    "当前正在编辑密码记录，请先完成或取消编辑", 
                    QMessageBox.Warning
                )
                return False
            
            # 导入所需模块
            from PyQt5.QtWidgets import QFileDialog
            import os
            import json
            from password import password_manager
            
            # 获取当前所有者
            owner = self.table_manager.current_owner
            if not owner:
                show_message(
                    self.main_window, 
                    "无法导出", 
                    "请先选择一个人员", 
                    QMessageBox.Warning
                )
                return False
            
            # 获取保存文件路径
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window,
                "导出密码数据",
                os.path.expanduser(f"~/{owner}的密码数据.json"),
                "JSON文件 (*.json)"
            )
            
            if not file_path:
                # 用户取消了操作
                return False
            
            # 获取密码数据
            passwords = password_manager.get_passwords_by_owner(owner)
            
            # 准备导出数据
            export_data = {
                "owner": owner,
                "passwords": passwords
            }
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            # 显示成功消息
            show_message(
                self.main_window,
                "导出成功",
                f"{owner}的密码数据已成功导出到: {file_path}",
                QMessageBox.Information
            )
            
            self.main_window.statusBar().showMessage(f"密码数据导出成功", 5000)
            return True
            
        except Exception as e:
            logger.error(f"导出密码数据时出错: {str(e)}")
            show_message(
                self.main_window,
                "导出失败",
                f"导出密码数据时出错: {str(e)}",
                QMessageBox.Critical
            )
            return False
    
    def import_data(self) -> bool:
        """
        导入密码数据
        
        Returns:
            bool: 导入成功返回True，否则返回False
        """
        try:
            # 如果正在编辑，不执行导入
            if self.table_manager.editing_row >= 0:
                show_message(
                    self.main_window, 
                    "无法导入", 
                    "当前正在编辑密码记录，请先完成或取消编辑", 
                    QMessageBox.Warning
                )
                return False
            
            # 导入所需模块
            from PyQt5.QtWidgets import QFileDialog
            import os
            import json
            from password import password_manager
            
            # 获取当前所有者
            owner = self.table_manager.current_owner
            if not owner:
                show_message(
                    self.main_window, 
                    "无法导入", 
                    "请先选择一个人员", 
                    QMessageBox.Warning
                )
                return False
            
            # 获取打开文件路径
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window,
                "导入密码数据",
                os.path.expanduser("~"),
                "JSON文件 (*.json)"
            )
            
            if not file_path:
                # 用户取消了操作
                return False
            
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 验证数据格式
            if not isinstance(import_data, dict) or "owner" not in import_data or "passwords" not in import_data:
                show_message(
                    self.main_window,
                    "无效的数据格式",
                    "所选文件不包含有效的密码数据格式",
                    QMessageBox.Warning
                )
                return False
            
            # 确认导入
            file_owner = import_data["owner"]
            password_count = len(import_data["passwords"])
            
            if file_owner != owner:
                result = QMessageBox.question(
                    self.main_window,
                    "确认导入",
                    f"文件中的数据属于 {file_owner}，但当前选择的是 {owner}。\n"
                    f"是否仍要导入 {password_count} 条密码记录到 {owner}？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if result != QMessageBox.Yes:
                    return False
            else:
                result = QMessageBox.question(
                    self.main_window,
                    "确认导入",
                    f"是否导入 {password_count} 条密码记录？\n"
                    f"这将覆盖现有记录。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if result != QMessageBox.Yes:
                    return False
            
            # 执行导入
            passwords = import_data["passwords"]
            
            # 清除现有数据
            password_manager.db.set(owner, [])
            
            # 添加导入的数据
            success_count = 0
            for password in passwords:
                result, _ = password_manager.add_password(owner, password)
                if result:
                    success_count += 1
            
            # 重新加载表格
            self.table_manager.load_passwords(owner)
            
            # 显示成功消息
            show_message(
                self.main_window,
                "导入成功",
                f"成功导入 {success_count} 条密码记录",
                QMessageBox.Information
            )
            
            self.main_window.statusBar().showMessage(f"密码数据导入成功: {success_count} 条记录", 5000)
            return True
            
        except Exception as e:
            logger.error(f"导入密码数据时出错: {str(e)}")
            show_message(
                self.main_window,
                "导入失败",
                f"导入密码数据时出错: {str(e)}",
                QMessageBox.Critical
            )
            return False