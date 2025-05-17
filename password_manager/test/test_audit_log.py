#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
审计日志系统测试脚本
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from features.audit.audit_log import audit_logger, OP_RESULT_SUCCESS
from core.db_manager import check_audit_logs_table

def main():
    """主函数"""
    print("开始测试审计日志系统...")
    
    # 检查audit_logs表是否存在
    print("\n1. 检查audit_logs表:")
    table_exists, count, latest = check_audit_logs_table()
    print(f"   - 表是否存在: {table_exists}")
    print(f"   - 当前记录数: {count}")
    if latest:
        print(f"   - 最新记录: ID={latest['id']}, 用户={latest['username']}, 操作={latest['operation_type']}")
    
    # 添加测试日志
    print("\n2. 添加测试日志:")
    test_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success = audit_logger.log_operation(
        operation_type="test",
        result=OP_RESULT_SUCCESS,
        details=f"审计日志数据库存储测试 - {test_time}",
        user="test_user",
        target="审计系统测试"
    )
    print(f"   - 添加结果: {'成功' if success else '失败'}")
    
    # 等待一会儿，让异步日志处理有时间完成
    print("\n3. 等待异步处理完成...")
    time.sleep(3)
    
    # 再次检查audit_logs表
    print("\n4. 再次检查audit_logs表:")
    table_exists, count, latest = check_audit_logs_table()
    print(f"   - 表是否存在: {table_exists}")
    print(f"   - 当前记录数: {count}")
    if latest:
        print(f"   - 最新记录: ID={latest['id']}, 用户={latest['username']}, 操作={latest['operation_type']}")
        print(f"   - 详细信息: {latest['details']}")
        print(f"   - 时间: {latest['created_at']}")
    
    # 查询日志测试
    print("\n5. 测试查询日志功能:")
    logs = audit_logger.get_logs(limit=5)
    print(f"   - 查询到 {len(logs)} 条日志")
    for i, log in enumerate(logs[:3], 1):
        print(f"   - 日志 #{i}: 用户={log.get('user')}, 操作={log.get('operation')}, 详情={log.get('details')}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    main() 