#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理表格搜索模块
处理密码表格的搜索和过滤功能
"""

import logging
from typing import List, Tuple, Optional

from PyQt5.QtWidgets import QTableWidgetItem

from core.password import password_manager
from ui.password_manager.ui_utils import create_table_item

# 配置日志
logger = logging.getLogger(__name__)


class TableSearchMixin:
    """
    表格搜索管理混入类
    
    提供搜索和过滤表格数据的方法
    """
    
    def search(self, keyword: str) -> bool:
        """
        搜索密码
        
        Args:
            keyword (str): 搜索关键词
            
        Returns:
            bool: 搜索成功返回True，否则返回False
        """
        if not keyword:
            # 如果关键词为空，清除搜索结果
            return self.clear_search()
            
        try:
            # 保存搜索关键字，用于后续刷新
            self.last_search_text = keyword
            logger.debug(f"设置搜索关键字: '{keyword}'")
            
            # 执行搜索
            results = password_manager.search_passwords(keyword, self.current_owner)
            
            if not results:
                # 没有找到结果，但搜索成功
                self.search_mode = True
                self.search_results = []
                self.table.setRowCount(0)
                return True
                
            # 保存搜索结果
            self.search_mode = True
            self.search_results = results
            
            # 禁用排序，以避免在加载数据时排序
            self.table.setSortingEnabled(False)
            
            # 清空表格
            self.table.setRowCount(0)
            
            # 填充表格
            for row, (owner, password) in enumerate(results):
                self.table.insertRow(row)
                
                # 设置行号为从1开始
                self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(row + 1)))
                
                # 填充所有者列（如果与当前所有者不同，添加所有者前缀）
                prefix = f"[{owner}] " if owner != self.current_owner else ""
                
                # 填充每一列
                for col, value in enumerate(password):
                    if col < self.table.columnCount():
                        text = value
                        if col == 0 and prefix:  # 为项目名称添加所有者前缀
                            text = f"{prefix}{value}"
                        self.table.setItem(row, col, create_table_item(text))
                
            # 重新启用排序
            self.table.setSortingEnabled(True)
            
            return True
        except Exception as e:
            logger.error(f"搜索密码时出错: {str(e)}")
            return False
            
    def _refresh_search_results(self):
        """
        刷新搜索结果
        """
        # 如果不在搜索模式，不需要刷新
        if not self.search_mode or not self.search_results:
            return
            
        # 清空表格
        self.table.setRowCount(0)
        
        # 重新填充表格
        for row, (owner, password) in enumerate(self.search_results):
            self.table.insertRow(row)
            
            # 设置行号为从1开始
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(row + 1)))
            
            # 填充所有者列（如果与当前所有者不同，添加所有者前缀）
            prefix = f"[{owner}] " if owner != self.current_owner else ""
            
            # 填充每一列
            for col, value in enumerate(password):
                if col < self.table.columnCount():
                    text = value
                    if col == 0 and prefix:  # 为项目名称添加所有者前缀
                        text = f"{prefix}{value}"
                    self.table.setItem(row, col, create_table_item(text))
            
    def clear_search(self) -> bool:
        """
        清除搜索结果，恢复显示所有密码
        
        Returns:
            bool: 清除成功返回True，否则返回False
        """
        if not self.search_mode:
            return True
            
        try:
            # 清除搜索模式标识
            self.search_mode = False
            
            # 清除搜索文本
            if hasattr(self, 'last_search_text'):
                logger.debug(f"清除搜索关键字: '{self.last_search_text}'")
                self.last_search_text = ""
                
            # 清除搜索结果
            self.search_results = None
            
            # 重新加载全部密码
            self._load_passwords_internal(self.current_owner)
            
            return True
        except Exception as e:
            logger.error(f"清除搜索结果时出错: {str(e)}")
            return False 