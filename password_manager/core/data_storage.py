#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据存储模块，提供抽象存储层，使用MySQL数据库存储
"""

import os
import json
import logging
import threading
import traceback
from typing import Dict, List, Any, Tuple, Optional, Union, Callable
from abc import ABC, abstractmethod

from config import DATA_DIR
from core.db_manager import db_manager

# 配置日志
logger = logging.getLogger(__name__)


class StorageBase(ABC):
    """
    存储基类（抽象基类），定义存储接口
    
    提供统一的存储接口，子类可以实现不同的存储方式。
    """
    
    @abstractmethod
    def load(self, key: Optional[str] = None) -> Dict[str, Any]:
        """
        加载数据
        
        Args:
            key (Optional[str]): 可选的键名，用于指定要加载的数据部分
            
        Returns:
            Dict[str, Any]: 加载的数据
        """
        pass
    
    @abstractmethod
    def save(self, data: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        保存数据
        
        Args:
            data (Dict[str, Any]): 要保存的数据
            key (Optional[str]): 可选的键名，用于指定要保存的数据部分
            
        Returns:
            bool: 操作是否成功
        """
        pass
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取指定键的数据
        
        Args:
            key (str): 键名
            default (Any, optional): 默认值，当键不存在时返回
            
        Returns:
            Any: 键对应的值，或者默认值（如果键不存在）
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> bool:
        """
        设置指定键的值
        
        Args:
            key (str): 键名
            value (Any): 值
            
        Returns:
            bool: 操作是否成功
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        删除指定键
        
        Args:
            key (str): 要删除的键名
            
        Returns:
            bool: 删除是否成功
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key (str): 要检查的键名
            
        Returns:
            bool: 键是否存在
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有数据
        
        Returns:
            Dict[str, Any]: 所有数据
        """
        pass


