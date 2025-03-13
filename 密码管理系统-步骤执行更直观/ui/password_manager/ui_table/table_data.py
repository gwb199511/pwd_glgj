#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理表格数据模块
处理密码数据的加载、刷新等功能
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt

from password import password_manager
from ui.password_manager.ui_utils import create_table_item

# 配置日志
logger = logging.getLogger(__name__)


class TableDataMixin:
    """
    表格数据管理混入类
    
    提供加载和管理表格数据的方法
    """
    
    def load_passwords(self, owner: str) -> bool:
        """
        加载指定所有者的密码
        
        Args:
            owner (str): 所有者名称
            
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            # 保存当前所有者
            self.current_owner = owner
            
            # 清除搜索结果
            self.search_results = None
            self.search_mode = False
            
            # 加载密码
            return self._load_passwords_internal(owner)
        except Exception as e:
            logger.error(f"加载密码时出错: {str(e)}")
            return False
            
    def _load_passwords_internal(self, owner: str, preserve_position: bool = False, insert_position: Optional[int] = None) -> bool:
        """
        内部密码加载方法
        
        Args:
            owner (str): 所有者名称
            preserve_position (bool, optional): 是否保持插入位置。默认为False。
            insert_position (int, optional): 插入的位置索引。仅在preserve_position为True时有效。
            
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            # 获取密码列表
            passwords = password_manager.get_passwords_by_owner(owner)
            
            # 禁用排序，以避免在加载数据时排序
            self.table.setSortingEnabled(False)
            
            # 清空表格
            self.table.setRowCount(0)
            
            # 填充表格
            for row, password in enumerate(passwords):
                self.table.insertRow(row)
                
                # 设置行号为从1开始
                self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(row + 1)))
                
                # 填充每一列
                for col, value in enumerate(password):
                    if col < self.table.columnCount():
                        self.table.setItem(row, col, create_table_item(value))
                        
            # 重新启用排序
            self.table.setSortingEnabled(True)
            
            # 清除编辑状态
            self.editing_row = -1
            
            return True
        except Exception as e:
            logger.error(f"加载密码时出错: {str(e)}")
            return False
            
    def get_selected_row(self) -> int:
        """
        获取当前选中的行
        
        Returns:
            int: 选中的行索引，如果没有选中则返回-1
        """
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return -1
        return rows[0].row()
            
    def _get_real_row_index(self, displayed_row: int) -> Optional[int]:
        """
        获取搜索结果中显示行对应的真实行索引
        
        Args:
            displayed_row (int): 显示的行索引
            
        Returns:
            Optional[int]: 真实的行索引，如果找不到则返回None
        """
        if not self.search_results or displayed_row < 0 or displayed_row >= len(self.search_results):
            return None
            
        # 获取搜索结果中的所有者和密码记录
        owner, password = self.search_results[displayed_row]
        
        # 如果所有者不是当前所有者，无法获取真实索引
        if owner != self.current_owner:
            return None
            
        # 获取所有者的所有密码
        all_passwords = password_manager.get_passwords_by_owner(owner)
        
        # 查找匹配的记录
        for i, p in enumerate(all_passwords):
            # 比较除密码字段之外的所有字段（密码字段可能已解密，无法直接比较）
            match = True
            for j in range(len(p)):
                if j != 4 and j < len(password) and str(p[j]) != str(password[j]):
                    match = False
                    break
                    
            if match:
                return i
                
        return None 