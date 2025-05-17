#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成菜单图片脚本
用于将右键菜单捕获为图片并保存到images目录
"""

import os
import sys
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, QEventLoop
from utils.menu_capture import MenuCapture

def main():
    """
    主函数，创建并保存菜单图片
    """
    # 创建Qt应用程序
    app = QApplication(sys.argv)
    
    # 创建images目录
    images_dir = os.path.abspath(os.path.join(os.path.dirname(current_dir), "images"))
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        logger.info(f"创建目录: {images_dir}")
    
    logger.info(f"菜单图片将保存到: {images_dir}")
    
    # 创建菜单捕获器
    menu_capture = MenuCapture()
    
    # 确保应用程序事件处理已启动
    app.processEvents()
    
    # 捕获菜单图片
    account_path, password_path = menu_capture.capture_both_menus(images_dir)
    
    # 创建事件循环以等待捕获完成
    loop = QEventLoop()
    
    # 设置一个定时器，一定时间后结束程序
    def finish_capture():
        logger.info(f"账号菜单图片已保存到: {account_path}")
        logger.info(f"密码菜单图片已保存到: {password_path}")
        
        # 显示成功消息
        QMessageBox.information(None, "菜单图片生成", 
            f"菜单图片已成功生成！\n\n"
            f"账号菜单图片: {account_path}\n"
            f"密码菜单图片: {password_path}")
        
        logger.info("完成！菜单图片已成功生成。")
        loop.quit()
    
    # 设置3秒后结束程序（给足够的时间让捕获完成）
    QTimer.singleShot(3000, finish_capture)
    
    # 等待捕获完成
    loop.exec_()

if __name__ == "__main__":
    main() 