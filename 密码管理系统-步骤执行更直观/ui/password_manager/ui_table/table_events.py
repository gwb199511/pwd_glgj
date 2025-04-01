#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理表格事件模块
处理表格的事件过滤器和右键菜单
"""

import logging
from typing import List, Tuple, Optional

# 配置日志
logger = logging.getLogger(__name__)

from PyQt5.QtWidgets import QMenu, QAction, QTableWidgetItem, QApplication
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QIcon

from config import PASSWORD_COLUMNS
from ui.password_manager.ui_guide import start_walkthrough

class TableEventsMixin:
    """
    表格事件管理混入类
    
    提供表格事件处理的方法，如右键菜单等
    """
    
    def _show_context_menu(self, position):
        """
        显示右键菜单
        
        Args:
            position: 鼠标位置
        """
        # 如果正在编辑，不显示菜单
        if self.editing_row >= 0:
            return
            
        # 获取当前鼠标位置下的行和列
        row = self.table.rowAt(position.y())
        col = self.table.columnAt(position.x())
        
        # 只在有效行上显示菜单
        if row >= 0:
            # 获取所有选中的单元格
            selected_items = self.table.selectedItems()
            # 获取选中的行（去重）
            selected_rows = list(set(item.row() for item in selected_items))
            selected_count = len(selected_rows)
            
            # 找出选中的密码列单元格
            password_cells = [(item.row(), item.column()) for item in selected_items if item.column() == 4]
            password_cell_count = len(password_cells)
            
            # 记录右键菜单信息到日志
            logger.info(f"右键菜单 - 当前行: {row + 1}, 当前列: {col + 1}, 选中行数: {selected_count}, 选中行: {[r + 1 for r in selected_rows]}")
            logger.info(f"选中的密码单元格数量: {password_cell_count}")
            
            # 创建菜单
            menu = QMenu(self.table)
            
            # 添加菜单项 - 检查是否有密码列被选中
            if password_cell_count > 0:
                # 复制
                copy_action = QAction(QIcon(""), "复制", self.table)
                copy_action.triggered.connect(self.copy_selected_content)
                menu.addAction(copy_action)
                
                # 生成新密码
                if selected_items:
                    menu.addSeparator()
                    
                    # 生成随机密码并更新到服务器
                    ssh_update_action = QAction(QIcon(""), "生成16位随机密码\n并更新到服务器", self.table)
                    ssh_update_action.triggered.connect(lambda: self._generate_and_update_passwords(password_cells, 16))
                    menu.addAction(ssh_update_action)
            else:
                # 复制内容
                copy_action = QAction(QIcon(""), "复制", self.table)
                copy_action.triggered.connect(self.copy_selected_content)
                menu.addAction(copy_action)
                
            # 编辑和删除菜单项（不管在哪一列）
            menu.addSeparator()
            
            # 添加行功能 - 只在单行选择或无选择时显示
            if row >= 0 and selected_count <= 1:  # 确保在有效行上点击了右键，且最多只选中了一行
                logger.info(f"准备添加'添加行'子菜单 (选中行数: {selected_count})")
                add_menu = menu.addMenu("添加行")
                
                # 在上方添加行
                add_above_action = QAction(QIcon(""), "在上方添加行", self.table)
                add_above_action.triggered.connect(lambda: self._add_row_with_logging(row, "上方"))
                add_menu.addAction(add_above_action)
                
                # 在下方添加行
                add_below_action = QAction(QIcon(""), "在下方添加行", self.table)
                add_below_action.triggered.connect(lambda: self._add_row_with_logging(row + 1, "下方"))
                add_menu.addAction(add_below_action)
                
                # 在末尾添加行
                add_last_action = QAction(QIcon(""), "在末尾添加行", self.table)
                add_last_action.triggered.connect(lambda: self._add_row_with_logging(self.table.rowCount(), "末尾"))
                add_menu.addAction(add_last_action)
                
                logger.info(f"已添加'添加行'子菜单，包含上方、下方和末尾三个选项")
                menu.addSeparator()
            
            # 编辑行功能 - 只在单行选择且有效行选择时显示
            if row >= 0 and selected_count == 1:
                edit_action = QAction(QIcon(""), "编辑行", self.table)
                edit_action.triggered.connect(lambda: self.edit_row(row))
                menu.addAction(edit_action)
                logger.info(f"已添加'编辑行'选项")
                
            # 删除行(们)
            if selected_count > 0:
                delete_text = "删除选中的行" if selected_count > 1 else "删除行"
                delete_action = QAction(QIcon(""), delete_text, self.table)
                delete_action.triggered.connect(lambda: self.delete_selected_rows(selected_rows))
                menu.addAction(delete_action)
            
            # 显示菜单
            menu.exec_(self.table.mapToGlobal(position))
    
    def _add_editing_row_proxy(self):
        """
        代理方法，将调用转发到add_editing_row方法
        """
        if hasattr(self, 'add_editing_row'):
            return self.add_editing_row()
        else:
            logger.error("实例没有add_editing_row方法")
            return -1
            
    def copy_selected_content(self):
        """
        复制选中的内容到剪贴板
        """
        selected_items = self.table.selectedItems()
        if not selected_items:
            return False
            
        # 获取所有选中的单元格内容，按行列顺序组织
        rows = {}
        cols = set()
        
        # 首先收集所有选中的行和列
        for item in selected_items:
            row_idx = item.row()
            col_idx = item.column()
            if row_idx not in rows:
                rows[row_idx] = {}
            rows[row_idx][col_idx] = item.text()
            cols.add(col_idx)
        
        # 构建要复制的文本，按表格格式组织
        text_lines = []
        for row_idx in sorted(rows.keys()):
            row_data = rows[row_idx]
            line = []
            # 遍历所有选中的列
            for col_idx in sorted(cols):
                # 如果该单元格被选中，添加其内容，否则添加空字符串
                if col_idx in row_data:
                    line.append(row_data[col_idx])
                else:
                    line.append("")
            text_lines.append("\t".join(line))
        
        # 将行组合成完整文本
        text = "\n".join(text_lines)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        logger.info(f"已复制{len(selected_items)}个单元格内容到剪贴板（表格格式）")
        return True
    
    def _add_row_with_logging(self, position: int, position_type: str):
        """
        带日志的添加行操作
        
        Args:
            position (int): 添加行的位置
            position_type (str): 位置类型描述（"上方"/"下方"/"末尾"）
        """
        logger.info(f"尝试在行{position + 1}（{position_type}）添加新行 [添加方式: {position_type}]")
        try:
            # 调用原有的添加行方法
            new_row = self.add_row_at(position)
            
            # 检查返回值，注意处理可能的None值
            if new_row is not None and new_row >= 0:
                logger.info(f"成功在行{position + 1}（{position_type}）添加新行，新行索引: {new_row + 1} [添加方式: {position_type}]")
            else:
                logger.error(f"在行{position + 1}（{position_type}）添加新行失败，返回值: {new_row} [添加方式: {position_type}]")
        except Exception as e:
            logger.error(f"在行{position + 1}（{position_type}）添加新行时出错: {str(e)} [添加方式: {position_type}]")
            # 确保表格处于正常状态
            if hasattr(self, 'editing_row') and self.editing_row >= 0:
                try:
                    # 取消任何可能的编辑状态
                    self.cancel_editing()
                except:
                    # 如果清理失败，至少重置编辑状态属性
                    self.editing_row = -1
                    if hasattr(self, 'original_row_data'):
                        self.original_row_data = None

    def _setup_field_guides(self, row: int):
        """
        设置字段指导
        
        为表格字段添加指导和帮助信息
        
        Args:
            row (int): 行索引
        """
        # 新版引导功能已移除对单独表格字段的引导
        # 所有引导功能现在通过浮层式步骤引导提供
        pass
        
    def _handle_field_custom_context_menu(self, position, field_name, field_index, parent=None):
        """
        处理字段的自定义上下文菜单
        
        Args:
            position: 菜单显示位置
            field_name (str): 字段名称
            field_index (int): 字段索引
            parent: 父窗口
        """
        if not hasattr(self, 'table') or self.table is None:
            logger.error("表格对象不存在，无法处理字段上下文菜单")
            return
            
        # 当前行
        row = self.table.currentRow()
        
        if row < 0:
            logger.warning("未选择行，无法处理字段上下文菜单")
            return
        
        # 获取所选单元格
        cell_value = ""
        item = self.table.item(row, field_index)
        if item:
            cell_value = item.text().strip()
        
        # 根据不同字段类型，显示不同的菜单
        if field_name == "密码":
            self._handle_password_context_menu(position, row, field_index, cell_value, parent)
        elif field_name == "IP地址":
            self._handle_ip_address_context_menu(position, row, field_index, cell_value, parent)
        else:
            # 默认菜单处理
            self._handle_general_context_menu(position, row, field_index, cell_value, parent)
            
    def _handle_password_context_menu(self, position, row, col, cell_value, parent=None):
        """
        处理密码字段的上下文菜单
        
        Args:
            position: 菜单显示位置
            row (int): 行索引
            col (int): 列索引
            cell_value (str): 单元格值
            parent: 父窗口
        """
        # 创建上下文菜单
        context_menu = QMenu()
        
        # 添加菜单项
        # 复制密码
        copy_action = QAction("复制密码", self.table)
        copy_action.triggered.connect(lambda: self._copy_cell_to_clipboard(row, col))
        context_menu.addAction(copy_action)
        
        # 生成随机密码
        generate_action = QAction("生成16位随机密码", self.table)
        generate_action.triggered.connect(lambda: self._generate_random_password(row, col))
        context_menu.addAction(generate_action)
        
        # 生成16位随机密码并更新到服务器(SSH)
        if hasattr(self, 'table') and self.table.item(row, PASSWORD_COLUMNS.index("IP地址")):
            ip_address = self.table.item(row, PASSWORD_COLUMNS.index("IP地址")).text().strip()
            if ip_address:
                update_ssh_action = QAction("生成16位随机密码并更新到服务器(SSH)", self.table)
                update_ssh_action.triggered.connect(lambda: self._generate_and_update_ssh_password(row, col))
                context_menu.addAction(update_ssh_action)
        
        # 添加密码强度校验功能
        if cell_value:
            context_menu.addSeparator()
            strength_action = QAction("检查密码强度", self.table)
            strength_action.triggered.connect(lambda: self._check_password_strength(cell_value, parent))
            context_menu.addAction(strength_action)
        
        # 显示菜单
        context_menu.exec_(self.table.viewport().mapToGlobal(position))
        
        # 不再显示旧的引导对话框
        # 主界面引导中已经包含了整体功能的说明
    
    def _handle_ip_address_context_menu(self, position, row, col, cell_value, parent=None):
        """
        处理IP地址字段的上下文菜单
        
        Args:
            position: 菜单显示位置
            row (int): 行索引
            col (int): 列索引
            cell_value (str): 单元格值
            parent: 父窗口
        """
        # 创建上下文菜单
        context_menu = QMenu()
        
        # 添加菜单项
        # 复制IP地址
        copy_action = QAction("复制IP地址", self.table)
        copy_action.triggered.connect(lambda: self._copy_cell_to_clipboard(row, col))
        context_menu.addAction(copy_action)
        
        # 尝试SSH连接
        if cell_value:
            ssh_action = QAction("SSH连接", self.table)
            ssh_action.triggered.connect(lambda: self._ssh_connect(row, col))
            context_menu.addAction(ssh_action)
            
            # Ping IP地址
            ping_action = QAction("Ping测试", self.table)
            ping_action.triggered.connect(lambda: self._ping_ip_address(cell_value))
            context_menu.addAction(ping_action)
            
            # 更多网络工具
            network_menu = QMenu("网络工具", context_menu)
            
            # 添加网络工具子菜单项
            tracert_action = QAction("路由跟踪", self.table)
            tracert_action.triggered.connect(lambda: self._tracert_ip_address(cell_value))
            network_menu.addAction(tracert_action)
            
            whois_action = QAction("Whois查询", self.table)
            whois_action.triggered.connect(lambda: self._whois_ip_address(cell_value))
            network_menu.addAction(whois_action)
            
            context_menu.addMenu(network_menu)
        
        # 显示菜单
        context_menu.exec_(self.table.viewport().mapToGlobal(position))
        
        # 不再显示旧的引导对话框
        # 主界面引导中已经包含了整体功能的说明

class TableEventFilter(QObject):
    """
    表格事件过滤器
    
    处理表格的键盘和鼠标事件
    """
    
    def __init__(self, table_widget, password_table):
        """
        初始化事件过滤器
        
        Args:
            table_widget (QTableWidget): 表格控件
            password_table (PasswordTable): 密码表格管理器
        """
        super().__init__()
        self.table = table_widget
        self.password_table = password_table
        
    def eventFilter(self, obj, event):
        """
        事件过滤器
        
        Args:
            obj: 事件对象
            event: 事件
            
        Returns:
            bool: 是否处理了事件
        """
        # 处理双击事件 - 已禁用编辑功能
        if event.type() == QEvent.MouseButtonDblClick:
            # 不再触发编辑功能
            return True
            
        # 处理键盘事件
        if event.type() == QEvent.KeyPress:
            # 处理Ctrl+C复制
            if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
                # 获取选中的内容
                selected_items = self.table.selectedItems()
                if not selected_items:
                    return False
                
                # 获取所有选中的单元格内容，按行列顺序组织
                rows = {}
                cols = set()
                
                # 首先收集所有选中的行和列
                for item in selected_items:
                    row_idx = item.row()
                    col_idx = item.column()
                    if row_idx not in rows:
                        rows[row_idx] = {}
                    rows[row_idx][col_idx] = item.text()
                    cols.add(col_idx)
                
                # 构建要复制的文本，按表格格式组织
                text_lines = []
                for row_idx in sorted(rows.keys()):
                    row_data = rows[row_idx]
                    line = []
                    # 遍历所有选中的列
                    for col_idx in sorted(cols):
                        # 如果该单元格被选中，添加其内容，否则添加空字符串
                        if col_idx in row_data:
                            line.append(row_data[col_idx])
                        else:
                            line.append("")
                    text_lines.append("\t".join(line))
                
                # 将行组合成完整文本
                text = "\n".join(text_lines)
                
                # 复制到剪贴板
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                
                logger.info(f"已复制{len(selected_items)}个单元格内容到剪贴板（表格格式）")
                return True
                
            # 处理Ctrl+A全选
            if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_A:
                # 执行表格全选
                self.table.selectAll()
                logger.debug("已执行表格全选操作")
                return True
        
        # 处理单元格编辑事件 - 检测并触发相应的引导
        if event.type() == QEvent.FocusIn:
            # 只有当表格处于编辑状态时才进行检查
            if hasattr(self.password_table, 'editing_row') and self.password_table.editing_row >= 0:
                # 获取当前选中的单元格
                current_item = self.table.currentItem()
                if current_item:
                    row = current_item.row()
                    col = current_item.column()
                    
                    # 根据列类型触发相应的引导
                    if col == 4:  # 密码列
                        # 获取主窗口作为引导对话框的父窗口
                        if hasattr(self.table, 'parent'):
                            parent = self.table.parent()
                            if parent:
                                # 不再调用旧的引导功能
                                logger.info(f"密码字段编辑 - 行: {row+1}")
                    
                    elif col == 2:  # IP地址列
                        # 获取主窗口作为引导对话框的父窗口
                        if hasattr(self.table, 'parent'):
                            parent = self.table.parent()
                            if parent:
                                # 不再调用旧的引导功能
                                logger.info(f"IP地址字段编辑 - 行: {row+1}")
        
        # 其他事件交给默认处理
        return super().eventFilter(obj, event) 