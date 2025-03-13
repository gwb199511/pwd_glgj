#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户管理模块，提供用户注册和登录功能
"""

import logging
import os
from typing import Tuple, Dict, Any, Optional

from config import USER_DATA_FILE, REMEMBER_FILE
from database import Database
from encrypt import encryptor

# 配置日志
logger = logging.getLogger(__name__)


class UserManager:
    """
    用户管理类，处理用户注册和登录
    
    提供用户注册、登录验证等功能，管理用户凭证的加密存储和验证。
    """

    _instance = None

    def __new__(cls):
        """
        单例模式，确保用户管理器只有一个实例
        
        Returns:
            UserManager: 用户管理器实例
        """
        if cls._instance is None:
            cls._instance = super(UserManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        初始化用户管理器
        """
        self.db = Database(USER_DATA_FILE)
        self.remember_db = Database(REMEMBER_FILE)
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
            return False, "用户名和密码不能为空"
            
        # 获取存储的加密密码
        stored_password = self.db.get(username)
        
        if not stored_password:
            return False, "用户名或密码错误"
            
        # 解密存储的密码
        decrypted_password = encryptor.decrypt(stored_password)
        
        # 比对密码
        if password == decrypted_password:
            self.current_user = username
            logger.info(f"用户 {username} 登录成功")
            return True, "登录成功"
        else:
            logger.warning(f"用户 {username} 登录失败，密码错误")
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
            
            # 保存凭证
            credentials = {
                "username": username,
                "password": encrypted_password
            }
            
            return self.remember_db.set("credentials", credentials)
        except Exception as e:
            logger.error(f"保存登录凭证时出错: {str(e)}")
            return False

    def clear_saved_credentials(self) -> bool:
        """
        清除保存的登录凭证
        
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        return self.remember_db.delete("credentials")

    def load_saved_credentials(self) -> Optional[Dict[str, str]]:
        """
        加载保存的登录凭证
        
        Returns:
            Optional[Dict[str, str]]: 包含用户名和密码的字典，如果没有保存的凭证则返回None
        """
        try:
            credentials = self.remember_db.get("credentials")
            
            if not credentials:
                return None
                
            # 解密密码
            username = credentials.get("username")
            encrypted_password = credentials.get("password")
            
            if not username or not encrypted_password:
                return None
                
            password = encryptor.decrypt(encrypted_password)
            
            return {
                "username": username,
                "password": password
            }
        except Exception as e:
            logger.error(f"加载登录凭证时出错: {str(e)}")
            return None

    def logout(self) -> None:
        """
        用户登出
        """
        self.current_user = None
        logger.info("用户已登出")

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