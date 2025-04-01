#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理模块，提供MySQL连接管理和配置功能
"""

import os
import json
import logging
import threading
import traceback
from typing import Dict, Any, Optional, List, Tuple

import pymysql
from pymysql.cursors import DictCursor

from config import DATA_DIR, DB_CONFIG_FILE, DEFAULT_MYSQL_CONFIG, STORAGE_TYPE

# 配置日志
logger = logging.getLogger(__name__)


class DBManager:
    """
    数据库管理类，提供MySQL连接管理和配置功能
    
    负责管理数据库连接、配置读写和表结构初始化。
    同时提供判断存储模式和数据迁移的功能。
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """
        单例模式，确保数据库管理器只有一个实例
        
        Returns:
            DBManager: 数据库管理器实例
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DBManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """初始化数据库管理器"""
        with self.__class__._lock:
            if not self._initialized:
                self.connection = None
                self.config = self._load_config()
                self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载数据库配置
        
        Returns:
            Dict[str, Any]: 数据库配置字典
        """
        try:
            if os.path.exists(DB_CONFIG_FILE):
                with open(DB_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果配置文件不存在，使用默认配置
                config = DEFAULT_MYSQL_CONFIG.copy()
                # 保存默认配置
                self._save_config(config)
                return config
        except Exception as e:
            logger.error(f"加载数据库配置时出错: {str(e)}")
            return DEFAULT_MYSQL_CONFIG.copy()
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存数据库配置
        
        Args:
            config (Dict[str, Any]): 数据库配置字典
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(DB_CONFIG_FILE), exist_ok=True)
            
            with open(DB_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"保存数据库配置时出错: {str(e)}")
            return False
    
    def connect(self) -> Tuple[bool, str]:
        """
        连接到MySQL数据库
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if self.connection and self.connection.open:
                # 如果已经有连接，先关闭
                self.connection.close()
            
            # 创建新连接
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            
            logger.info(f"已连接到MySQL数据库: {self.config['host']}:{self.config['port']}/{self.config['database']}")
            return True, "数据库连接成功"
        except pymysql.MySQLError as e:
            error_message = f"连接MySQL数据库时出错: {str(e)}"
            logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"连接数据库时出现未知错误: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return False, error_message
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        try:
            if self.connection and self.connection.open:
                self.connection.close()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {str(e)}")
    
    def is_connected(self) -> bool:
        """
        检查是否已连接到数据库
        
        Returns:
            bool: 如果已连接返回True，否则返回False
        """
        try:
            if self.connection and self.connection.open:
                # 执行简单查询以验证连接
                with self.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None and result[0] == 1
            return False
        except Exception:
            return False
    
    def update_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        更新数据库配置
        
        Args:
            config (Dict[str, Any]): 新的数据库配置
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 验证配置
            required_keys = ['host', 'port', 'user', 'password', 'database']
            for key in required_keys:
                if key not in config:
                    return False, f"配置缺少必要字段: {key}"
            
            # 保存配置
            self.config = config
            if not self._save_config(config):
                return False, "保存配置文件失败"
            
            # 尝试连接
            return self.connect()
        except Exception as e:
            error_message = f"更新数据库配置时出错: {str(e)}"
            logger.error(error_message)
            return False, error_message
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前数据库配置
        
        Returns:
            Dict[str, Any]: 数据库配置字典
        """
        return self.config.copy()
    
    def create_database(self) -> Tuple[bool, str]:
        """
        创建数据库
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 连接到MySQL服务器（不指定数据库）
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                charset='utf8mb4'
            )
            
            database_name = self.config['database']
            with conn.cursor() as cursor:
                # 检查数据库是否存在
                cursor.execute(f"SHOW DATABASES LIKE '{database_name}'")
                result = cursor.fetchone()
                
                if not result:
                    # 创建数据库
                    cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    logger.info(f"数据库 {database_name} 已创建")
                else:
                    logger.info(f"数据库 {database_name} 已存在")
            
            conn.close()
            return True, f"数据库 {database_name} 准备就绪"
        except pymysql.MySQLError as e:
            error_message = f"创建数据库时出错: {str(e)}"
            logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"创建数据库时出现未知错误: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return False, error_message
    
    def initialize_tables(self) -> Tuple[bool, str]:
        """
        初始化数据库表结构
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 确保连接到数据库
            if not self.is_connected():
                success, message = self.connect()
                if not success:
                    return False, message
            
            # 定义表结构SQL
            tables_sql = {
                "users": """
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) NOT NULL UNIQUE,
                        password VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "passwords": """
                    CREATE TABLE IF NOT EXISTS passwords (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        owner VARCHAR(50) NOT NULL,
                        project_name VARCHAR(100) NOT NULL,
                        func_desc VARCHAR(100),
                        ip_address VARCHAR(50) NOT NULL,
                        account VARCHAR(50) NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        area VARCHAR(50),
                        network_type VARCHAR(50),
                        other_info TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX (owner)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "remember": """
                    CREATE TABLE IF NOT EXISTS remember (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expire_at TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "audit_logs": """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        log_type VARCHAR(20) NOT NULL,
                        operation_type VARCHAR(20) NOT NULL,
                        result VARCHAR(10) NOT NULL,
                        details TEXT,
                        user VARCHAR(50),
                        target VARCHAR(100),
                        ip_address VARCHAR(50),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX (log_type, operation_type, result)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "user_settings": """
                    CREATE TABLE IF NOT EXISTS user_settings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) NOT NULL,
                        setting_key VARCHAR(100) NOT NULL,
                        setting_value TEXT,
                        UNIQUE KEY (username, setting_key)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "db_config": """
                    CREATE TABLE IF NOT EXISTS db_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        host VARCHAR(100) NOT NULL,
                        port INT NOT NULL DEFAULT 3306,
                        user VARCHAR(50) NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        database_name VARCHAR(50) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            }
            
            # 创建表
            with self.connection.cursor() as cursor:
                for table_name, sql in tables_sql.items():
                    cursor.execute(sql)
                    logger.info(f"表 {table_name} 已初始化")
            
            self.connection.commit()
            return True, "数据库表结构初始化完成"
        except pymysql.MySQLError as e:
            error_message = f"初始化表结构时出错: {str(e)}"
            logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"初始化表结构时出现未知错误: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return False, error_message
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试数据库连接
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 创建临时连接以测试配置
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                charset='utf8mb4'
            )
            
            # 尝试查询服务器信息
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
            
            conn.close()
            return True, f"连接成功，MySQL版本: {version}"
        except pymysql.MySQLError as e:
            error_message = f"测试连接时出错: {str(e)}"
            logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"测试连接时出现未知错误: {str(e)}"
            logger.error(error_message)
            return False, error_message
    
    def execute_query(self, sql: str, params = None) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        
        Args:
            sql (str): SQL查询语句
            params: 查询参数，可以是元组、列表或None
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        try:
            if not self.is_connected():
                self.connect()
            
            # 参数处理
            if params is None:
                params = ()
            elif isinstance(params, dict):
                # 将字典转换为JSON字符串，避免SQL执行错误
                json_value = json.dumps(params, ensure_ascii=False)
                logger.warning(f"执行SQL查询时参数为字典类型，已转换为JSON字符串: {json_value}")
                # 使用固定值，依赖调用方确保SQL语句兼容
                params = (json_value,)
            
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"执行查询时出错: {str(e)}")
            return []
    
    def execute_update(self, sql: str, params = None) -> int:
        """
        执行SQL更新（插入、更新、删除）
        
        Args:
            sql (str): SQL更新语句
            params: 更新参数，可以是元组、列表或None
            
        Returns:
            int: 受影响的行数，错误时返回-1
        """
        try:
            if not self.is_connected():
                self.connect()
            
            # 参数处理
            if params is None:
                params = ()
            elif isinstance(params, dict):
                # 将字典转换为JSON字符串，避免SQL执行错误
                json_value = json.dumps(params, ensure_ascii=False)
                logger.warning(f"执行SQL更新时参数为字典类型，已转换为JSON字符串: {json_value}")
                # 使用固定值，依赖调用方确保SQL语句兼容
                params = (json_value,)
            
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                self.connection.commit()
                return affected_rows
        except Exception as e:
            logger.error(f"执行更新时出错: {str(e)}")
            self.connection.rollback()
            return -1
    
    def execute_insert(self, sql: str, params = None) -> int:
        """
        执行SQL插入
        
        Args:
            sql (str): SQL插入语句
            params: 插入参数, 可以是元组、列表或None
            
        Returns:
            int: 最后插入的ID，错误时返回-1
        """
        try:
            if not self.is_connected():
                self.connect()
            
            # 参数处理
            if params is None:
                params = ()
            elif isinstance(params, dict):
                # 将字典转换为JSON字符串，避免SQL执行错误
                json_value = json.dumps(params, ensure_ascii=False)
                logger.warning(f"执行SQL时参数为字典类型，已转换为JSON字符串: {json_value}")
                # 使用固定值，依赖调用方确保SQL语句兼容
                params = (json_value,)
            
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                self.connection.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"执行插入时出错: {str(e)}")
            self.connection.rollback()
            return -1


# 创建全局实例
db_manager = DBManager() 