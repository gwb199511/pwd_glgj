#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户设置模块，管理用户个性化配置
"""

import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List

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
    增加了延迟保存和批量操作功能，减少频繁的数据库访问。
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
            self._pending_changes = {}
            self._last_save_time = 0
            self._save_interval = 2.0  # 最小保存间隔（秒）
            self._save_timer = None
            self._save_lock = threading.Lock()
            self._load_settings()
            self._initialized = True
            # 启动后台保存线程
            self._start_background_save()
            
    def _start_background_save(self):
        """启动后台保存线程"""
        def save_task():
            while True:
                try:
                    # 检查是否有待保存的更改
                    with self._save_lock:
                        changes_exist = bool(self._pending_changes)
                    
                    # 如果有更改且达到保存间隔，执行保存
                    if changes_exist and time.time() - self._last_save_time >= self._save_interval:
                        self._flush_pending_changes()
                except Exception as e:
                    logger.error(f"后台保存设置时出错: {str(e)}")
                
                # 等待一段时间
                time.sleep(1.0)
        
        # 创建并启动后台线程
        save_thread = threading.Thread(target=save_task, daemon=True)
        save_thread.start()
            
    def _load_settings(self):
        """从存储加载设置"""
        try:
            # 从存储接口加载数据
            self._settings = self._storage.get_all()
            if not self._settings:
                self._settings = self._get_default_settings()
                self._save_settings_immediately()
        except Exception as e:
            logger.error(f"加载用户设置时出错: {str(e)}")
            self._settings = self._get_default_settings()
    
    def _save_settings_immediately(self):
        """立即保存设置到存储（不使用延迟）"""
        try:
            # 使用存储接口保存数据
            success = self._storage.save(self._settings)
            if success:
                self._last_save_time = time.time()
            return success
        except Exception as e:
            logger.error(f"立即保存用户设置时出错: {str(e)}")
            return False
            
    def _save_settings_delayed(self):
        """延迟保存设置到存储"""
        # 取消现有的定时器（如果存在）
        if self._save_timer:
            try:
                self._save_timer.cancel()
            except:
                pass
        
        # 创建新的定时器
        self._save_timer = threading.Timer(self._save_interval, self._flush_pending_changes)
        self._save_timer.daemon = True
        self._save_timer.start()
    
    def _flush_pending_changes(self):
        """将所有待处理的更改刷新到存储"""
        with self._save_lock:
            # 如果没有待处理的更改，直接返回
            if not self._pending_changes:
                return True
            
            try:
                # 将待处理的更改应用到设置
                for key, value in self._pending_changes.items():
                    parts = key.split('.')
                    
                    if len(parts) == 1:
                        # 根级别设置
                        self._settings[parts[0]] = value
                    else:
                        # 嵌套设置
                        config = self._settings
                        for i, part in enumerate(parts[:-1]):
                            if part not in config:
                                config[part] = {}
                            config = config[part]
                        
                        config[parts[-1]] = value
                
                # 清空待处理的更改
                self._pending_changes = {}
                
                # 保存到存储
                success = self._save_settings_immediately()
                logger.debug("已将所有待处理的设置更改保存到存储")
                return success
            except Exception as e:
                logger.error(f"保存待处理的设置更改时出错: {str(e)}")
                return False
            
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
            # 首先检查待处理的更改
            if key in self._pending_changes:
                return self._pending_changes[key]
            
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
            
    def set(self, key: str, value: Any, immediate: bool = False) -> bool:
        """
        设置值
        
        Args:
            key (str): 设置键名，支持点号分隔的嵌套键
            value (Any): 要设置的值
            immediate (bool): 是否立即保存，默认为False（延迟保存）
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        try:
            with self._save_lock:
                # 添加到待处理的更改
                self._pending_changes[key] = value
            
            # 根据需要选择保存方式
            if immediate:
                return self._flush_pending_changes()
            else:
                self._save_settings_delayed()
                return True
        except Exception as e:
            logger.error(f"设置用户配置时出错: {str(e)}")
            return False
    
    def set_batch(self, settings: Dict[str, Any], immediate: bool = False) -> bool:
        """
        批量设置多个值
        
        Args:
            settings (Dict[str, Any]): 键值对字典，键为设置键名
            immediate (bool): 是否立即保存，默认为False（延迟保存）
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        try:
            with self._save_lock:
                # 将所有设置添加到待处理的更改
                for key, value in settings.items():
                    self._pending_changes[key] = value
            
            # 根据需要选择保存方式
            if immediate:
                return self._flush_pending_changes()
            else:
                self._save_settings_delayed()
                return True
        except Exception as e:
            logger.error(f"批量设置用户配置时出错: {str(e)}")
            return False
            
    def is_guide_completed(self, guide_key: str) -> bool:
        """
        检查特定引导是否已完成
        
        Args:
            guide_key (str): 引导键名
            
        Returns:
            bool: 如果引导已完成则返回True，否则返回False
        """
        guided_key = f"{guide_key}_guided"
        return self.get(f"guides.{guided_key}", False)
        
    def get_batch(self, keys: List[str], defaults: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        批量获取多个设置值
        
        Args:
            keys (List[str]): 设置键名列表
            defaults (Dict[str, Any], optional): 默认值字典，键为设置键名
            
        Returns:
            Dict[str, Any]: 设置值字典
        """
        result = {}
        defaults = defaults or {}
        
        for key in keys:
            result[key] = self.get(key, defaults.get(key))
        
        return result
        
    def complete_guide_steps(self, guide_keys: List[str]) -> None:
        """
        完成多个引导步骤（合并为一次数据库操作）
        
        Args:
            guide_keys (List[str]): 引导键名列表
        """
        settings = {}
        
        # 准备所有设置
        for key in guide_keys:
            guided_key = f"{key}_guided"
            settings[f"guides.{guided_key}"] = True
            settings[f"guides.{key}"] = True
        
        # 批量设置并立即保存
        self.set_batch(settings, immediate=True)
        logger.info(f"已完成引导步骤: {', '.join(guide_keys)}")
        
    def mark_guide_completed(self, guide_key: str, immediate: bool = False) -> None:
        """
        标记特定引导为已完成
        
        Args:
            guide_key (str): 引导键名
            immediate (bool): 是否立即保存，默认为False（延迟保存）
        """
        settings = {}
        guided_key = f"{guide_key}_guided"
        settings[f"guides.{guided_key}"] = True
        settings[f"guides.{guide_key}"] = True
        
        # 使用批量设置
        self.set_batch(settings, immediate=immediate)
        logger.info(f"已标记引导 {guide_key} 为已完成")
        
    def mark_multiple_guides_completed(self, guide_keys: list) -> None:
        """
        标记多个引导为已完成（批量操作）
        
        Args:
            guide_keys (list): 引导键名列表
        """
        settings = {}
        for key in guide_keys:
            guided_key = f"{key}_guided"
            settings[f"guides.{guided_key}"] = True
        
        self.set_batch(settings)
        logger.info(f"已批量标记引导为已完成: {', '.join(guide_keys)}")
        
    def reset_guides(self) -> None:
        """重置所有引导状态为未完成"""
        guides = self.get("guides", {})
        settings = {}
        
        # 收集所有引导键
        for key in list(guides.keys()):
            settings[f"guides.{key}"] = False
            logger.info(f"已重置引导状态: {key}")
            
        # 特别确保主要引导状态被重置
        key_list = ["main_features_guided", "password_update_guided", "main_features", "password_update"]
        for key in key_list:
            settings[f"guides.{key}"] = False
            settings[f"guides.{key}_guided"] = False
            logger.info(f"已强制重置引导状态: {key}")
        
        # 批量保存所有更改
        self.set_batch(settings, immediate=True)
        logger.info("所有引导状态已重置")
    
    def flush_all_changes(self) -> bool:
        """
        立即保存所有待处理的更改
        
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        return self._flush_pending_changes()


# 创建单例实例
user_settings = UserSettings() 