class MySQLStorage(StorageBase):
    """
    MySQL存储类，基于MySQL数据库实现
    
    根据不同的数据类型（用户、密码等）提供相应的存储实现。
    """
    
    def __init__(self, table_name: str, id_field: str = 'id'):
        """
        初始化MySQL存储
        
        Args:
            table_name (str): 表名
            id_field (str): ID字段名
        """
        self.table_name = table_name
        self.id_field = id_field
        self.data = {}
    
    def load(self, key: Optional[str] = None) -> Dict[str, Any]:
        """
        加载数据
        
        Args:
            key (Optional[str]): 可选的键名，用于指定要加载的数据部分
            
        Returns:
            Dict[str, Any]: 加载的数据
        """
        try:
            # 构建查询条件
            where_clause = ""
            params = ()
            
            if key:
                if self.table_name == "users":
                    where_clause = "WHERE username = %s"
                    params = (key,)
                elif self.table_name == "passwords":
                    where_clause = "WHERE owner = %s"
                    params = (key,)
                elif self.table_name == "user_settings":
                    where_clause = "WHERE username = %s"
                    params = (key,)
            
            # 执行查询
            sql = f"SELECT * FROM {self.table_name} {where_clause}"
            results = db_manager.execute_query(sql, params)
            
            # 处理结果
            if self.table_name == "users":
                # 用户数据以用户名为键，密码为值
                self.data = {row['username']: row['password'] for row in results}
            elif self.table_name == "passwords":
                # 密码数据以owner为键，密码列表为值
                self.data = {}
                for row in results:
                    owner = row['owner']
                    if owner not in self.data:
                        self.data[owner] = []
                    
                    # 构建密码记录（与JSON格式一致）
                    # 兼容两种列名：function和func_desc
                    func_description = ""
                    if 'func_desc' in row:
                        func_description = row['func_desc'] or ""
                    elif 'function' in row:
                        func_description = row['function'] or ""
                    
                    password_record = [
                        row['project_name'],
                        func_description,
                        row['ip_address'],
                        row['account'],
                        row['password'],
                        row['area'] or "",
                        row['network_type'] or "",
                        row['other_info'] or ""
                    ]
                    
                    self.data[owner].append(password_record)
            elif self.table_name == "remember":
                # 记住登录信息以用户名为键，密码为值
                self.data = {}
                # 只加载未过期的记录
                from datetime import datetime
                current_time = datetime.now()
                
                for row in results:
                    username = row['username']
                    expire_at = row['expire_at']
                    
                    # 检查是否已过期
                    if expire_at and expire_at > current_time:
                        self.data[username] = row['password']
            elif self.table_name == "user_settings":
                # 用户设置数据以用户名为键，设置键值对为值
                self.data = {}
                for row in results:
                    username = row['username']
                    if username not in self.data:
                        self.data[username] = {}
                    
                    # 解析嵌套键
                    setting_key = row['setting_key']
                    parts = setting_key.split('.')
                    
                    # 解析JSON值
                    try:
                        value = json.loads(row['setting_value'])
                    except:
                        value = row['setting_value']
                    
                    # 构建嵌套字典
                    current = self.data[username]
                    for i, part in enumerate(parts[:-1]):
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    
                    current[parts[-1]] = value
            
            if key:
                return {key: self.data.get(key, {})}
            return self.data
            
        except Exception as e:
            logger.error(f"MySQL加载数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return {}
    
    def save(self, data: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        保存数据
        
        Args:
            data (Dict[str, Any]): 要保存的数据
            key (Optional[str]): 可选的键名，用于指定要保存的数据部分
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if key:
                value = data.get(key, {})
                return self.set(key, value)
            else:
                # 处理整个数据集 - 批量处理减少数据库连接次数
                # 为不同表类型准备批量操作
                if self.table_name == "user_settings":
                    return self._batch_save_settings(data)
                else:
                    # 处理整个数据集
                    success = True
                    for k, v in data.items():
                        if not self.set(k, v):
                            success = False
                    return success
                
        except Exception as e:
            logger.error(f"MySQL保存数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def _batch_save_settings(self, settings_data: Dict[str, Any]) -> bool:
        """
        批量保存用户设置数据（特殊处理减少数据库操作）
        
        Args:
            settings_data (Dict[str, Any]): 设置数据
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取所有设置项及其嵌套结构
            flattened_settings = {}
            
            # 递归展平嵌套字典
            def flatten_dict(prefix, obj):
                for k, v in obj.items():
                    key = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, dict):
                        flatten_dict(key, v)
                    else:
                        flattened_settings[key] = v
            
            # 处理所有用户
            for username, user_settings in settings_data.items():
                # 展平该用户的所有设置
                flatten_dict("", user_settings)
                
                # 准备批量插入的参数
                batch_values = []
                for setting_key, setting_value in flattened_settings.items():
                    # 将值转换为JSON字符串
                    value_json = json.dumps(setting_value, ensure_ascii=False)
                    batch_values.append((username, setting_key, value_json))
                
                if not batch_values:
                    continue
                
                # 获取数据库连接
                conn = None
                try:
                    from core.db_manager import db_manager
                    
                    # 删除该用户的所有设置
                    db_manager.execute_update(
                        f"DELETE FROM {self.table_name} WHERE username = %s", 
                        (username,)
                    )
                    
                    # 批量插入新设置
                    # 使用REPLACE INTO来处理唯一键冲突
                    for username, setting_key, value_json in batch_values:
                        sql = """
                            REPLACE INTO user_settings (username, setting_key, setting_value)
                            VALUES (%s, %s, %s)
                        """
                        db_manager.execute_insert(sql, (username, setting_key, value_json))
                        
                except Exception as e:
                    logger.error(f"批量保存设置时出错: {str(e)}")
                    return False
            
            # 更新内存数据
            self.data = settings_data
            return True
            
        except Exception as e:
            logger.error(f"批量处理设置数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取指定键的数据
        
        Args:
            key (str): 键名
            default (Any, optional): 默认值，当键不存在时返回
            
        Returns:
            Any: 键对应的值，或者默认值（如果键不存在）
        """
        # 首先尝试从内存中获取
        if key in self.data:
            return self.data[key]
        
        # 否则从数据库加载
        result = self.load(key)
        return result.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置指定键的值
        
        Args:
            key (str): 键名
            value (Any): 值
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 更新内存中的数据
            self.data[key] = value
            
            # 记录操作开始
            logger.info(f"开始设置键 '{key}' 的值 - 表: {self.table_name}")
            
            # 根据不同表类型处理数据
            if self.table_name == "users":
                # 删除原有数据
                delete_sql = f"DELETE FROM {self.table_name} WHERE username = %s"
                logger.debug(f"执行SQL: {delete_sql} - 参数: {key}")
                db_manager.execute_update(delete_sql, (key,))
                
                # 插入新数据
                insert_sql = f"INSERT INTO {self.table_name} (username, password) VALUES (%s, %s)"
                logger.debug(f"执行SQL: {insert_sql} - 参数: {key}, [密码已隐藏]")
                result = db_manager.execute_insert(insert_sql, (key, value))
                logger.info(f"插入结果: {result}")
                return result > 0
                
            elif self.table_name == "passwords":
                # 删除原有数据
                delete_sql = f"DELETE FROM {self.table_name} WHERE owner = %s"
                logger.debug(f"执行SQL: {delete_sql} - 参数: {key}")
                rows_affected = db_manager.execute_update(delete_sql, (key,))
                logger.info(f"已删除 {rows_affected} 条 {key} 的密码记录")
                
                # 插入新数据
                success = True
                records_inserted = 0
                
                if not value or len(value) == 0:
                    logger.warning(f"为 {key} 设置的值是空列表，不会插入任何记录")
                
                for record in value:
                    if len(record) < 8:  # 确保记录格式正确
                        logger.warning(f"记录格式不正确，至少需要8个字段: {record}")
                        continue
                    
                    insert_sql = """
                        INSERT INTO passwords 
                        (owner, project_name, func_desc, ip_address, account, password, area, network_type, other_info)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (
                        key,           # owner
                        record[0],     # project_name
                        record[1],     # func_desc
                        record[2],     # ip_address
                        record[3],     # account
                        record[4],     # password
                        record[5],     # area
                        record[6],     # network_type
                        record[7]      # other_info
                    )
                    
                    logger.debug(f"执行SQL: {insert_sql} - 参数: {key}, {record[0]}, {record[1]}, {record[2]}, {record[3]}, [密码已隐藏], {record[5]}, {record[6]}, {record[7]}")
                    result = db_manager.execute_insert(insert_sql, params)
                    
                    if result > 0:
                        records_inserted += 1
                    else:
                        logger.error(f"插入记录失败: {record[0]}")
                        success = False
                
                logger.info(f"为 {key} 成功修改了 {records_inserted} 条记录")
                return success
                
            elif self.table_name == "user_settings":
                # 递归处理设置
                def process_settings(prefix, data):
                    success = True
                    for k, v in data.items():
                        setting_key = f"{prefix}.{k}" if prefix else k
                        
                        if isinstance(v, dict):
                            # 递归处理嵌套字典
                            if not process_settings(setting_key, v):
                                success = False
                        else:
                            # 删除原有数据
                            db_manager.execute_update(
                                f"DELETE FROM {self.table_name} WHERE username = %s AND setting_key = %s", 
                                (key, setting_key)
                            )
                            
                            # 将值转换为JSON字符串
                            value_json = json.dumps(v, ensure_ascii=False)
                            
                            # 插入新数据
                            sql = """
                                INSERT INTO user_settings (username, setting_key, setting_value)
                                VALUES (%s, %s, %s)
                            """
                            result = db_manager.execute_insert(sql, (key, setting_key, value_json))
                            
                            if result <= 0:
                                success = False
                    
                    return success
                
                return process_settings("", value)
                
            elif self.table_name == "remember":
                # 删除原有数据
                db_manager.execute_update(f"DELETE FROM {self.table_name} WHERE username = %s", (key,))
                
                # 添加过期时间
                from datetime import datetime, timedelta
                from config import REMEMBER_EXPIRE_DAYS
                expire_at = datetime.now() + timedelta(days=REMEMBER_EXPIRE_DAYS)
                
                # 插入新数据
                sql = """
                    INSERT INTO remember (username, password, expire_at) 
                    VALUES (%s, %s, %s)
                """
                result = db_manager.execute_insert(sql, (key, value, expire_at))
                return result > 0
                
            else:
                logger.warning(f"未知的表类型: {self.table_name}")
                return False
                
        except Exception as e:
            logger.error(f"MySQL设置数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除指定键
        
        Args:
            key (str): 要删除的键名
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 从内存中删除
            if key in self.data:
                del self.data[key]
            
            # 构建WHERE子句
            where_field = ""
            if self.table_name == "users":
                where_field = "username"
            elif self.table_name == "passwords":
                where_field = "owner"
            elif self.table_name == "user_settings":
                where_field = "username"
            else:
                return False
            
            # 执行删除
            sql = f"DELETE FROM {self.table_name} WHERE {where_field} = %s"
            result = db_manager.execute_update(sql, (key,))
            
            return result >= 0  # 0表示没有行受影响，但也算成功
            
        except Exception as e:
            logger.error(f"MySQL删除数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key (str): 要检查的键名
            
        Returns:
            bool: 键是否存在
        """
        try:
            # 构建WHERE子句
            where_field = ""
            if self.table_name == "users":
                where_field = "username"
            elif self.table_name == "passwords":
                where_field = "owner"
            elif self.table_name == "user_settings":
                where_field = "username"
            else:
                return False
            
            # 执行查询
            sql = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {where_field} = %s"
            results = db_manager.execute_query(sql, (key,))
            
            return results[0]['count'] > 0 if results else False
            
        except Exception as e:
            logger.error(f"MySQL检查键是否存在时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有数据
        
        Returns:
            Dict[str, Any]: 所有数据
        """
        try:
            # 强制从数据库重新加载数据，而不是使用缓存
            self.data = {}  # 清除缓存
            self.load()     # 从数据库重新加载
            logger.debug(f"从数据库获取所有{self.table_name}数据: {list(self.data.keys())}")
            return self.data
        except Exception as e:
            logger.error(f"获取所有数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return self.data


class StorageFactory:
    """
    存储工厂类，负责创建存储实例
    
    根据配置文件中的存储类型创建相应的存储实例。
    """
    
    @staticmethod
    def create_storage(storage_type: str, file_path: Optional[str] = None, 
                      table_name: Optional[str] = None) -> StorageBase:
        """
        创建MySQL存储实例
        
        Args:
            storage_type (str): 仅支持"mysql"
            file_path (Optional[str]): 已弃用，保留参数是为了兼容性
            table_name (Optional[str]): MySQL存储的表名
            
        Returns:
            StorageBase: MySQL存储实例
        """
        if not table_name:
            raise ValueError("使用MySQL存储时必须指定表名")
        return MySQLStorage(table_name)
    
    @staticmethod
    def get_storage_type() -> str:
        """
        获取当前存储类型
        
        Returns:
            str: 强制返回"mysql"作为存储类型，确保系统始终使用MySQL存储
        """
        # 始终强制返回"mysql"作为存储类型
        # 从config导入STORAGE_TYPE，但忽略它的值
        from config import STORAGE_TYPE
        return "mysql"


class PasswordHistoryStorage:
    """
    密码历史记录存储类，管理密码修改历史记录
    
    提供添加和查询密码历史记录的功能。
    """
    
    _instance = None
    
    def __new__(cls):
        """
        单例模式，确保密码历史记录存储只有一个实例
        
        Returns:
            PasswordHistoryStorage: 密码历史记录存储实例
        """
        if cls._instance is None:
            cls._instance = super(PasswordHistoryStorage, cls).__new__(cls)
        return cls._instance
    
    def add_history(self, password_id: int, old_password: str, new_password: str, 
                   ip_address: str, modify_user: str, modify_reason: str = "") -> bool:
        """
        添加密码修改历史记录
        
        Args:
            password_id (int): 密码ID
            old_password (str): 修改前的密码
            new_password (str): 修改后的密码
            ip_address (str): IP地址
            modify_user (str): 修改人
            modify_reason (str, optional): 修改原因，默认为空字符串
            
        Returns:
            bool: 操作是否成功
        """
        try:
            from datetime import datetime
            
            # 验证密码ID是否存在
            verify_sql = "SELECT id FROM passwords WHERE id = %s"
            id_exists = db_manager.execute_query(verify_sql, [password_id])
            
            # 如果ID不存在，尝试通过IP地址查找正确的ID
            if not id_exists and ip_address:
                logger.warning(f"历史记录使用的密码ID {password_id} 不存在，尝试通过IP地址 {ip_address} 查找")
                find_id_sql = "SELECT id FROM passwords WHERE ip_address = %s ORDER BY id DESC LIMIT 1"
                ip_results = db_manager.execute_query(find_id_sql, [ip_address])
                
                if ip_results and len(ip_results) > 0:
                    new_id = ip_results[0]['id']
                    logger.info(f"找到新的密码ID: {new_id}，原ID: {password_id}")
                    password_id = new_id
                else:
                    logger.error(f"无法找到IP地址 {ip_address} 对应的密码记录")
            
            # 插入历史记录
            sql = """
                INSERT INTO password_history 
                (password_id, old_password, new_password, ip_address, modify_user, modify_reason, modify_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                password_id,
                old_password,
                new_password,
                ip_address,
                modify_user,
                modify_reason,
                datetime.now()
            )
            
            result = db_manager.execute_insert(sql, params)
            return result > 0
            
        except Exception as e:
            logger.error(f"添加密码历史记录失败: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def get_history(self, password_id: int, page: int = 1, page_size: int = 10, 
                   start_time: Optional[str] = None, end_time: Optional[str] = None,
                   ip_address: Optional[str] = None, account: Optional[str] = None) -> Dict[str, Any]:
        """
        获取密码修改历史记录
        
        Args:
            password_id (int): 密码ID
            page (int, optional): 页码，从1开始。默认为1。
            page_size (int, optional): 每页记录数。默认为10。
            start_time (Optional[str], optional): 开始时间，格式为'YYYY-MM-DD HH:MM:SS'。默认为None。
            end_time (Optional[str], optional): 结束时间，格式为'YYYY-MM-DD HH:MM:SS'。默认为None。
            ip_address (Optional[str], optional): IP地址(用于备选查询)。默认为None。
            account (Optional[str], optional): 账号(用于日志)。默认为None。
            
        Returns:
            Dict[str, Any]: 包含历史记录的字典
        """
        try:
            # 记录查询参数
            logger.info(f"查询密码历史记录 - 密码ID: {password_id}, 页码: {page}, 每页记录数: {page_size}")
            if start_time:
                logger.info(f"开始时间: {start_time}")
            if end_time:
                logger.info(f"结束时间: {end_time}")
            if ip_address:
                logger.info(f"IP地址: {ip_address}")
            
            # 检查password_history表是否存在
            check_table_sql = "SHOW TABLES LIKE 'password_history'"
            table_exists = db_manager.execute_query(check_table_sql)
            
            if not table_exists:
                logger.error("password_history表不存在")
                return {'total': 0, 'page': page, 'page_size': page_size, 'records': [], 'error': 'password_history表不存在'}
            
            # 检查是否有历史记录
            # 先获取所有历史记录的数量
            all_count_sql = "SELECT COUNT(*) as count FROM password_history"
            all_count_result = db_manager.execute_query(all_count_sql)
            total_history = all_count_result[0]['count'] if all_count_result else 0
            
            if total_history == 0:
                logger.warning("密码历史记录表中没有任何记录")
                return {'total': 0, 'page': page, 'page_size': page_size, 'records': [], 'warning': '密码历史记录表中没有任何记录'}
            
            # 构建查询条件 - 使用更灵活的方法
            where_conditions = []
            params = []
            
            # 检查ID是否存在于历史记录表中
            check_id_sql = "SELECT COUNT(*) as count FROM password_history WHERE password_id = %s"
            id_exists_result = db_manager.execute_query(check_id_sql, [password_id])
            id_exists = id_exists_result[0]['count'] > 0 if id_exists_result else False
            
            if id_exists:
                # ID存在，使用ID查询
                where_conditions.append("password_id = %s")
                params.append(password_id)
            elif ip_address:
                # ID不存在但有IP地址，尝试通过IP地址查询
                logger.warning(f"密码ID {password_id} 在历史记录中不存在，尝试使用IP地址 {ip_address} 查询")
                
                # 首先检查这个IP地址是否存在于历史记录中
                check_ip_sql = "SELECT DISTINCT password_id FROM password_history WHERE ip_address = %s"
                ip_ids_result = db_manager.execute_query(check_ip_sql, [ip_address])
                
                if ip_ids_result and len(ip_ids_result) > 0:
                    # 找到了IP地址对应的历史记录
                    history_ids = [row['password_id'] for row in ip_ids_result]
                    id_list_str = ", ".join(str(id) for id in history_ids)
                    
                    logger.info(f"发现IP地址 {ip_address} 对应的历史密码ID: {id_list_str}")
                    
                    # 使用IP地址查询
                    where_conditions.append("ip_address = %s")
                    params.append(ip_address)
                    
                    # 尝试更新当前密码记录在数据库中的ID关联
                    if len(history_ids) == 1:
                        logger.info(f"自动将当前密码ID {password_id} 更新为历史记录ID {history_ids[0]}")
                        password_id = history_ids[0]
                else:
                    # IP地址在历史记录中不存在
                    logger.warning(f"IP地址 {ip_address} 在历史记录中不存在")
                    where_conditions.append("password_id = %s")  # 使用一个不会匹配的条件
                    params.append(-1)
            else:
                # 没有可用的条件，返回警告
                logger.warning("无法查询历史记录：ID不存在且未提供IP地址")
                return {
                    'total': 0, 
                    'page': page, 
                    'page_size': page_size, 
                    'records': [],
                    'warning': '当前密码没有关联的历史记录。可能是新添加的密码，或者由于数据库变更导致历史关联丢失。'
                }
            
            # 添加时间范围条件
            if start_time:
                where_conditions.append("modify_time >= %s")
                params.append(start_time)
                
            if end_time:
                where_conditions.append("modify_time <= %s")
                params.append(end_time)
            
            # 构建WHERE子句
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 计算总记录数
            count_sql = f"SELECT COUNT(*) as count FROM password_history {where_clause}"
            count_result = db_manager.execute_query(count_sql, params)
            total = count_result[0]['count'] if count_result else 0
            
            logger.info(f"符合条件的总记录数: {total}")
            
            # 如果没有记录，提前返回
            if total == 0:
                logger.warning("未找到符合条件的历史记录")
                return {'total': 0, 'page': page, 'page_size': page_size, 'records': [], 
                       'warning': '未找到符合条件的历史记录'}
            
            # 分页查询
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT * FROM password_history 
                {where_clause}
                ORDER BY modify_time DESC
                LIMIT %s, %s
            """
            params.extend([offset, page_size])
            
            results = db_manager.execute_query(query_sql, params)
            
            # 记录查询结果
            logger.info(f"查询到 {len(results)} 条历史记录")
            if results and len(results) > 0:
                logger.info(f"第一条记录: {results[0]}")
            
            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'records': results
            }
            
        except Exception as e:
            logger.error(f"查询密码历史记录失败: {str(e)}")
            logger.debug(traceback.format_exc())
            return {'total': 0, 'page': page, 'page_size': page_size, 'records': [], 'error': str(e)}


# 创建全局实例
password_history_storage = PasswordHistoryStorage()


def get_user_storage() -> StorageBase:
    """
    获取用户存储实例
    
    Returns:
        StorageBase: 用户存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="users")


def get_password_storage() -> StorageBase:
    """
    获取密码存储实例
    
    Returns:
        StorageBase: 密码存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="passwords")


def get_user_settings_storage() -> StorageBase:
    """
    获取用户设置存储实例
    
    Returns:
        StorageBase: 用户设置存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="user_settings")


def get_remember_storage() -> StorageBase:
    """
    获取记住登录信息存储实例
    
    Returns:
        StorageBase: 记住登录信息存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="remember")


def get_password_history_storage() -> PasswordHistoryStorage:
    """
    获取密码历史记录存储实例
    
    Returns:
        PasswordHistoryStorage: 密码历史记录存储实例
    """
    return password_history_storage 