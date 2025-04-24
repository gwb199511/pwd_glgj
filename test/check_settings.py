#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查用户设置脚本
"""

import os
import sys
import json

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入相关模块
from core.user_settings import user_settings
from core.db_user_settings import db_user_settings

def main():
    """检查用户设置中的引导状态"""
    # 设置用户
    username = "admin"
    user_settings.set_current_user(username)
    
    # 从用户设置对象获取值
    from_settings = user_settings.is_guide_completed("main_features")
    
    # 直接从数据库获取值
    from_db = db_user_settings.get_setting(username, "guides.main_features_guided", False)
    
    # 获取所有设置
    all_settings = db_user_settings.get_all_settings(username)
    print("直接从DB获取的所有设置:")
    print(json.dumps(all_settings, ensure_ascii=False, indent=2))
    
    # 强制重新加载设置
    print("\n强制重新加载设置...")
    user_settings._load_settings()
    
    # 再次检查guides设置
    guides_in_settings = "guides" in user_settings._settings
    main_features_key = "main_features_guided"
    has_main_features = guides_in_settings and main_features_key in user_settings._settings.get("guides", {})
    main_features_value = user_settings._settings.get("guides", {}).get(main_features_key) if guides_in_settings else None
    
    # 打印结果
    print(f"\n用户: {username}")
    print(f"从user_settings.is_guide_completed获取的值: {from_settings}")
    print(f"从db_user_settings直接获取的值: {from_db}")
    print(f"guides是否在settings中: {guides_in_settings}")
    print(f"main_features_guided是否在guides中: {has_main_features}")
    print(f"main_features_guided的值: {main_features_value}")
    
    # 检查内存中的设置
    print("\n内存中的设置:")
    settings_dict = user_settings._settings
    if settings_dict:
        print(json.dumps(settings_dict, ensure_ascii=False, indent=2))
    else:
        print("内存中没有设置")

if __name__ == "__main__":
    main() 