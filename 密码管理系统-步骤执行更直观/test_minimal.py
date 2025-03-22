#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
最小化测试脚本，隔离导入问题
"""

print("1. 开始导入模块")
import sys
print("2. 导入sys成功")
import traceback
print("3. 导入traceback成功")

try:
    print("4. 准备导入PyQt5")
    from PyQt5.QtWidgets import QApplication
    print("5. 导入PyQt5.QtWidgets成功")
except Exception as e:
    print(f"导入PyQt5失败: {str(e)}")
    traceback.print_exc()

try:
    print("6. 准备导入audit_log")
    import audit_log
    print("7. 导入audit_log成功")
except Exception as e:
    print(f"导入audit_log失败: {str(e)}")
    traceback.print_exc()

try:
    print("8. 准备导入AuditLogViewer")
    from audit_log_viewer import AuditLogViewer
    print("9. 导入AuditLogViewer成功")
except Exception as e:
    print(f"导入AuditLogViewer失败: {str(e)}")
    traceback.print_exc()

print("10. 脚本执行结束") 