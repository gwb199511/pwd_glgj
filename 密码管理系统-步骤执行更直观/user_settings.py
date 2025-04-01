#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户设置模块，管理用户个性化配置
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# 导入存储接口
import sys
import os.path
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_storage import get_user_settings_storage

# 配置日志
logger = logging.getLogger(__name__)

class UserSettings:
    """
    用户设置类，管理用户的偏好设置
    
    提供保存和加载用户设置的功能，包括引导状态、界面设置等。
    """
    
    _instance = None
    
    def __new__(cls):
        """
        单例模式，确保设置管理器只有一个实例
        
        Returns:
            UserSettings: 设置管理器实例
        """
        if cls._instance is None:
            cls._instance = super(UserSettings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        """初始化用户设置管理器"""
        if not self._initialized:
            # 使用存储接口
            self._storage = get_user_settings_storage()
            self._settings = {}
            self._load_settings()
            self._initialized = True
            
    def _load_settings(self):
        """从存储加载设置"""
        try:
            # 从存储接口加载数据
            self._settings = self._storage.get_all()
            if not self._settings:
                self._settings = self._get_default_settings()
                self._save_settings()
        except Exception as e:
            logger.error(f"加载用户设置时出错: {str(e)}")
            self._settings = self._get_default_settings()
            
    def _save_settings(self):
        """保存设置到存储"""
        try:
            # 使用存储接口保存数据
            self._storage.save(self._settings)
        except Exception as e:
            logger.error(f"保存用户设置时出错: {str(e)}")
            
    def _get_default_settings(self) -> Dict[str, Any]:
        """获取默认设置"""
        return {
            # 引导设置
            "guides": {
                "password_update_guided": False,  # 密码更新引导是否已完成
            },
            # 界面设置
            "ui": {
                "table_font_size": 9,
                "show_grid_lines": True,
                "auto_resize_columns": True,
            },
            # 密码设置
            "password": {
                "default_length": 16,
                "include_special_chars": True,
                "auto_generate_for_new": False,
            }
        }
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取设置值
        
        Args:
            key (str): 设置键名，支持点号分隔的嵌套键
            default (Any, optional): 默认值，当键不存在时返回
            
        Returns:
            Any: 设置值
        """
        try:
            # 支持使用点号获取嵌套键
            parts = key.split('.')
            value = self._settings
            for part in parts:
                value = value.get(part, {})
                
            # 如果最后得到的是空字典，说明键不存在
            if value == {} and len(parts) > 0:
                return default
                
            return value
        except:
            return default
            
    def set(self, key: str, value: Any) -> bool:
        """
        设置值
        
        Args:
            key (str): 设置键名，支持点号分隔的嵌套键
            value (Any): 要设置的值
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        try:
            # 支持使用点号设置嵌套键
            parts = key.split('.')
            
            # 特殊情况处理：根键
            if len(parts) == 1:
                self._settings[parts[0]] = value
                self._save_settings()
                return True
                
            # 常规情况：嵌套键
            config = self._settings
            for i, part in enumerate(parts[:-1]):
                if part not in config:
                    config[part] = {}
                config = config[part]
                
            config[parts[-1]] = value
            self._save_settings()
            return True
        except Exception as e:
            logger.error(f"设置用户配置时出错: {str(e)}")
            return False
            
    def is_guide_completed(self, guide_key: str) -> bool:
        """
        检查特定引导是否已完成
        
        Args:
            guide_key (str): 引导键名
            
        Returns:
            bool: 如果引导已完成则返回True，否则返回False
        """
        return self.get(f"guides.{guide_key}_guided", False)
        
    def mark_guide_completed(self, guide_key: str) -> None:
        """
        标记特定引导为已完成
        
        Args:
            guide_key (str): 引导键名
        """
        self.set(f"guides.{guide_key}_guided", True)
        
    def reset_guides(self) -> None:
        """重置所有引导状态为未完成"""
        guides = self.get("guides", {})
        for key in guides:
            self.set(f"guides.{key}", False)


# 创建单例实例
user_settings = UserSettings() 