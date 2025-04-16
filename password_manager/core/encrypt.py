#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密模块，提供数据加密和解密功能（已移除加密逻辑，现在直接返回原始数据）
"""

import os
import logging
import threading
from config import ENCRYPTION_KEY_FILE, ENCRYPTION_ENCODING, ENCRYPTION_PREFIX, DATA_DIR

# 配置日志
logger = logging.getLogger(__name__)


class Encryptor:
    """
    加密器类，原本提供加密和解密功能
    
    已移除加密逻辑，现在直接返回原始数据，保持与原接口兼容。
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """
        单例模式，确保加密器只有一个实例，并保证线程安全
        
        Returns:
            Encryptor: 加密器实例
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Encryptor, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """
        初始化加密器，仅在首次创建实例时执行
        """
        with self.__class__._lock:
            if not self._initialized:
                # 移除实际密钥加载逻辑，仍创建简单的初始化结构
                self._initialized = True

    def _load_or_create_key(self):
        """
        原本加载或创建加密密钥的函数，现已简化
        
        Returns:
            bytes: 空密钥（不再使用）
        """
        logger.info("密钥加载函数已被调用，但加密功能已禁用")
        return b''

    def encrypt(self, data):
        """
        原本加密字符串数据的函数，现直接返回原始数据
        
        Args:
            data (str): 待处理的字符串
            
        Returns:
            str: 原始数据不变
        """
        # 直接返回原始数据，不进行加密
        return data

    def decrypt(self, encrypted_data):
        """
        原本解密字符串数据的函数，现直接返回原始数据
        
        Args:
            encrypted_data (str): 待处理的字符串
            
        Returns:
            str: 原始数据不变
        """
        # 直接返回原始数据，不进行解密
        return encrypted_data

    def is_encrypted(self, data):
        """
        原本检查字符串是否已加密的函数，现始终返回False
        
        Args:
            data (str): 要检查的字符串
            
        Returns:
            bool: 始终返回False，表示数据未加密
        """
        # 始终返回False，表示数据未加密
        return False


# 创建加密器实例
encryptor = Encryptor() 