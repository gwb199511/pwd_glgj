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
import time
from typing import Dict, Any, Optional, List, Tuple

import pymysql
from pymysql.cursors import DictCursor

from config import DATA_DIR, DB_CONFIG_FILE, DEFAULT_MYSQL_CONFIG, STORAGE_TYPE

# 配置日志
logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    数据库连接池类，用于管理和复用数据库连接
    
    提供连接的创建、获取、释放和维护功能。
    """
    
    def __init__(self, config, max_connections=10, connection_timeout=60):
        """
        初始化连接池
        
        Args:
            config (Dict): 数据库配置
            max_connections (int): 最大连接数
            connection_timeout (int): 连接超时时间（秒）
        """
        self.config = config
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.connections = []
        self.in_use = {}
        self.lock = threading.Lock()
        self.last_connection_time = 0  # 上次创建连接的时间
        self.connection_interval = 0.1  # 连接创建的最小间隔时间（秒）
        self.last_log_time = 0  # 上次日志记录时间
        self.log_interval = 3.0  # 日志输出的最小间隔（秒）
        
        # 预创建连接
        self._create_initial_connections()
    
    def _create_initial_connections(self, initial_count=2):
        """
        预创建一些连接以提高初始性能
        
        Args:
            initial_count (int): 初始连接数
        """
        try:
            for _ in range(min(initial_count, self.max_connections)):
                conn = self._create_connection()
                if conn:
                    self.connections.append(conn)
                    self.last_connection_time = time.time()
        except Exception as e:
            logger.error(f"预创建连接失败: {str(e)}")
    
    def get_connection(self):
        """
        获取一个数据库连接
        
        Returns:
            pymysql.Connection: 数据库连接
        """
        with self.lock:
            current_time = time.time()
            
            # 1. 首先尝试从空闲连接中获取
            for conn in self.connections:
                if conn not in self.in_use:
                    # 找到一个空闲连接
                    try:
                        # 检查连接是否有效
                        if self._check_connection(conn):
                            # 有效连接，标记为使用中
                            self.in_use[conn] = current_time
                            return conn
                        else:
                            # 连接无效，关闭并移除
                            self._close_connection(conn)
                    except:
                        # 连接出错，尝试移除
                        self._close_connection(conn)
            
            # 2. 如果没有空闲连接，检查超时连接
            for conn in list(self.in_use.keys()):
                if current_time - self.in_use[conn] > self.connection_timeout:
                    # 找到一个超时连接，尝试重用
                    try:
                        if self._check_connection(conn):
                            # 更新使用时间
                            self.in_use[conn] = current_time
                            return conn
                        else:
                            # 连接无效，关闭并移除
                            self._close_connection(conn)
                    except:
                        # 连接出错，尝试移除
                        self._close_connection(conn)
            
            # 3. 如果未达到最大连接数，创建新连接
            if len(self.connections) < self.max_connections:
                # 检查创建连接的时间间隔
                if current_time - self.last_connection_time >= self.connection_interval:
                    try:
                        conn = self._create_connection()
                        if conn:
                            self.connections.append(conn)
                            self.in_use[conn] = current_time
                            self.last_connection_time = current_time
                            
                            # 控制日志频率
                            if current_time - self.last_log_time >= self.log_interval:
                                logger.info(f"已连接到MySQL数据库: {self.config['host']}:{self.config['port']}/{self.config['database']}")
                                self.last_log_time = current_time
                            
                            return conn
                    except Exception as e:
                        if current_time - self.last_log_time >= self.log_interval:
                            logger.error(f"创建数据库连接失败: {str(e)}")
                            self.last_log_time = current_time
                        return None
                else:
                    # 连接创建过于频繁，等待一小段时间
                    time.sleep(0.01)
                    return self.get_connection()
            
            # 4. 已达到最大连接数，找到最早的使用中连接
            if self.in_use:
                oldest_time = min(self.in_use.values())
                for conn, use_time in self.in_use.items():
                    if use_time == oldest_time:
                        # 再次检查该连接是否有效
                        if self._check_connection(conn):
                            # 更新使用时间并返回
                            self.in_use[conn] = current_time
                            logger.debug("已重用最早的连接")
                            return conn
                        else:
                            # 连接无效，移除并尝试创建新连接
                            self._close_connection(conn)
                            return self.get_connection()
            
            # 最后，如果连接池已满且无法重用连接，创建临时连接
            logger.debug("连接池已满，创建临时连接")
            try:
                conn = self._create_connection()
                # 不添加到连接池，使用后会自动关闭
                if conn:
                    if current_time - self.last_log_time >= self.log_interval:
                        logger.info(f"已创建临时MySQL连接: {self.config['host']}:{self.config['port']}/{self.config['database']}")
                        self.last_log_time = current_time
                    return conn
            except Exception as e:
                if current_time - self.last_log_time >= self.log_interval:
                    logger.error(f"创建临时数据库连接失败: {str(e)}")
                    self.last_log_time = current_time
                return None
    
    def release_connection(self, conn):
        """
        释放一个数据库连接
        
        Args:
            conn (pymysql.Connection): 要释放的连接
        """
        with self.lock:
            # 如果连接在使用中列表里，移除它
            if conn in self.in_use:
                del self.in_use[conn]
            
            # 检查连接是否在连接池中
            in_pool = conn in self.connections
            
            # 如果不在连接池中且连接池未满，将其添加到连接池
            if not in_pool and len(self.connections) < self.max_connections:
                # 确保连接有效
                if self._check_connection(conn):
                    self.connections.append(conn)
                else:
                    # 无效连接，关闭它
                    try:
                        if conn.open:
                            conn.close()
                    except:
                        pass
            elif not in_pool:
                # 不在连接池中且连接池已满，关闭该临时连接
                try:
                    if conn.open:
                        conn.close()
                except:
                    pass
    
    def _create_connection(self):
        """
        创建数据库连接
        
        Returns:
            pymysql.Connection: 新创建的数据库连接
        """
        return pymysql.connect(
            host=self.config['host'],
            port=self.config['port'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            charset='utf8mb4',
            cursorclass=DictCursor
        )
    
    def _check_connection(self, conn):
        """
        检查连接是否有效
        
        Args:
            conn (pymysql.Connection): 要检查的连接
            
        Returns:
            bool: 连接是否有效
        """
        try:
            if not conn.open:
                return False
            
            # 执行简单查询测试连接
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
        except:
            return False
    
    def _close_connection(self, conn):
        """
        关闭并移除一个连接
        
        Args:
            conn (pymysql.Connection): 要关闭的连接
        """
        try:
            if conn in self.in_use:
                del self.in_use[conn]
            
            if conn in self.connections:
                self.connections.remove(conn)
            
            if conn.open:
                conn.close()
        except:
            pass
    
    def close_all(self):
        """关闭所有连接"""
        with self.lock:
            for conn in self.connections:
                try:
                    if conn.open:
                        conn.close()
                except:
                    pass
            
            self.connections = []
            self.in_use = {}
    
    def cleanup_idle_connections(self, idle_timeout=300):
        """
        清理空闲连接
        
        Args:
            idle_timeout (int): 空闲超时时间（秒）
        """
        with self.lock:
            current_time = time.time()
            to_remove = []
            
            for conn in self.connections:
                # 检查连接是否空闲
                if conn not in self.in_use or current_time - self.in_use.get(conn, 0) > idle_timeout:
                    to_remove.append(conn)
            
            # 关闭并移除空闲连接
            for conn in to_remove:
                self._close_connection(conn)


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
                # 初始化连接池
                self.connection_pool = ConnectionPool(self.config)
                # 启动后台线程定期清理空闲连接
                self._start_connection_cleanup()
                self._initialized = True
    
    def _start_connection_cleanup(self):
        """启动后台线程定期清理空闲连接"""
        def cleanup_task():
            while True:
                time.sleep(60)  # 每分钟检查一次
                try:
                    self.connection_pool.cleanup_idle_connections()
                except:
                    pass
        
        # 创建后台线程
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
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
        连接到MySQL数据库（保留向后兼容性）
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 从连接池获取连接
            conn = self.connection_pool.get_connection()
            if conn:
                self.connection = conn
                logger.info(f"已连接到MySQL数据库: {self.config['host']}:{self.config['port']}/{self.config['database']}")
                return True, "数据库连接成功"
            else:
                error_message = "无法从连接池获取连接"
                logger.error(error_message)
                return False, error_message
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
        """断开数据库连接（保留向后兼容性）"""
        if self.connection:
            self.connection_pool.release_connection(self.connection)
            self.connection = None
    
    def is_connected(self) -> bool:
        """
        检查是否已连接到数据库
        
        Returns:
            bool: 如果已连接返回True，否则返回False
        """
        if not self.connection:
            return False
        
        try:
            return self.connection_pool._check_connection(self.connection)
        except:
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
            
            # 关闭现有连接池
            if hasattr(self, 'connection_pool'):
                self.connection_pool.close_all()
            
            # 创建新连接池
            self.connection_pool = ConnectionPool(config)
            self.connection = None
            
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
            # 从连接池获取连接
            conn = self.connection_pool.get_connection()
            if not conn:
                return False, "无法获取数据库连接"
            
            # 尝试查询服务器信息
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
            
            # 释放连接
            self.connection_pool.release_connection(conn)
            
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
        conn = None
        try:
            # 获取连接
            if not self.is_connected():
                conn = self.connection_pool.get_connection()
            else:
                conn = self.connection
            
            if not conn:
                logger.error("执行查询时无法获取数据库连接")
                return []
            
            # 参数处理
            if params is None:
                params = ()
            elif isinstance(params, dict):
                # 将字典转换为JSON字符串
                json_value = json.dumps(params, ensure_ascii=False)
                logger.warning(f"执行SQL查询时参数为字典类型，已转换为JSON字符串: {json_value}")
                params = (json_value,)
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"执行查询时出错: {str(e)}")
            return []
        finally:
            # 如果是新获取的连接，释放它
            if conn and conn != self.connection:
                self.connection_pool.release_connection(conn)
    
    def execute_update(self, sql: str, params = None) -> int:
        """
        执行SQL更新（插入、更新、删除）
        
        Args:
            sql (str): SQL更新语句
            params: 更新参数，可以是元组、列表或None
            
        Returns:
            int: 受影响的行数，错误时返回-1
        """
        conn = None
        try:
            # 获取连接
            if not self.is_connected():
                conn = self.connection_pool.get_connection()
            else:
                conn = self.connection
            
            if not conn:
                logger.error("执行更新时无法获取数据库连接")
                return -1
            
            # 参数处理
            if params is None:
                params = ()
            elif isinstance(params, dict):
                # 将字典转换为JSON字符串
                json_value = json.dumps(params, ensure_ascii=False)
                logger.warning(f"执行SQL更新时参数为字典类型，已转换为JSON字符串: {json_value}")
                params = (json_value,)
            
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                conn.commit()
                return affected_rows
        except Exception as e:
            logger.error(f"执行更新时出错: {str(e)}")
            if conn:
                conn.rollback()
            return -1
        finally:
            # 如果是新获取的连接，释放它
            if conn and conn != self.connection:
                self.connection_pool.release_connection(conn)
    
    def execute_insert(self, sql: str, params = None) -> int:
        """
        执行SQL插入
        
        Args:
            sql (str): SQL插入语句
            params: 插入参数, 可以是元组、列表或None
            
        Returns:
            int: 最后插入的ID，错误时返回-1
        """
        conn = None
        try:
            # 获取连接
            if not self.is_connected():
                conn = self.connection_pool.get_connection()
            else:
                conn = self.connection
            
            if not conn:
                logger.error("执行插入时无法获取数据库连接")
                return -1
            
            # 参数处理
            if params is None:
                params = ()
            elif isinstance(params, dict):
                # 将字典转换为JSON字符串
                json_value = json.dumps(params, ensure_ascii=False)
                logger.warning(f"执行SQL插入时参数为字典类型，已转换为JSON字符串: {json_value}")
                params = (json_value,)
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"执行插入时出错: {str(e)}")
            if conn:
                conn.rollback()
            return -1
        finally:
            # 如果是新获取的连接，释放它
            if conn and conn != self.connection:
                self.connection_pool.release_connection(conn)


# 创建全局实例
db_manager = DBManager() 