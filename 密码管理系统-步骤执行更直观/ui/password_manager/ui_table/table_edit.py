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

from config import PASSWORD_COLUMNS
from password import password_manager
from user import user_manager
from ui.password_manager.ui_utils import (
    create_table_item, get_row_data, validate_password_entry, 
    highlight_required_fields, confirm_delete,
    show_message, show_confirmation
)

# 配置日志
logger = logging.getLogger(__name__)


class TableEditMixin:
    """
    表格编辑管理混入类
    
    提供编辑和修改表格数据的方法
    """
    
    def add_editing_row(self) -> int:
        """
        在表格最后添加一个新的编辑行
        
        Returns:
            int: 新添加行的索引
        """
        try:
            # 获取当前表格行数
            row_count = self.table.rowCount()
            logger.info(f"当前表格总行数: {row_count}")
            
            # 判断最后一行是否是按钮行
            has_button_row = (row_count > 0 and self.table.cellWidget(row_count - 1, 0) is not None)
            if has_button_row:
                logger.info("检测到表格底部有按钮行")
            
            # 计算实际插入行的位置
            insert_row = row_count - 1 if has_button_row else row_count
            logger.info(f"将在位置 {insert_row} 插入新行")
            
            # 插入新行
            self.table.insertRow(insert_row)
            
            # 设置项目单元格为可编辑
            for col in range(self.table.columnCount()):
                item = QTableWidgetItem("")
                if col == 0:
                    # 在第一个单元格中设置标记，表示这是新添加的行
                    item.setData(Qt.UserRole + 200, True)
                    logger.info(f"在第{insert_row+1}行第1列设置了新行标记")
                self.table.setItem(insert_row, col, item)
            
            # 设置编辑状态
            self.editing_row = insert_row
            
            # 添加确认和取消按钮
            self._add_confirm_cancel_buttons(insert_row)
            
            # 添加数据验证
            self._setup_data_validation(insert_row)
            
            # 设置焦点到第一个单元格
            if self.table.item(insert_row, 0):
                self.table.setCurrentCell(insert_row, 0)
                self.table.editItem(self.table.item(insert_row, 0))
            
            # 添加到编辑行列表
            self.edited_rows.add(insert_row)
            logger.info(f"已将第{insert_row+1}行添加到编辑行列表")
            
            return insert_row
        except Exception as e:
            logger.error(f"添加编辑行时发生错误: {str(e)}")
            return -1
        
    def edit_row(self, row: int) -> bool:
        """
        开始编辑指定行
        
        Args:
            row (int): 行索引
            
        Returns:
            bool: 开始编辑成功返回True，否则返回False
        """
        if row < 0 or row >= self.table.rowCount():
            return False
            
        # 如果已经在编辑状态，先取消当前编辑
        if self.editing_row >= 0:
            self.cancel_editing()
            
        # 保存原始数据
        self.editing_row = row
        
        # 禁用排序，以避免在编辑时排序
        self.table.setSortingEnabled(False)
        
        # 暂时存储并清除表格样式表，以避免样式冲突
        original_style = self.table.styleSheet()
        self.table.setStyleSheet("")
        
        # 临时启用编辑功能 - 直接设置，不保存原始值
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked)
        
        # 批量处理前禁用UI更新以提高性能
        self.table.setUpdatesEnabled(False)
        
        # 使所有单元格可编辑并设置特殊的背景色
        highlight_color = QColor("#cce5ff")
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                # 保存原始数据以便取消时恢复
                item.setData(Qt.UserRole, item.text())
                # 设置为可编辑状态
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                # 设置高亮背景色
                item.setBackground(highlight_color)
                
        # 重新启用UI更新
        self.table.setUpdatesEnabled(True)
        
        # 恢复样式表
        self.table.setStyleSheet(original_style)
        
        # 添加确认和取消按钮
        self._add_confirm_cancel_buttons(row)
        
        # 设置行高更大一点以凸显
        self.table.setRowHeight(row, self.table.rowHeight(row) + 12)
        
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
        confirm_button = QPushButton("✓")
        confirm_button.setFixedSize(23, 23)  # 调整为更小的尺寸，与行高更协调
        confirm_button.setToolTip("确认修改")
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; 
                color: white; 
                border-radius: 12px; 
                font-weight: bold;
                font-size: 12px;
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
        cancel_button = QPushButton("✕")
        cancel_button.setFixedSize(23, 23)  # 调整为更小的尺寸，与行高更协调
        cancel_button.setToolTip("取消修改")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336; 
                color: white; 
                border-radius: 12px; 
                font-weight: bold;
                font-size: 10px;
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
            self.table.setRowHeight(button_row, 30)
        
    def confirm_editing(self, row: int) -> bool:
        """
        确认编辑指定行，保存数据
        
        Args:
            row (int): 行索引
            
        Returns:
            bool: 是否成功保存
        """
        # 获取行信息
        row_name = self.table.item(row, 0).text() if self.table.item(row, 0) else '新行'
        logger.info(f"开始确认编辑 - 第{row+1}行: {row_name}")
        
        # 检查是否修改了密码字段
        password_changed = False
        if hasattr(self, 'original_data') and row < len(self.original_data):
            original_row_data = self.original_data[row]
            current_row_data = get_row_data(self.table, row)
            # 检查密码列(通常是第5列，索引为4)是否发生变化
            if len(original_row_data) > 4 and len(current_row_data) > 4:
                password_changed = original_row_data[4] != current_row_data[4]
        
        # 如果修改了密码，则要求用户验证身份
        if password_changed:
            logger.info("检测到密码变更，需要进行身份验证")
            # 创建密码确认对话框
            from ui.password_manager.ui_dialogs import PasswordConfirmDialog
            password_dialog = PasswordConfirmDialog(self.table.parent())
            if password_dialog.exec_() != password_dialog.Accepted:
                logger.warning("用户取消了身份验证，编辑操作被取消")
                return False
            
            # 获取用户输入的密码
            current_password = password_dialog.get_password()
            
            # 验证用户密码
            login_success, _ = user_manager.login(self.current_owner, current_password)
            if not login_success:
                logger.warning(f"用户 {self.current_owner} 身份验证失败，编辑操作被取消")
                msg_box = QMessageBox()
                msg_box.setWindowTitle("验证失败")
                msg_box.setText("密码不正确，无法继续操作。")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                return False
            
            logger.info(f"用户 {self.current_owner} 身份验证成功，继续执行编辑操作")
        
        # 批量编辑模式下的确认处理
        if hasattr(self, 'batch_editing') and self.batch_editing:
            logger.info("批量编辑模式 - 一次性确认所有修改")
            return self._confirm_batch_editing(row)
            
        try:
            # 验证必填字段
            valid = validate_password_entry(self.table, row)
            if not valid:
                logger.warning(f"确认编辑失败 - 第{row+1}行: 必填字段未完成")
                return False
                
            # 移除高亮
            self._clear_highlight(row)
            
            # 获取行数据
            row_data = get_row_data(self.table, row)
            
            # 获取真实行索引
            real_row = self._get_real_row_index(row) if self.search_mode else row
            
            if real_row is None:
                logger.error(f"无法获取第{row+1}行的真实索引")
                msg_box = QMessageBox()
                msg_box.setWindowTitle("确认编辑")
                msg_box.setText(f"无法获取第{row+1}行的真实索引")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                return False
                
            # 判断是否是新添加的行
            is_new_row = False
            
            # 首先检查是否有存储在第一个单元格的数据标记
            if self.table.item(row, 0) and self.table.item(row, 0).data(Qt.UserRole + 200):
                is_new_row = True
                logger.info(f"根据存储的标记判断第{row+1}行是新添加的行")
            else:
                # 退回到位置判断（作为备用方法）
                is_new_row = (row == self.table.rowCount() - 2)  # 减2是因为有一个按钮行
                logger.info(f"根据位置判断第{row+1}行是否为新行: {is_new_row}")
            
            if is_new_row:
                logger.info("检测到新添加的行，将跳过SSH密码更新步骤")
            else:
                # 先进行SSH更新检查
                logger.info("检查是否有需要SSH更新的密码")
                ssh_update_result = self.check_ssh_password_updates()
                
                # 如果SSH更新失败，取消编辑并返回
                if ssh_update_result == False:
                    logger.warning("SSH密码更新失败，取消本地数据库更新")
                    return False
                    
            # 执行本地数据库更新操作
            if is_new_row:
                logger.info(f"检测到新添加的行，使用add_password方法直接添加")
                # 对于新行，直接调用add_password方法添加新记录
                success, message = password_manager.add_password(
                    self.current_owner, 
                    row_data,
                    position=row if is_new_row else None
                )
            else:
                # 对于现有行，执行正常更新
                success, message = password_manager.update_password(
                    self.current_owner, 
                    real_row, 
                    row_data
                )
            
            if not success:
                logger.error(f"保存第{row+1}行数据失败: {message}")
                msg_box = QMessageBox()
                msg_box.setWindowTitle("确认编辑")
                msg_box.setText(f"保存第{row+1}行数据失败: {message}")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                return False
                
            # 清除编辑状态
            self.editing_row = -1
            
            # 移除确认和取消按钮
            self._remove_confirm_cancel_buttons(row)
            
            # 重新加载数据以显示最新内容 - 对于新添加的行，记录插入位置
            insert_position = row if is_new_row else None
            
            if self.search_mode:
                self._refresh_search_results()
            else:
                self._load_passwords_internal(self.current_owner, preserve_position=is_new_row, insert_position=insert_position)
                
            # 处理链式编辑的下一行
            if hasattr(self, 'pending_edit_rows') and self.pending_edit_rows:
                next_row = self.pending_edit_rows.pop(0)
                logger.info(f"继续编辑下一行 - 行: {next_row+1}")
                self.edit_row(next_row)
                
                # 如果没有更多待编辑行，恢复原始确认函数
                if not self.pending_edit_rows and hasattr(self, 'original_confirm_editing'):
                    logger.info("所有行编辑完成，恢复原始确认函数")
                    self.confirm_editing = self.original_confirm_editing
                    delattr(self, 'original_confirm_editing')
                
            logger.info(f"成功确认编辑 - 第{row+1}行: {row_name}")
            return True
            
        except Exception as e:
            logger.error(f"确认编辑时出错: {str(e)}")
            return False
            
    def _confirm_batch_editing(self, current_row: int) -> bool:
        """
        批量编辑模式下的确认处理 (已简化，保留基本功能)
        
        Args:
            current_row (int): 当前编辑的行
            
        Returns:
            bool: 是否成功保存所有更改
        """
        logger.warning("批量编辑功能已被简化")
        # 显示消息提示用户使用单行编辑
        from PyQt5.QtWidgets import QMessageBox
        msg_box = QMessageBox()
        msg_box.setWindowTitle("批量编辑已简化")
        msg_box.setText("批量编辑功能已被简化，请使用单行编辑。")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
        msg_box.exec_()
        
        # 清除编辑状态
        self.cancel_editing()
        
        if hasattr(self, 'batch_editing'):
            self.batch_editing = False
        
        if hasattr(self, 'batch_edited_rows'):
            delattr(self, 'batch_edited_rows')
            
        if hasattr(self, 'original_passwords'):
            delattr(self, 'original_passwords')
        
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
        取消编辑，恢复到原始状态
        """
        logger.info(f"取消编辑 - 第{self.editing_row+1}行: {self.table.item(self.editing_row, 0).text() if self.table.item(self.editing_row, 0) else '新行'}")
            
        # 如果没有正在编辑的行，直接返回
        if self.editing_row < 0 or self.editing_row >= self.table.rowCount():
            logger.warning(f"取消编辑失败: 没有正在编辑的行或行索引 {self.editing_row} 超出范围")
            return
        
        # 批量处理前禁用UI更新以提高性能
        self.table.setUpdatesEnabled(False)
        
        # 获取当前编辑的行
        row = self.editing_row
            
        # 记录批量编辑模式下的取消
        if hasattr(self, 'batch_editing') and self.batch_editing:
            if hasattr(self, 'batch_edited_rows'):
                logger.info(f"取消批量编辑 - 共{len(self.batch_edited_rows)}行")
                
                # 记录操作的项目名称
                project_names = []
                for r in self.batch_edited_rows:
                    if self.table.item(r, 0):
                        project_names.append(self.table.item(r, 0).text())
                
                if project_names:
                    projects_str = "、".join(project_names[:3])
                    if len(project_names) > 3:
                        projects_str += f" 等{len(project_names)}个项目"
                    logger.info(f"取消批量编辑项目: {projects_str}")
        
        # 移除确认和取消按钮
        self._remove_confirm_cancel_buttons(row)
        
        # 如果是新添加的行且不在搜索模式，则删除该行
        if row == self.table.rowCount() - 1 and not self.search_mode:
            # 如果是编辑最后一行，可能是新添加的行，执行删除
            all_empty = True
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and item.text() and item.text() != "<双击添加>":
                    all_empty = False
                    break
                    
            # 如果所有单元格为空或只有占位符，则认为是新添加的行
            if all_empty:
                self.table.removeRow(row)
                logger.info(f"删除空行: {row+1}")
        else:
            # 如果是编辑现有行，则重新加载数据以恢复原始值
            if self.search_mode:
                self._refresh_search_results()
                logger.debug("搜索模式: 刷新搜索结果以恢复原始数据")
            else:
                self._load_passwords_internal(self.current_owner)
                logger.debug("重新加载数据以恢复原始值")
                
        # 清除批量编辑相关属性
        if hasattr(self, 'batch_editing'):
            self.batch_editing = False
        if hasattr(self, 'batch_edited_rows'):
            delattr(self, 'batch_edited_rows')
        if hasattr(self, 'original_passwords'):
            delattr(self, 'original_passwords')
                
        # 清除编辑状态
        self.editing_row = -1
        
        # 恢复表格的编辑触发器设置
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 重新启用UI更新
        self.table.setUpdatesEnabled(True)
        
        logger.info("取消编辑完成，已恢复原始数据")
        
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
        
    def confirm_editing(self, row: int = None) -> Tuple[bool, str]:
        """
        确认编辑

        Args:
            row (int, optional): 要编辑的行. Defaults to None.

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        # ... existing code ...
                
        # 如果添加/更新成功
        if success:
            # 新行
            if self.is_new_row:
                # 保存插入位置
                position = self.insert_position if hasattr(self, 'insert_position') else None
                
                # 添加到密码管理器
                success, message = self.password_manager.add_password(
                    self.current_user,
                    site_info,
                    position=position  # 传递插入位置
                )
            else:
                # 更新现有记录
                success, message = self.password_manager.update_password(
                    self.current_user,
                    self.original_site_info,
                    site_info
                )
        
        # ... existing code ...

        # ... existing code ... 