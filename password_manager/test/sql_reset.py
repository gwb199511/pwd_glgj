#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用原始SQL命令重置引导状态
"""

import os
import sys
import pymysql
import json

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入配置
from config import DEFAULT_MYSQL_CONFIG, DATA_DIR, DB_CONFIG_FILE

def main():
    """重置所有引导状态"""
    print("正在重置所有引导状态...")
    
    # 加载数据库配置
    db_config = DEFAULT_MYSQL_CONFIG
    
    # 尝试从文件加载配置（如果存在）
    if os.path.exists(DB_CONFIG_FILE):
        try:
            with open(DB_CONFIG_FILE, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                db_config.update(file_config)
                print(f"已从 {DB_CONFIG_FILE} 加载数据库配置")
        except Exception as e:
            print(f"加载数据库配置文件出错: {str(e)}")
    
    # 连接到数据库
    try:
        conn = pymysql.connect(
            host=db_config.get('host', 'localhost'),
            user=db_config.get('user', 'root'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'password_manager'),
            port=db_config.get('port', 3306),
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # 更新引导状态
        username = "admin"
        guides_to_reset = [
            "guides.main_features_guided",
            "guides.password_update_guided"
        ]
        
        # 查询当前值
        for guide_key in guides_to_reset:
            cursor.execute(
                "SELECT id, setting_value FROM user_settings WHERE username = %s AND setting_key = %s",
                (username, guide_key)
            )
            result = cursor.fetchone()
            
            if result:
                id_val, value = result
                print(f"设置 {guide_key} (ID: {id_val}) 当前值: {value}")
                
                # 更新值
                cursor.execute(
                    "UPDATE user_settings SET setting_value = 'false' WHERE id = %s",
                    (id_val,)
                )
                affected = cursor.rowcount
                print(f"已更新 {guide_key} 为 false, 影响行数: {affected}")
            else:
                print(f"未找到设置: {guide_key}")
                
        # 提交更改
        conn.commit()
        
        # 验证更改
        print("\n验证更改:")
        for guide_key in guides_to_reset:
            cursor.execute(
                "SELECT setting_value FROM user_settings WHERE username = %s AND setting_key = %s",
                (username, guide_key)
            )
            result = cursor.fetchone()
            if result:
                print(f"设置 {guide_key} 新值: {result[0]}")
            else:
                print(f"未找到设置: {guide_key}")
                
        # 关闭连接
        cursor.close()
        conn.close()
        
        print("\n所有引导状态已重置，下次启动应用时将显示引导界面")
        
    except Exception as e:
        print(f"数据库操作失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 