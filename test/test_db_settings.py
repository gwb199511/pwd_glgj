#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试数据库用户设置
"""

import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.db_manager import db_manager
from core.db_user_settings import db_user_settings
from core.user_settings import user_settings

def main():
    """主函数"""
    print("=" * 50)
    print("测试数据库用户设置")
    print("=" * 50)
    
    # 检查表是否存在
    check_table_sql = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = DATABASE() 
    AND table_name = 'user_settings'
    """
    table_result = db_manager.execute_query(check_table_sql)
    table_exists = table_result and len(table_result) > 0
    
    print(f"\n1. 用户设置表是否存在: {table_exists}")
    print(f"   查询结果: {table_result}")
    
    if table_exists:
        # 查询记录数
        count_sql = "SELECT COUNT(*) FROM user_settings"
        count_result = db_manager.execute_query(count_sql)
        print(f"   查询COUNT结果: {count_result}")
        
        # 安全地提取记录数
        record_count = 0
        if count_result and len(count_result) > 0:
            try:
                if isinstance(count_result[0], dict):
                    # 字典形式的结果
                    record_count = count_result[0].get('COUNT(*)', 0)
                else:
                    # 元组形式的结果
                    record_count = count_result[0][0]
            except Exception as e:
                print(f"   提取记录数时出错: {str(e)}")
                if count_result:
                    print(f"   结果类型: {type(count_result)}, 内容: {count_result}")
        
        print(f"\n2. 用户设置表记录数: {record_count}")
        
        if record_count > 0:
            # 查询所有记录
            all_records_sql = "SELECT id, username, setting_key, setting_value FROM user_settings LIMIT 10"
            all_records = db_manager.execute_query(all_records_sql)
            print(f"   查询记录结果: {all_records}")
            
            print("\n3. 前10条用户设置记录:")
            if all_records:
                for i, record in enumerate(all_records):
                    try:
                        if isinstance(record, dict):
                            # 字典形式的结果
                            print(f"   #{i+1}: ID: {record.get('id')}, 用户: {record.get('username')}, "
                                  f"键: {record.get('setting_key')}, 值: {record.get('setting_value')}")
                        else:
                            # 元组形式的结果
                            print(f"   #{i+1}: ID: {record[0]}, 用户: {record[1]}, 键: {record[2]}, 值: {record[3]}")
                    except Exception as e:
                        print(f"   处理记录 #{i+1} 时出错: {str(e)}")
                        print(f"   记录内容: {record}")
            else:
                print("   无记录")
            
            # 测试读取
            test_username = "default"
            test_setting = "ui.table_font_size"
            print(f"\n4. 读取设置 {test_username}/{test_setting}")
            try:
                value = db_user_settings.get_setting(test_username, test_setting, None)
                print(f"   值: {value}")
            except Exception as e:
                print(f"   读取设置时出错: {str(e)}")
            
            # 测试内存缓存
            print(f"\n5. 从内存缓存读取 ui.table_font_size")
            try:
                cached_value = user_settings.get("ui.table_font_size")
                print(f"   缓存值: {cached_value}")
            except Exception as e:
                print(f"   读取缓存时出错: {str(e)}")
            
            # 测试写入
            test_key = "test.sample_setting"
            test_value = f"测试值 {record_count}"
            print(f"\n6. 写入测试设置 {test_key}: {test_value}")
            try:
                db_user_settings.set_setting(test_username, test_key, test_value)
                print(f"   设置成功")
                
                # 再次读取
                new_value = db_user_settings.get_setting(test_username, test_key, None)
                print(f"   读取新设置: {new_value}")
            except Exception as e:
                print(f"   写入/读取新设置时出错: {str(e)}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    main() 