#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接从数据库检查用户设置
"""

import os
import sys
import json

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入相关模块
from core.db_manager import db_manager

def main():
    """直接从数据库查询用户设置"""
    username = "admin"
    
    # 查询用户所有设置
    query = "SELECT id, username, setting_key, setting_value, created_at, updated_at FROM user_settings WHERE username = %s"
    results = db_manager.execute_query(query, (username,))
    
    print(f"用户 {username} 的设置:")
    print("=" * 80)
    
    # 格式化打印结果
    for row in results:
        # 获取各字段值
        if isinstance(row, dict):
            # 字典格式结果
            id_val = row.get('id')
            username_val = row.get('username')
            key_val = row.get('setting_key')
            value_val = row.get('setting_value')
            created_at_val = row.get('created_at')
            updated_at_val = row.get('updated_at')
        else:
            # 元组格式结果
            id_val, username_val, key_val, value_val, created_at_val, updated_at_val = row
        
        # 尝试美化JSON格式
        try:
            if isinstance(value_val, str):
                value_parsed = json.loads(value_val)
                value_formatted = json.dumps(value_parsed, ensure_ascii=False, indent=2)
            else:
                value_formatted = str(value_val)
        except:
            value_formatted = str(value_val)
            
        print(f"ID: {id_val}")
        print(f"用户名: {username_val}")
        print(f"设置键: {key_val}")
        print(f"设置值: {value_formatted}")
        print(f"创建时间: {created_at_val}")
        print(f"更新时间: {updated_at_val}")
        print("-" * 80)
        
        # 特别检查guides.main_features_guided
        if key_val == "guides.main_features_guided":
            print("\n特别关注的设置项:")
            print(f"guides.main_features_guided 的值类型: {type(value_val)}")
            print(f"值内容: {value_val}")
            if isinstance(value_val, str):
                try:
                    parsed = json.loads(value_val)
                    print(f"解析后的值: {parsed}, 类型: {type(parsed)}")
                except:
                    print("无法解析为JSON")

if __name__ == "__main__":
    main() 