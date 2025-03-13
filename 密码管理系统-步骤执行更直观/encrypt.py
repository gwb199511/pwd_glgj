#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密模块，提供数据加密和解密功能
"""

import os
import base64
import logging
import threading
from cryptography.fernet import Fernet, InvalidToken
from config import ENCRYPTION_KEY_FILE, ENCRYPTION_ENCODING, ENCRYPTION_PREFIX, DATA_DIR

# 配置日志
logger = logging.getLogger(__name__)


class Encryptor:
    """
    加密器类，提供加密和解密功能

    使用Fernet对称加密算法（基于AES-128-CBC）实现数据的加密和解密，
    自动管理加密密钥的生成和存储。
    """

    _instance = None
    _lock = threading.Lock()  # 添加类级别的锁，确保线程安全
    _initialized = False
    
    def __new__(cls):
        """
        单例模式，确保加密器只有一个实例，并保证线程安全
        
        Returns:
            Encryptor: 加密器实例
        """
        with cls._lock:  # 使用锁确保线程安全
            if cls._instance is None:
                cls._instance = super(Encryptor, cls).__new__(cls)
                # 仅创建实例，初始化在__init__中完成
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """
        初始化加密器，仅在首次创建实例时执行
        """
        # 使用锁确保线程安全
        with self.__class__._lock:
            if not self._initialized:
                self._key = self._load_or_create_key()
                self._fernet = Fernet(self._key)
                self._initialized = True

    def _load_or_create_key(self):
        """
        加载或创建加密密钥
        
        如果密钥文件存在，则从文件加载密钥；
        如果密钥文件不存在或为空，则生成新的密钥并保存到文件。
        
        Returns:
            bytes: 加密密钥
        """
        try:
            # 确保数据目录存在
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR)
                
            if os.path.exists(ENCRYPTION_KEY_FILE) and os.path.getsize(ENCRYPTION_KEY_FILE) > 0:
                with open(ENCRYPTION_KEY_FILE, 'rb') as key_file:
                    key = key_file.read()
                    return key
            else:
                # 生成新密钥
                key = Fernet.generate_key()
                with open(ENCRYPTION_KEY_FILE, 'wb') as key_file:
                    key_file.write(key)
                return key
        except Exception as e:
            logger.error(f"加载或创建密钥时出错: {str(e)}")
            # 在密钥加载失败的情况下，生成临时密钥（不保存）
            return Fernet.generate_key()

    def encrypt(self, data):
        """
        加密字符串数据
        
        Args:
            data (str): 待加密的字符串
            
        Returns:
            str: 加密后的字符串
        """
        if not data:
            return data
            
        # 如果数据已经加密，直接返回
        if self.is_encrypted(data):
            return data
            
        try:
            # 将字符串转换为字节
            data_bytes = data.encode(ENCRYPTION_ENCODING)
            # 使用Fernet加密
            encrypted_bytes = self._fernet.encrypt(data_bytes)
            # 将加密后的字节转换回字符串
            encrypted_str = encrypted_bytes.decode(ENCRYPTION_ENCODING)
            return encrypted_str
        except Exception as e:
            logger.error(f"加密数据时出错: {str(e)}")
            # 在加密失败的情况下，返回原始数据
            return data

    def decrypt(self, encrypted_data):
        """
        解密字符串数据
        
        Args:
            encrypted_data (str): 加密的字符串
            
        Returns:
            str: 解密后的字符串
        """
        if not encrypted_data:
            return encrypted_data
            
        # 如果数据未加密，直接返回
        if not self.is_encrypted(encrypted_data):
            return encrypted_data
            
        try:
            # 将加密字符串转换为字节
            encrypted_bytes = encrypted_data.encode(ENCRYPTION_ENCODING)
            # 使用Fernet解密
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            # 将解密后的字节转换回字符串
            decrypted_str = decrypted_bytes.decode(ENCRYPTION_ENCODING)
            return decrypted_str
        except InvalidToken:
            logger.warning(f"无效的加密令牌，无法解密数据")
            return encrypted_data
        except Exception as e:
            logger.error(f"解密数据时出错: {str(e)}")
            # 在解密失败的情况下，返回原始数据
            return encrypted_data

    def is_encrypted(self, data):
        """
        检查字符串是否已加密
        
        Args:
            data (str): 要检查的字符串
            
        Returns:
            bool: 如果字符串已加密则返回True，否则返回False
        """
        if not isinstance(data, str):
            return False
            
        # Fernet加密的数据通常以特定前缀开头
        return data.startswith(ENCRYPTION_PREFIX)


# 创建加密器实例
encryptor = Encryptor() 