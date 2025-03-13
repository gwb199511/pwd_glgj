#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理表格模块
重定向到拆分后的表格模块
"""

# 从新的模块导入所需类
from ui.password_manager.ui_table import PasswordTable, TableEventFilter

# 重新导出类，提供向后兼容性
__all__ = ['PasswordTable', 'TableEventFilter'] 