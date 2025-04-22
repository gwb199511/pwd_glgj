#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库用户设置管理模块
用于在MySQL数据库中管理用户设置
"""

import json
import logging
import os
from datetime import datetime

from core.db_manager import db_manager
from config import DATA_DIR

# 旧的用户设置文件路径
USER_SETTINGS_FILE = os.path.join(DATA_DIR, 'user_settings.json')

class DBUserSettings:
    """数据库用户设置管理类"""
    
    def __init__(self):
        """初始化用户设置管理器"""
        self.logger = logging.getLogger(__name__)
        self._ensure_settings_table()
        
    def _ensure_settings_table(self):
        """确保用户设置表存在"""
        try:
            # 检查数据库中是否已存在user_settings表
            sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'user_settings'
            """
            result = db_manager.execute_query(sql)
            
            # 检查是否存在表
            table_exists = result and len(result) > 0
            
            if not table_exists:
                # 如果表不存在，创建表
                self.logger.info("创建user_settings表")
                create_table_sql = """
                CREATE TABLE `user_settings` (
                  `id` int NOT NULL AUTO_INCREMENT,
                  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                  `setting_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                  `setting_value` json NULL,
                  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`) USING BTREE,
                  UNIQUE INDEX `unique_user_setting`(`username` ASC, `setting_key` ASC) USING BTREE
                ) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;
                """
                db_manager.execute_query(create_table_sql)
                self.logger.info("成功创建user_settings表")
        except Exception as e:
            self.logger.error(f"检查/创建用户设置表时出错: {str(e)}")
            raise
    
    def migrate_from_file(self, default_username="default"):
        """从文件中迁移用户设置到数据库"""
        if not os.path.exists(USER_SETTINGS_FILE):
            self.logger.warning(f"用户设置文件不存在: {USER_SETTINGS_FILE}")
            return False
            
        try:
            # 读取文件中的设置
            with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                file_settings = json.load(f)
                
            # 迁移设置到数据库
            self.logger.info("开始迁移用户设置到数据库")
            
            # 扁平化设置并写入数据库
            for section, settings in file_settings.items():
                for key, value in settings.items():
                    setting_key = f"{section}.{key}"
                    self.set_setting(default_username, setting_key, value)
                    
            self.logger.info("用户设置迁移完成")
            
            # 备份旧设置文件
            backup_file = f"{USER_SETTINGS_FILE}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            os.rename(USER_SETTINGS_FILE, backup_file)
            self.logger.info(f"已备份旧的用户设置文件为: {backup_file}")
            
            return True
        except Exception as e:
            self.logger.error(f"迁移用户设置时出错: {str(e)}")
            return False
    
    def get_setting(self, username, setting_key, default_value=None):
        """获取用户设置"""
        try:
            sql = """
            SELECT setting_value 
            FROM user_settings 
            WHERE username = %s AND setting_key = %s
            """
            params = (username, setting_key)
            result = db_manager.execute_query(sql, params)
            
            if result and len(result) > 0:
                # 从JSON字符串解析设置值
                if isinstance(result[0], dict):
                    # 字典形式的结果
                    value = result[0].get('setting_value')
                else:
                    # 元组形式的结果
                    value = result[0][0]
                    
                try:
                    if value and isinstance(value, str):
                        return json.loads(value)
                    return value
                except (json.JSONDecodeError, TypeError):
                    return value
            return default_value
        except Exception as e:
            self.logger.error(f"获取设置 {username}/{setting_key} 时出错: {str(e)}")
            return default_value
    
    def set_setting(self, username, setting_key, setting_value):
        """设置用户设置"""
        try:
            # 将值转换为JSON字符串
            if not isinstance(setting_value, str):
                # 非字符串值使用json.dumps
                json_value = json.dumps(setting_value)
            else:
                # 尝试将字符串解析为JSON，如果成功，直接存储；如果失败，包装为JSON字符串
                try:
                    json.loads(setting_value)
                    # 如果能解析为有效JSON，直接使用
                    json_value = setting_value
                except json.JSONDecodeError:
                    # 如果不是有效JSON，包装为JSON字符串
                    json_value = json.dumps(setting_value)
                
            # 使用REPLACE INTO语法，如果记录不存在则插入，如果存在则更新
            sql = """
            REPLACE INTO user_settings 
            (username, setting_key, setting_value) 
            VALUES (%s, %s, %s)
            """
            params = (username, setting_key, json_value)
            db_manager.execute_query(sql, params)
            return True
        except Exception as e:
            self.logger.error(f"设置 {username}/{setting_key} 值为 {setting_value} 时出错: {str(e)}")
            return False
    
    def delete_setting(self, username, setting_key):
        """删除用户设置"""
        sql = """
        DELETE FROM user_settings 
        WHERE username = %s AND setting_key = %s
        """
        params = (username, setting_key)
        db_manager.execute_query(sql, params)
        return True
    
    def get_all_settings(self, username):
        """获取用户的所有设置"""
        sql = """
        SELECT setting_key, setting_value 
        FROM user_settings 
        WHERE username = %s
        """
        params = (username,)
        result = db_manager.execute_query(sql, params)
        
        settings = {}
        for row in result:
            key, value = row
            # 处理层次结构的键 (如 "guides.password_update_guided")
            parts = key.split('.')
            current = settings
            
            # 遍历键的每一部分，创建必要的嵌套字典
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # 最后一部分是实际的键
                    try:
                        current[part] = json.loads(value) if value else value
                    except (json.JSONDecodeError, TypeError):
                        current[part] = value
                else:
                    # 中间部分是嵌套字典
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                    
        return settings
    
    def reset_guides(self, username="default"):
        """重置引导记录"""
        guides_keys = [
            "guides.password_update_guided"
        ]
        
        for key in guides_keys:
            self.set_setting(username, key, False)
        
        return True

# 创建单例实例
db_user_settings = DBUserSettings() 