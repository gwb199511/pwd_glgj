#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重置引导状态脚本
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入相关模块
from core.db_manager import db_manager

def main():
    """重置所有引导状态"""
    print("正在重置所有引导状态...")
    
    # 设置默认用户
    username = "admin"
    
    # 直接操作数据库确保重置
    guides_to_reset = [
        "guides.main_features_guided",
        "guides.password_update_guided"
    ]
    
    for guide_key in guides_to_reset:
        # 先查询当前值
        query = "SELECT setting_value FROM user_settings WHERE username = %s AND setting_key = %s"
        result = db_manager.execute_query(query, (username, guide_key))
        
        # 正确处理查询结果
        current_value = None
        if result and len(result) > 0:
            row = result[0]
            if isinstance(row, dict):
                # 字典形式的结果
                current_value = row.get('setting_value')
            elif isinstance(row, (list, tuple)) and len(row) > 0:
                # 元组/列表形式的结果
                current_value = row[0]
                
        print(f"设置 {guide_key} 当前值: {current_value}")
        
        # 设置为false
        update_query = """
        UPDATE user_settings 
        SET setting_value = 'false' 
        WHERE username = %s AND setting_key = %s
        """
        affected = db_manager.execute_query(update_query, (username, guide_key))
        print(f"已将 {guide_key} 重置为 false, 影响行数: {affected}")
    
    # 验证重置结果
    print("\n验证重置结果:")
    for guide_key in guides_to_reset:
        query = "SELECT setting_value FROM user_settings WHERE username = %s AND setting_key = %s"
        result = db_manager.execute_query(query, (username, guide_key))
        
        # 正确处理查询结果
        current_value = None
        if result and len(result) > 0:
            row = result[0]
            if isinstance(row, dict):
                # 字典形式的结果
                current_value = row.get('setting_value')
            elif isinstance(row, (list, tuple)) and len(row) > 0:
                # 元组/列表形式的结果
                current_value = row[0]
                
        print(f"设置 {guide_key} 新值: {current_value}")
    
    print("\n所有引导状态已重置，下次启动应用时将显示引导界面")

if __name__ == "__main__":
    main() 