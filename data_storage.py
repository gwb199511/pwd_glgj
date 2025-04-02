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
from db_manager import db_manager

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
                    from db_manager import db_manager
                    
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
            
            # 根据不同表类型处理数据
            if self.table_name == "users":
                # 删除原有数据
                db_manager.execute_update(f"DELETE FROM {self.table_name} WHERE username = %s", (key,))
                
                # 插入新数据
                sql = f"INSERT INTO {self.table_name} (username, password) VALUES (%s, %s)"
                result = db_manager.execute_insert(sql, (key, value))
                return result > 0
                
            elif self.table_name == "passwords":
                # 删除原有数据
                db_manager.execute_update(f"DELETE FROM {self.table_name} WHERE owner = %s", (key,))
                
                # 插入新数据
                success = True
                for record in value:
                    if len(record) < 8:  # 确保记录格式正确
                        continue
                    
                    sql = """
                        INSERT INTO passwords 
                        (owner, project_name, func_desc, ip_address, account, password, area, network_type, other_info)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    result = db_manager.execute_insert(sql, (
                        key,           # owner
                        record[0],     # project_name
                        record[1],     # func_desc
                        record[2],     # ip_address
                        record[3],     # account
                        record[4],     # password
                        record[5],     # area
                        record[6],     # network_type
                        record[7]      # other_info
                    ))
                    
                    if result <= 0:
                        success = False
                
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
        # 从数据库加载所有数据
        self.load()
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
        # 从配置中获取存储类型，但始终返回mysql
        # 这样即使配置文件被修改，也会保持使用MySQL
        return "mysql"


def get_user_storage() -> StorageBase:
    """
    获取用户存储实例
    
    Returns:
        StorageBase: 用户MySQL存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="users")


def get_password_storage() -> StorageBase:
    """
    获取密码存储实例
    
    Returns:
        StorageBase: 密码MySQL存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="passwords")


def get_user_settings_storage() -> StorageBase:
    """
    获取用户设置存储实例
    
    Returns:
        StorageBase: 用户设置MySQL存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="user_settings")


def get_remember_storage() -> StorageBase:
    """
    获取记住登录信息的存储实例
    
    Returns:
        StorageBase: 记住登录信息的MySQL存储实例
    """
    return StorageFactory.create_storage("mysql", table_name="remember") 