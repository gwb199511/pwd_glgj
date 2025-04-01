#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户管理模块，提供用户注册、登录、验证等功能
"""

import logging
import os
import json
import time
import hashlib
import getpass
import threading
from typing import Tuple, Dict, Any, Optional, List, Union

from config import DATA_DIR
from database import Database
from encrypt import encryptor
from audit_log import AuditLogger, OP_TYPE_LOGIN, OP_TYPE_LOGOUT, OP_RESULT_SUCCESS, OP_RESULT_FAIL

# 配置日志
logger = logging.getLogger(__name__)
audit_logger = AuditLogger()

# 用户数据文件路径
USER_DATA_FILE = os.path.join(DATA_DIR, 'users.json')
REMEMBER_FILE = os.path.join(DATA_DIR, 'remember.json')

class UserManager:
    """
    用户管理类，处理用户注册和登录
    
    提供用户注册、登录验证等功能，管理用户凭证的加密存储和验证。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """
        单例模式，确保用户管理器只有一个实例
        
        Returns:
            UserManager: 用户管理器实例
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UserManager, cls).__new__(cls)
                cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        初始化用户管理器
        """
        # 导入存储接口
        import sys
        import os.path
        # 添加项目根目录到Python路径
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from data_storage import get_user_storage, get_remember_storage
        
        # 使用存储接口
        self.db = get_user_storage()
        self.remember_db = get_remember_storage()
        self.current_user = None

    def register(self, username: str, password: str) -> Tuple[bool, str]:
        """
        注册新用户
        
        Args:
            username (str): 用户名
            password (str): 密码
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        if not username or not password:
            return False, "用户名和密码不能为空"
            
        # 检查用户名是否已存在
        if self.db.exists(username):
            return False, "用户名已存在"
            
        # 加密密码
        encrypted_password = encryptor.encrypt(password)
        
        # 保存用户数据
        if self.db.set(username, encrypted_password):
            logger.info(f"用户 {username} 注册成功")
            return True, "注册成功"
        else:
            logger.error(f"用户 {username} 注册失败")
            return False, "注册失败，请稍后重试"

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        用户登录验证
        
        Args:
            username (str): 用户名
            password (str): 密码
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        if not username or not password:
            # 记录审计日志 - 登录失败（输入为空）
            audit_logger.log_operation(
                operation_type=OP_TYPE_LOGIN,
                result=OP_RESULT_FAIL,
                details="登录失败：用户名和密码不能为空",
                user=username if username else "未知用户",
                target="用户登录"
            )
            return False, "用户名和密码不能为空"
            
        # 获取存储的加密密码
        stored_password = self.db.get(username)
        
        if not stored_password:
            # 记录审计日志 - 登录失败（用户不存在）
            audit_logger.log_operation(
                operation_type=OP_TYPE_LOGIN,
                result=OP_RESULT_FAIL,
                details="登录失败：用户名不存在",
                user=username,
                target="用户登录"
            )
            return False, "用户名或密码错误"
            
        # 解密存储的密码
        decrypted_password = encryptor.decrypt(stored_password)
        
        # 比对密码
        if password == decrypted_password:
            self.current_user = username
            logger.info(f"用户 {username} 登录成功")
            
            # 记录审计日志 - 登录成功
            audit_logger.log_operation(
                operation_type=OP_TYPE_LOGIN,
                result=OP_RESULT_SUCCESS,
                details="用户登录成功",
                user=username,
                target="用户登录"
            )
            
            return True, "登录成功"
        else:
            logger.warning(f"用户 {username} 登录失败，密码错误")
            
            # 记录审计日志 - 登录失败（密码错误）
            audit_logger.log_operation(
                operation_type=OP_TYPE_LOGIN,
                result=OP_RESULT_FAIL,
                details="登录失败：密码错误",
                user=username,
                target="用户登录"
            )
            
            return False, "用户名或密码错误"

    def save_credentials(self, username: str, password: str) -> bool:
        """
        保存登录凭证（记住密码功能）
        
        Args:
            username (str): 用户名
            password (str): 密码
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        try:
            # 加密密码
            encrypted_password = encryptor.encrypt(password)
            
            # 直接操作数据库保存凭证，避免使用字典参数
            # 先删除旧记录
            from db_manager import db_manager
            
            # 确保数据库连接
            if not db_manager.is_connected():
                success, message = db_manager.connect()
                if not success:
                    logger.error(f"保存凭证时连接数据库失败: {message}")
                    return False
            
            # 清除旧记录
            db_manager.execute_update("DELETE FROM remember WHERE username = %s", (username,))
            
            # 添加过期时间
            from datetime import datetime, timedelta
            from config import REMEMBER_EXPIRE_DAYS
            expire_at = datetime.now() + timedelta(days=REMEMBER_EXPIRE_DAYS)
            
            # 插入新记录
            sql = "INSERT INTO remember (username, password, expire_at) VALUES (%s, %s, %s)"
            result = db_manager.execute_insert(sql, (username, encrypted_password, expire_at))
            
            if result > 0:
                logger.info(f"成功保存用户 {username} 的登录凭证")
                return True
            else:
                logger.error("保存凭证失败，数据库操作未返回有效ID")
                return False
        except Exception as e:
            logger.error(f"保存登录凭证时出错: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def clear_saved_credentials(self) -> bool:
        """
        清除保存的登录凭证
        
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        try:
            # 从数据库删除所有凭证记录
            from db_manager import db_manager
            
            # 确保数据库连接
            if not db_manager.is_connected():
                success, message = db_manager.connect()
                if not success:
                    logger.error(f"清除凭证时连接数据库失败: {message}")
                    return False
            
            result = db_manager.execute_update("DELETE FROM remember", ())
            
            if result >= 0:
                logger.info("已清除所有保存的登录凭证")
                return True
            else:
                logger.error("清除凭证失败，数据库操作返回错误")
                return False
        except Exception as e:
            logger.error(f"清除登录凭证时出错: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def load_saved_credentials(self) -> Optional[Dict[str, str]]:
        """
        加载保存的登录凭证
        
        Returns:
            Optional[Dict[str, str]]: 包含用户名和密码的字典，如果没有保存的凭证则返回None
        """
        try:
            # 从数据库获取最新的凭证
            from db_manager import db_manager
            db_manager.connect()
            
            # 获取未过期的记录
            from datetime import datetime
            current_time = datetime.now()
            
            # 直接通过列名获取结果
            sql = "SELECT username, password FROM remember WHERE expire_at > %s ORDER BY expire_at DESC LIMIT 1"
            results = db_manager.execute_query(sql, (current_time,))
            
            if not results or len(results) == 0:
                logger.warning("未找到有效的登录凭证")
                return None
                
            # 遍历结果，确保正确获取值
            for row in results:
                # 检查行数据类型
                if isinstance(row, dict):
                    # 如果返回的是字典，直接通过键获取值
                    username = row.get('username')
                    encrypted_password = row.get('password')
                else:
                    # 如果返回的是元组或列表，通过索引获取值
                    username = row[0] if len(row) > 0 else None
                    encrypted_password = row[1] if len(row) > 1 else None
                
                # 找到第一条有效记录即可
                if username and encrypted_password:
                    # 解密密码
                    password = encryptor.decrypt(encrypted_password)
                    
                    logger.info(f"成功加载用户 {username} 的登录凭证")
                    return {
                        "username": username,
                        "password": password
                    }
            
            logger.warning("找到记录但用户名或密码为空")
            return None
        except Exception as e:
            logger.error(f"加载登录凭证时出错: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def logout(self) -> None:
        """
        用户登出
        """
        # 获取当前用户，用于日志记录
        username = self.current_user or "未知用户"
        
        # 清除当前用户
        self.current_user = None
        logger.info("用户已登出")
        
        # 记录审计日志 - 登出
        audit_logger.log_operation(
            operation_type=OP_TYPE_LOGOUT,
            result=OP_RESULT_SUCCESS,
            details="用户登出系统",
            user=username,
            target="用户登出"
        )

    def get_current_user(self) -> Optional[str]:
        """
        获取当前登录的用户
        
        Returns:
            Optional[str]: 当前用户名，如果未登录则返回None
        """
        return self.current_user

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        修改用户密码
        
        Args:
            username (str): 用户名
            old_password (str): 旧密码
            new_password (str): 新密码
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        # 先验证旧密码
        login_success, _ = self.login(username, old_password)
        
        if not login_success:
            return False, "原密码错误"
            
        if not new_password:
            return False, "新密码不能为空"
            
        # 加密新密码
        encrypted_password = encryptor.encrypt(new_password)
        
        # 保存新密码
        if self.db.set(username, encrypted_password):
            logger.info(f"用户 {username} 密码修改成功")
            return True, "密码修改成功"
        else:
            logger.error(f"用户 {username} 密码修改失败")
            return False, "密码修改失败，请稍后重试"


# 创建用户管理器实例
user_manager = UserManager() 