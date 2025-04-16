#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
迁移脚本，用于将旧的项目结构迁移到新的结构
"""

import os
import shutil
import re
import sys
from pathlib import Path

# 定义源文件夹和目标文件夹
SOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "密码管理系统-步骤执行更直观")
TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

# 文件映射表
FILE_MAPPING = {
    "run.py": "run.py",
    "main.py": "main.py",
    "config.py": "config.py",
    "requirements.txt": "requirements.txt",
    "user.py": "core/user.py",
    "password.py": "core/password.py",
    "database.py": "core/database.py",
    "db_manager.py": "core/db_manager.py",
    "encrypt.py": "core/encrypt.py",
    "data_storage.py": "core/data_storage.py",
    "user_settings.py": "core/user_settings.py",
    "login_ui.py": "ui/login/login_ui.py",
    "ui_components.py": "ui/components/ui_components.py",
    "mysql_config_dialog.py": "ui/dialogs/mysql_config_dialog.py",
    "excel_dialog.py": "ui/dialogs/excel_dialog.py",
    "password_generator_dialog.py": "ui/dialogs/password_generator_dialog.py",
    "ui/password_manager/password_manager_ui.py": "ui/password_manager/password_manager_ui.py",
    "ui/password_manager/ui_layout.py": "ui/password_manager/ui_layout.py",
    "ui/password_manager/ui_operations.py": "ui/password_manager/ui_operations.py",
    "ui/password_manager/ui_utils.py": "ui/password_manager/ui_utils.py",
    "excel_utils.py": "utils/excel_utils.py",
    "password_generator.py": "utils/password_generator.py",
    "ssh_password_updater.py": "features/ssh/ssh_password_updater.py",
    "ssh_log_viewer.py": "features/ssh/ssh_log_viewer.py",
    "view_ssh_logs.py": "features/ssh/view_ssh_logs.py",
    "audit_log.py": "features/audit/audit_log.py",
    "audit_log_viewer.py": "features/audit/audit_log_viewer.py",
    "audit_log_viewer_standalone.py": "features/audit/audit_log_viewer_standalone.py",
}

# 导入路径替换规则
IMPORT_REPLACEMENTS = [
    (r"from login_ui import", "from ui.login.login_ui import"),
    (r"from user_settings import", "from core.user_settings import"),
    (r"from password_generator import", "from utils.password_generator import"),
    (r"from excel_utils import", "from utils.excel_utils import"),
    (r"from encrypt import", "from core.encrypt import"),
    (r"from database import", "from core.database import"),
    (r"from db_manager import", "from core.db_manager import"),
    (r"from user import", "from core.user import"),
    (r"from password import", "from core.password import"),
    (r"from data_storage import", "from core.data_storage import"),
    (r"from mysql_config_dialog import", "from ui.dialogs.mysql_config_dialog import"),
    (r"from excel_dialog import", "from ui.dialogs.excel_dialog import"),
    (r"from password_generator_dialog import", "from ui.dialogs.password_generator_dialog import"),
    (r"from ui_components import", "from ui.components.ui_components import"),
    (r"from audit_log import", "from features.audit.audit_log import"),
    (r"from audit_log_viewer import", "from features.audit.audit_log_viewer import"),
    (r"from ssh_password_updater import", "from features.ssh.ssh_password_updater import"),
    (r"from ssh_log_viewer import", "from features.ssh.ssh_log_viewer import"),
    (r"from view_ssh_logs import", "from features.ssh.view_ssh_logs import"),
]

def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def copy_file_with_path_update(source_file, target_file):
    """复制文件并更新导入路径"""
    # 确保目标目录存在
    target_dir = os.path.dirname(target_file)
    ensure_directory(target_dir)
    
    # 读取源文件内容
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 应用导入路径替换规则
    for pattern, replacement in IMPORT_REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    
    # 写入目标文件
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已复制并更新: {source_file} -> {target_file}")

def copy_directory(source_dir, target_dir):
    """复制整个目录"""
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    for item in os.listdir(source_dir):
        s = os.path.join(source_dir, item)
        t = os.path.join(target_dir, item)
        if os.path.isdir(s):
            copy_directory(s, t)
        else:
            if not os.path.exists(t) or os.stat(s).st_mtime > os.stat(t).st_mtime:
                shutil.copy2(s, t)
    
    print(f"已复制目录: {source_dir} -> {target_dir}")

def create_init_files():
    """在所有包目录中创建__init__.py文件"""
    packages = [
        "core",
        "ui",
        "ui/login",
        "ui/components",
        "ui/dialogs",
        "ui/password_manager",
        "utils",
        "features",
        "features/ssh",
        "features/audit"
    ]
    
    for package in packages:
        init_file = os.path.join(TARGET_DIR, package, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write("# 包初始化文件\n")
            print(f"已创建: {init_file}")

def migrate_files():
    """根据映射表迁移文件"""
    for source_rel_path, target_rel_path in FILE_MAPPING.items():
        source_file = os.path.join(SOURCE_DIR, source_rel_path)
        target_file = os.path.join(TARGET_DIR, target_rel_path)
        
        if os.path.exists(source_file):
            copy_file_with_path_update(source_file, target_file)
        else:
            print(f"警告: 源文件不存在 {source_file}")

def migrate_data_files():
    """迁移数据和日志文件"""
    # 迁移数据文件
    source_data_dir = os.path.join(SOURCE_DIR, "data")
    target_data_dir = os.path.join(TARGET_DIR, "data")
    if os.path.exists(source_data_dir):
        copy_directory(source_data_dir, target_data_dir)
    
    # 迁移日志文件
    source_logs_dir = os.path.join(SOURCE_DIR, "logs")
    target_logs_dir = os.path.join(TARGET_DIR, "logs")
    if os.path.exists(source_logs_dir):
        copy_directory(source_logs_dir, target_logs_dir)

def main():
    """主函数"""
    print("开始迁移项目文件...")
    
    # 1. 确保所有目标目录存在
    for rel_path in set(os.path.dirname(path) for path in FILE_MAPPING.values()):
        ensure_directory(os.path.join(TARGET_DIR, rel_path))
    
    # 2. 创建__init__.py文件
    create_init_files()
    
    # 3. 迁移文件并更新导入路径
    migrate_files()
    
    # 4. 迁移数据和日志文件
    migrate_data_files()
    
    print("\n迁移完成！")
    print("请运行 python run.py 测试新结构的功能。")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"迁移过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 