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

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from config import LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_FORMAT, FONT_FAMILY
from login_ui import LoginUI
from ui.password_manager.password_manager_ui import PasswordManagerUI
from user_settings import user_settings


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


def main():
    """
    主函数
    """
    # 设置日志系统
    setup_logging()
    
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