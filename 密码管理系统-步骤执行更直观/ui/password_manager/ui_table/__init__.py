#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理表格模块
整合所有表格相关功能
"""

from .base_table import BasePasswordTable
from .table_data import TableDataMixin
from .table_edit import TableEditMixin
from .table_search import TableSearchMixin
from .table_events import TableEventsMixin, TableEventFilter
from .table_password import TablePasswordMixin


class PasswordTable(BasePasswordTable, 
                   TableDataMixin,
                   TableEditMixin,
                   TableSearchMixin, 
                   TableEventsMixin,
                   TablePasswordMixin):
    """
    密码表格类
    
    整合所有表格功能，包括基础表格、数据加载、编辑、搜索、事件处理和密码生成等。
    """
    
    def __init__(self, table_widget):
        """
        初始化密码表格
        
        Args:
            table_widget: 表格控件
        """
        # 调用基类初始化
        BasePasswordTable.__init__(self, table_widget)
        
        # 连接右键菜单信号
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # 安装事件过滤器
        self.table.installEventFilter(TableEventFilter(self.table, self)) 