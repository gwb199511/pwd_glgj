#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
密码管理系统主入口
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
import traceback
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"已添加项目根目录到Python路径: {project_root}")

# 针对UI模块单独添加路径
ui_path = os.path.join(project_root, 'ui')
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)
    print(f"已添加UI模块路径: {ui_path}")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from config import LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_FORMAT, FONT_FAMILY, DATA_DIR
from ui.login.login_ui import LoginUI
from ui.password_manager.password_manager_ui import PasswordManagerUI
from core.user_settings import user_settings
from core.db_user_settings import db_user_settings


def setup_logging():
    """
    设置日志系统
    """
    # 确保日志目录存在
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 记录启动信息
    logging.info("密码管理系统启动")


def migrate_user_settings_if_needed():
    """
    如有必要，将用户设置从JSON文件迁移到数据库
    """
    try:
        # 检查是否存在用户设置文件
        settings_file = os.path.join(DATA_DIR, 'user_settings.json')
        if os.path.exists(settings_file):
            logging.info("检测到用户设置文件，尝试迁移到数据库...")
            
            # 检查数据库中是否已有设置数据
            from core.db_manager import db_manager
            check_sql = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'user_settings'
            """
            tables_result = db_manager.execute_query(check_sql)
            
            if tables_result and tables_result[0][0] > 0:
                # 表存在，检查是否有数据
                count_sql = "SELECT COUNT(*) FROM user_settings"
                count_result = db_manager.execute_query(count_sql)
                
                if count_result and count_result[0][0] == 0:
                    # 表存在但没有数据，执行迁移
                    result = user_settings.migrate_from_file()
                    if result:
                        logging.info("用户设置已成功迁移到数据库")
                    else:
                        logging.warning("用户设置迁移失败")
                else:
                    logging.info("数据库中已有用户设置数据，跳过迁移")
            else:
                # 表不存在，创建表并执行迁移
                logging.info("创建用户设置数据库表...")
                # 确保表存在
                db_user_settings._ensure_settings_table()
                
                # 执行迁移
                result = user_settings.migrate_from_file()
                if result:
                    logging.info("用户设置已成功迁移到数据库")
                else:
                    logging.warning("用户设置迁移失败")
    except Exception as e:
        logging.error(f"迁移用户设置时出错: {str(e)}")
        logging.error(traceback.format_exc())


def main():
    """
    主函数
    """
    # 设置日志系统
    setup_logging()
    
    # 迁移用户设置（如果需要）
    migrate_user_settings_if_needed()
    
    # 确保用户设置模块已经初始化
    logging.info(f"初始化用户设置模块...")
    try:
        # 访问设置以触发初始化
        _ = user_settings.get("version", "未知")
        logging.info(f"用户设置模块已初始化")
    except Exception as e:
        logging.error(f"初始化用户设置模块时出错: {str(e)}")

    # 检查是否有重置引导记录的命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--reset-guides":
        user_settings.reset_guides()
        logging.info("已重置引导记录")

    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont(FONT_FAMILY)
    app.setFont(font)

    # 创建登录界面
    login_window = LoginUI()
    
    # 密码管理窗口实例
    password_manager_window = None

    # 定义登录成功回调函数
    def on_login_success(username):
        nonlocal password_manager_window
        logging.info(f"用户 {username} 登录成功，准备打开密码管理界面")
        # 隐藏登录窗口
        login_window.hide()
        # 设置当前用户
        user_settings.set_current_user(username)
        # 创建并显示密码管理界面
        password_manager_window = PasswordManagerUI(username)
        password_manager_window.run()
        
    # 连接登录成功信号
    login_window.login_success.connect(on_login_success)
    
    # 显示登录界面
    login_window.run()
    
    # 进入应用程序主循环
    sys.exit(app.exec_())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"程序发生错误: {str(e)}")
        logging.error(traceback.format_exc())
        sys.exit(1) 