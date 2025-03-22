#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理表格编辑模块
处理密码表格的添加、编辑和删除功能
"""

import logging
from typing import List, Tuple, Optional, Dict, Any

from PyQt5.QtWidgets import (
    QTableWidgetItem, QPushButton, QHBoxLayout, 
    QWidget, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush

from config import PASSWORD_COLUMNS, REQUIRED_FIELDS
from password import password_manager
from user import user_manager
from ui.password_manager.ui_utils import (
    create_table_item, get_row_data, validate_password_entry, 
    highlight_required_fields, confirm_delete,
    show_message, show_confirmation
)
from ui.password_manager.ui_guide import show_guide_if_needed

# 配置日志
logger = logging.getLogger(__name__)


class TableEditMixin:
    """
    表格编辑管理混入类
    
    提供编辑和修改表格数据的方法
    """
    
    def add_editing_row(self) -> int:
        """
        添加一行并进入编辑模式
        
        Returns:
            int: 新行的索引
        """
        self.add_row()
        new_row = self.table.rowCount() - 1
        return self.edit_row(new_row)
        
    def edit_row(self, row: int) -> bool:
        """
        进入行编辑模式
        
        Args:
            row (int): 要编辑的行索引
            
        Returns:
            bool: 如果成功进入编辑模式返回True，否则返回False
        """
        if self.editing_row != -1:
            # 如果已经有正在编辑的行，取消编辑
            self.cancel_editing()
            
        self.editing_row = row
        
        # 通知委托进入编辑模式
        if hasattr(self, 'required_field_delegate'):
            self.required_field_delegate.set_editing_mode(True, row)
        
        # 记录行数据的原始副本用于取消操作
        self.original_row_data = get_row_data(self.table, row)
        
        # 设置行为可编辑状态
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            else:
                # 如果单元格项不存在，创建一个空的可编辑项
                empty_item = QTableWidgetItem("")
                empty_item.setFlags(empty_item.flags() | Qt.ItemIsEditable)
                self.table.setItem(row, col, empty_item)
        
        # 高亮显示必填字段
        highlight_required_fields(self.table, row)
        
        # 添加确认和取消按钮
        self._add_confirm_cancel_buttons(row)
        
        # 设置数据验证
        self._setup_data_validation(row)
        
        # 设置字段指导
        self._setup_field_guides(row)
        
        # 让表格有接收键盘焦点的能力
        self.table.setFocusPolicy(Qt.StrongFocus)
        self.table.setFocus()
        
        # 设置操作按钮
        self._setup_edit_buttons(row)
        
        # 使用单元格选择模式，允许用户选择任意单元格进行编辑
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        
        # 设置第一个必填字段为当前单元格，但同时确保用户知道所有字段都可编辑
        if REQUIRED_FIELDS and len(REQUIRED_FIELDS) > 0:
            first_required = REQUIRED_FIELDS[0]
            self.table.setCurrentCell(row, first_required)
            self.table.editItem(self.table.item(row, first_required))
        
        # 显示状态信息，提示用户可以编辑所有字段
        statusBar = self._find_status_bar()
        if statusBar:
            statusBar.showMessage('编辑模式：点击任意单元格进行编辑，完成后点击"确认"按钮保存', 5000)
        
        # 确保表格支持多种编辑触发方式
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        
        return True
        
    def _add_confirm_cancel_buttons(self, row: int):
        """
        添加确认和取消按钮到指定行的下一行
        
        Args:
            row (int): 要添加按钮的行索引
        """
        # 判断是否需要添加新行（当编辑最后一行时）
        is_last_row = (row == self.table.rowCount() - 1)
        
        # 确定按钮所在行
        button_row = row + 1
        
        # 如果是最后一行，需要添加一个新行
        if is_last_row:
            self.table.insertRow(button_row)
            # 设置行号为从1开始
            self.table.setVerticalHeaderItem(button_row, QTableWidgetItem(str(button_row + 1)))
            # 创建空白占位单元格
            for col in range(self.table.columnCount()):
                self.table.setItem(button_row, col, QTableWidgetItem(""))
        
        # 记录按钮所在行和是否新添加的标志，方便后续处理
        self.button_row = button_row
        self.is_button_row_new = is_last_row
        
        # 保存按钮行原来最右侧的单元格，以便后续恢复
        last_col = self.table.columnCount() - 1
        if self.table.item(button_row, last_col):
            self.original_cell_text = self.table.item(button_row, last_col).text()
        else:
            self.original_cell_text = ""
        
        # 创建按钮容器，使用最小的布局边距
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(1, 1, 1, 1)
        button_layout.setSpacing(6)  # 增加按钮间距
        
        # 确认按钮
        confirm_button = QPushButton("确认")
        confirm_button.setFixedHeight(23)  # 调整高度，宽度根据文字自适应
        confirm_button.setToolTip("确认修改")
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; 
                color: white; 
                border-radius: 4px; 
                font-weight: bold;
                font-size: 12px;
                padding: 1px 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #398e3c;
            }
        """)
        confirm_button.clicked.connect(lambda: self.confirm_editing(row))
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setFixedHeight(23)  # 调整高度，宽度根据文字自适应
        cancel_button.setToolTip("取消修改")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336; 
                color: white; 
                border-radius: 4px; 
                font-weight: bold;
                font-size: 12px;
                padding: 1px 8px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
        """)
        cancel_button.clicked.connect(self.cancel_editing)
        
        # 添加按钮到布局
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        
        # 设置单元格小部件到按钮行的最右侧单元格
        self.table.setCellWidget(button_row, last_col, button_widget)
        
        # 如果是新添加的行，设置行高较小
        if is_last_row:
            self.table.setRowHeight(button_row, 35)  # 增加行高以适应文字按钮
        
    def confirm_editing(self, row: int) -> bool:
        """
        确认编辑，保存更改
        
        Args:
            row (int): 要确认的行索引
            
        Returns:
            bool: 如果成功确认编辑返回True，否则返回False
        """
        # 先检查必填字段是否已填写
        if not validate_password_entry(self.table, row):
            return False
            
        new_data = get_row_data(self.table, row)
        
        # 区分添加模式和编辑模式
        if self.original_row_data and any(self.original_row_data):
            # 编辑现有条目
            # 查找真实的行索引（考虑搜索模式）
            real_index = self._get_real_row_index(row)
            
            if real_index is not None:
                success, message = password_manager.update_password(
                    self.current_owner, real_index, new_data
                )
            else:
                success, message = False, "无法确定要更新的记录索引"
                
            action_desc = "编辑"
        else:
            # 添加新条目
            success, message = password_manager.add_password(self.current_owner, new_data)
            action_desc = "添加"
        
        if success:
            # 取消编辑模式
            self._remove_confirm_cancel_buttons(row)
            self._clear_highlight(row)
            
            # 设置单元格为不可编辑状态
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            
            # 重置编辑行状态
            self.editing_row = -1
            self.original_row_data = None
            
            # 通知委托退出编辑模式
            if hasattr(self, 'required_field_delegate'):
                self.required_field_delegate.set_editing_mode(False)
            
            # 重置表格选择模式
            self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
            
            # 重新加载数据
            self._refresh_data()
            
            # 显示成功消息
            statusBar = self._find_status_bar()
            if statusBar:
                statusBar.showMessage(f"密码记录{action_desc}成功", 5000)
                
            return True
        else:
            # 显示错误消息
            QMessageBox.warning(
                self.table.parent(), 
                f"密码记录{action_desc}失败", 
                message, 
                QMessageBox.Ok
            )
            return False
        
    def _clear_highlight(self, row: int):
        """
        清除行高亮
        
        Args:
            row (int): 行索引
        """
        if row < 0 or row >= self.table.rowCount():
            return
            
        # 批量处理前禁用UI更新以提高性能
        self.table.setUpdatesEnabled(False)
        
        # 清除高亮背景色
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush())
                # 恢复不可编辑状态
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                
        # 恢复原始行高
        self.table.setRowHeight(row, self.table.verticalHeader().defaultSectionSize())
        
        # 重新启用UI更新
        self.table.setUpdatesEnabled(True)
        
    def _remove_confirm_cancel_buttons(self, row: int):
        """
        移除确认和取消按钮
        
        Args:
            row (int): 按钮对应的编辑行索引
        """
        # 处理按钮行
        if hasattr(self, 'button_row') and self.button_row < self.table.rowCount():
            # 如果按钮行是新添加的，则删除它
            if hasattr(self, 'is_button_row_new') and self.is_button_row_new:
                self.table.removeRow(self.button_row)
                logger.debug(f"删除按钮行: {self.button_row+1}")
            else:
                # 如果使用的是现有行，则恢复最后一个单元格的内容
                last_col = self.table.columnCount() - 1
                if hasattr(self, 'original_cell_text'):
                    self.table.removeCellWidget(self.button_row, last_col)
                    self.table.setItem(self.button_row, last_col, QTableWidgetItem(self.original_cell_text))
                    logger.debug(f"恢复按钮行单元格内容: 行{self.button_row+1}, 列{last_col+1}")
            
            # 清除按钮行相关属性
            delattr(self, 'button_row')
            if hasattr(self, 'is_button_row_new'):
                delattr(self, 'is_button_row_new')
            if hasattr(self, 'original_cell_text'):
                delattr(self, 'original_cell_text')
        
    def cancel_editing(self):
        """
        取消编辑，恢复原始数据
        """
        if self.editing_row == -1:
            return
            
        row = self.editing_row
        logger.info(f"取消编辑 - 第{row}行: {self.table.item(row, 0).text() if self.table.item(row, 0) else '新行'}")
        
        # 如果是新添加的行（没有原始数据或原始数据为空），删除该行
        if not self.original_row_data or not any(self.original_row_data):
            self.table.removeRow(row)
        else:
            # 恢复原始数据
            for col, text in enumerate(self.original_row_data):
                if col < self.table.columnCount():
                    item = self.table.item(row, col)
                    if item:
                        item.setText(text)
                    else:
                        self.table.setItem(row, col, QTableWidgetItem(text))
                        
            # 清除高亮
            self._clear_highlight(row)
            
            # 设置单元格为不可编辑状态
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    
            # 移除操作按钮
            self._remove_confirm_cancel_buttons(row)
        
        # 重置编辑行状态
        self.editing_row = -1
        self.original_row_data = None
        
        # 通知委托退出编辑模式
        if hasattr(self, 'required_field_delegate'):
            self.required_field_delegate.set_editing_mode(False)
        
        # 重置表格选择模式
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        logger.info("取消编辑完成，已恢复原始数据")
        
        # 显示状态消息
        statusBar = self._find_status_bar()
        if statusBar:
            statusBar.showMessage("已取消编辑", 3000)
        
    def delete_row(self, row: int) -> bool:
        """
        删除指定行
        
        Args:
            row (int): 要删除的行索引
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        if row < 0 or row >= self.table.rowCount():
            return False
            
        # 如果正在编辑，先取消编辑
        if self.editing_row >= 0:
            self.cancel_editing()
            
        try:
            # 如果是搜索模式，获取真实行索引
            if self.search_mode:
                real_row = self._get_real_row_index(row)
                if real_row is None:
                    logger.error("无法获取真实行索引")
                    return False
            else:
                real_row = row
                
            # 执行删除操作
            success, message = password_manager.delete_password(self.current_owner, real_row)
            
            if not success:
                logger.error(f"删除密码失败: {message}")
                return False
                
            # 重新加载数据
            if self.search_mode:
                # 更新搜索结果，移除已删除的项
                if row < len(self.search_results):
                    self.search_results.pop(row)
                self._refresh_search_results()
            else:
                # 否则重新加载所有密码
                self._load_passwords_internal(self.current_owner)
                
            return True
        except Exception as e:
            logger.error(f"删除行时出错: {str(e)}")
            return False
            
    def delete_selected_rows(self, rows: List[int]) -> bool:
        """
        删除多个选中的行
        
        Args:
            rows (List[int]): 要删除的行索引列表
            
        Returns:
            bool: 全部删除成功返回True，否则返回False
        """
        if not rows:
            return False
            
        # 如果正在编辑，先取消编辑
        if self.editing_row >= 0:
            self.cancel_editing()
            
        try:
            # 删除前确认
            if not confirm_delete(self.table.parent()):
                return False
                
            # 转换为真实行索引
            real_rows = []
            if self.search_mode:
                for row in sorted(rows):
                    real_row = self._get_real_row_index(row)
                    if real_row is not None:
                        real_rows.append((row, real_row))
            else:
                real_rows = [(row, row) for row in sorted(rows)]
                
            # 检查转换结果
            if not real_rows:
                logger.error("无法获取真实行索引")
                return False
                
            # 从后向前删除，以避免索引变化的问题
            real_rows.reverse()
            
            for displayed_row, real_row in real_rows:
                success, message = password_manager.delete_password(self.current_owner, real_row)
                if not success:
                    logger.error(f"删除密码失败: {message}")
                    return False
                    
                # 如果在搜索模式下，更新搜索结果
                if self.search_mode and displayed_row < len(self.search_results):
                    self.search_results.pop(displayed_row)
                    
            # 重新加载数据
            if self.search_mode:
                self._refresh_search_results()
            else:
                self._load_passwords_internal(self.current_owner)
                
            return True
        except Exception as e:
            logger.error(f"删除多行时出错: {str(e)}")
            return False
            
    def add_row_at(self, position: int = None) -> None:
        """
        在指定位置添加新行

        Args:
            position (int, optional): 插入位置. Defaults to None.
        """
        try:
            # 如果未指定位置或位置超出范围，则在表格末尾添加
            if position is None or position < 0:
                position = self.table.rowCount()
            elif position > self.table.rowCount():
                position = self.table.rowCount()

            logger.info(f"在位置 {position} 添加新行")
            
            # 禁用排序以防止行位置改变
            old_sort_state = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            
            # 插入新行
            self.table.insertRow(position)
            
            # 新行获取焦点
            self.table.selectRow(position)
            self.edit_row(position)
            
            # 行索引指向新行
            self.editing_row = position
            # 标记为新行
            self.is_new_row = True
            # 保存插入位置，用于加载时恢复
            self.insert_position = position
            
            # 恢复排序状态
            self.table.setSortingEnabled(old_sort_state)
        except Exception as e:
            logger.exception(f"添加行失败: {str(e)}")
    
    def _setup_data_validation(self, row: int):
        """
        为新增行添加数据验证
        
        Args:
            row (int): 行索引
        """
        # 高亮显示必填字段
        highlight_required_fields(self.table, row)
        
        # 设置单元格变化监听，保持必填字段的高亮状态
        self.table.itemChanged.connect(self._refresh_required_field_highlight)
        
        # 添加字段编辑监听，用于触发相应的引导
        if hasattr(self, '_setup_field_guides'):
            self._setup_field_guides(row)
    
    def _refresh_required_field_highlight(self, item):
        """
        刷新必填字段高亮
        
        当单元格内容变化时，确保必填字段保持高亮状态
        
        Args:
            item (QTableWidgetItem): 变化的单元格项
        """
        # 如果不在编辑状态，忽略
        if self.editing_row < 0:
            return
            
        # 仅处理编辑行的单元格变化
        if item.row() != self.editing_row:
            return
            
        # 仅对必填字段进行处理
        if item.column() in REQUIRED_FIELDS:
            # 如果单元格内容为空，设置占位符标记
            if not item.text().strip():
                item.setData(Qt.UserRole, "placeholder")
            else:
                # 如果有内容，清除占位符标记
                item.setData(Qt.UserRole, None)
            
            # 刷新表格，让委托重新渲染单元格
            self.table.viewport().update()
            
            # 在状态栏提示用户必填项
            try:
                field_name = PASSWORD_COLUMNS[item.column()]
                if not item.text().strip():
                    status_msg = f"请填写必填项: {field_name}"
                    if hasattr(self.table, 'window') and hasattr(self.table.window(), 'statusBar'):
                        self.table.window().statusBar().showMessage(status_msg, 3000)
            except:
                # 忽略任何出错
                pass

    def _setup_field_guides(self, row: int):
        """
        设置字段编辑引导
        
        当用户编辑特定字段时，显示相应的引导
        
        Args:
            row (int): 行索引
        """
        # 首先显示首次编辑引导
        show_guide_if_needed("first_edit", self.table.window())
        
        # 监听密码和IP地址字段的编辑
        # 要实现这个功能，我们需要在单元格激活时检查它的列
        # 这部分在itemActivated信号中处理
        
        # 连接单元格变化信号
        self.table.itemDoubleClicked.connect(
            lambda item: self._show_field_guide_for_item(item)
        )
    
    def _show_field_guide_for_item(self, item):
        """
        根据单元格类型显示相应的引导
        
        Args:
            item (QTableWidgetItem): 表格单元格项
        """
        if not item:
            return
            
        # 如果不是在编辑状态，忽略
        if self.editing_row < 0:
            return
            
        column = item.column()
        
        # 密码字段 (列索引4)
        if column == 4:
            show_guide_if_needed("password_field", self.table.window())
            
        # IP地址字段 (列索引2)
        elif column == 2:
            show_guide_if_needed("ip_field", self.table.window())
    
    def check_ssh_password_updates(self) -> bool:
        """
        检查SSH密码更新
        
        Returns:
            bool: 是否更新成功
        """
        # 实现检查SSH密码更新的逻辑
        # 这可能需要根据您的具体实现来决定
        return True
    
    def _get_real_row_index(self, row: int) -> Optional[int]:
        """
        获取真实行索引
        
        Args:
            row (int): 显示行索引
            
        Returns:
            Optional[int]: 真实行索引或None
        """
        # 实现逻辑以获取真实行索引
        # 在搜索模式下需要从search_results中获取
        if self.search_mode and hasattr(self, 'search_results') and self.search_results:
            if 0 <= row < len(self.search_results):
                return self.search_results[row][0]  # 假设search_results存储格式为[(real_index, data), ...]
        return row
    
    def _load_passwords_internal(self, owner: str, preserve_position: bool = False, insert_position: Optional[int] = None):
        """
        内部加载密码
        
        Args:
            owner (str): 所有者
            preserve_position (bool): 是否保留位置
            insert_position (Optional[int]): 插入位置
        """
        # 实现加载密码的逻辑
        # 这可能需要根据您的具体实现来决定
        pass
    
    def _refresh_search_results(self):
        """
        刷新搜索结果
        """
        # 实现刷新搜索结果的逻辑
        # 这可能需要根据您的具体实现来决定
        pass
    
    def _setup_edit_buttons(self, row: int):
        """
        设置编辑行的操作按钮
        
        Args:
            row (int): 要编辑的行索引
        """
        # 目前此方法仅作为占位符，以避免AttributeError
        # 如果需要添加额外的编辑功能按钮，可以在此实现
        logger.debug(f"设置行 {row} 的编辑按钮")
        # 可能的实现：添加额外的工具按钮，例如密码生成器按钮等
        pass
    
    def _find_status_bar(self):
        """
        查找状态栏对象
        
        Returns:
            QStatusBar: 状态栏对象，或None（如果找不到）
        """
        try:
            parent = self.table.parent()
            while parent:
                if hasattr(parent, 'statusBar'):
                    return parent.statusBar()
                parent = parent.parent()
            return None
        except Exception as e:
            logger.error(f"查找状态栏时出错: {str(e)}")
            return None
    
    def _refresh_data(self):
        """
        刷新表格数据
        
        根据当前模式（搜索模式或普通模式）重新加载数据
        """
        if self.search_mode:
            self._refresh_search_results()
        else:
            self._load_passwords_internal(self.current_owner)

    def add_row(self):
        """
        在表格末尾添加一个空行
        """
        # 获取当前表格行数
        row_count = self.table.rowCount()
        
        # 插入新行
        self.table.insertRow(row_count)
        
        # 设置空单元格
        for col in range(self.table.columnCount()):
            self.table.setItem(row_count, col, QTableWidgetItem(""))
        
        return row_count 