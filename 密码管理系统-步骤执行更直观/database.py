#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库模块，提供JSON文件读写功能
"""

import os
import json
import logging
import traceback
from typing import Dict, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)


class Database:
    """
    数据库类，提供JSON文件的读写功能
    
    管理数据的持久化存储，提供数据的读取、保存、获取和更新操作。
    使用JSON作为存储格式，支持异常处理和错误恢复。
    """

    def __init__(self, file_path: str):
        """
        初始化数据库对象
        
        Args:
            file_path (str): JSON文件路径
        """
        self.file_path = file_path
        self.data = {}
        self.load_data()

    def load_data(self) -> Dict[str, Any]:
        """
        从文件加载数据
        
        Returns:
            Dict[str, Any]: 加载的数据字典
        """
        # 初始化为空字典，减少代码重复
        self.data = {}
        
        try:
            # 确保包含文件的目录存在
            directory = os.path.dirname(self.file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            # 如果文件存在，从文件读取数据
            if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
                with open(self.file_path, 'r', encoding='utf-8') as file:
                    self.data = json.load(file)
            else:
                # 如果文件不存在或为空，初始化为空字典并创建空文件
                with open(self.file_path, 'w', encoding='utf-8') as file:
                    json.dump(self.data, file, ensure_ascii=False, indent=4)
            
            return self.data
            
        except json.JSONDecodeError as e:
            # 明确处理JSON解析错误
            logger.error(f"解析JSON文件失败: {self.file_path}, 错误: {str(e)}")
            # 创建备份文件
            self._create_backup()
            
        except IOError as e:
            # 明确处理IO错误
            logger.error(f"读写文件时出错: {self.file_path}, 错误: {str(e)}")
            
        except Exception as e:
            # 处理其他未预见的错误
            logger.error(f"加载数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            
        # 在所有异常情况下，都返回空字典
        return self.data

    def save_data(self) -> bool:
        """
        保存数据到文件
        
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            # 确保包含文件的目录存在
            directory = os.path.dirname(self.file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            # 将数据写入文件
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(self.data, file, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"保存数据时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False

    def _create_backup(self) -> None:
        """
        创建数据文件的备份
        """
        if os.path.exists(self.file_path):
            backup_path = f"{self.file_path}.bak"
            try:
                with open(self.file_path, 'r', encoding='utf-8') as src_file:
                    with open(backup_path, 'w', encoding='utf-8') as backup_file:
                        backup_file.write(src_file.read())
                logger.info(f"已创建数据文件备份: {backup_path}")
            except Exception as e:
                logger.error(f"创建备份时出错: {str(e)}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取指定键的数据
        
        Args:
            key (str): 键名
            default (Any, optional): 默认值，当键不存在时返回。默认为None
            
        Returns:
            Any: 键对应的值，或者默认值（如果键不存在）
        """
        return self.data.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有数据
        
        Returns:
            Dict[str, Any]: 完整的数据字典
        """
        return self.data

    def set(self, key: str, value: Any) -> bool:
        """
        设置指定键的值
        
        Args:
            key (str): 键名
            value (Any): 值
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        self.data[key] = value
        return self.save_data()

    def delete(self, key: str) -> bool:
        """
        删除指定键
        
        Args:
            key (str): 要删除的键名
            
        Returns:
            bool: 删除成功返回True，键不存在或操作失败返回False
        """
        if key in self.data:
            del self.data[key]
            return self.save_data()
        return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key (str): 要检查的键名
            
        Returns:
            bool: 如果键存在返回True，否则返回False
        """
        return key in self.data 