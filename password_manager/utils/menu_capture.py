#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
菜单捕获工具
用于将右键菜单捕获为图片并保存
"""

import os
import logging
import traceback
from PyQt5.QtWidgets import QMenu, QApplication, QWidget
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, QSize

# 配置日志
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory):
    """
    确保目录存在，不存在则创建
    
    Args:
        directory (str): 目录路径
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logger.info(f"创建目录: {directory}")
        except Exception as e:
            logger.error(f"创建目录 {directory} 失败: {str(e)}")
            return False
    return True

def capture_menu_to_image(menu, file_path):
    """
    将菜单捕获为图片并保存
    
    Args:
        menu (QMenu): 要捕获的菜单
        file_path (str): 保存图片的路径
    
    Returns:
        bool: 是否成功
    """
    try:
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if not ensure_directory_exists(directory):
            return False
            
        # 确保菜单已经完成布局
        menu.adjustSize()
        
        # 创建一个正确尺寸的QPixmap
        pixmap = QPixmap(menu.width(), menu.height())
        pixmap.fill(Qt.transparent)
        
        # 使用QPainter将菜单渲染到QPixmap
        painter = QPainter(pixmap)
        menu.render(painter)
        painter.end()
        
        # 保存图片
        success = pixmap.save(file_path, "PNG")
        if success:
            logger.info(f"成功保存菜单图片到: {file_path}")
            return True
        else:
            logger.error(f"保存图片失败: {file_path}")
            return False
            
    except Exception as e:
        logger.error(f"捕获菜单图片时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

class MenuCapture:
    """
    菜单捕获类，用于创建和捕获右键菜单
    """
    
    def __init__(self, parent=None):
        """
        初始化菜单捕获器
        
        Args:
            parent (QWidget): 父窗口
        """
        self.parent = parent or QApplication.activeWindow()
        self.account_menu = None
        self.password_menu = None
    
    def create_account_menu(self):
        """
        创建账号列右键菜单
        
        Returns:
            QMenu: 创建的菜单
        """
        # 创建菜单
        menu = QMenu(self.parent)
        
        # 设置样式
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                padding: 5px;
                border-radius: 3px;
            }
            QMenu::item {
                padding: 5px 30px 5px 20px;
                border: 1px solid transparent;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
            }
            QMenu::separator {
                height: 1px;
                background: #ccc;
                margin: 5px 15px;
            }
        """)
        
        # 导入图标管理器
        from utils.icon_manager import IconManager
        icon_manager = IconManager()
        
        # 添加菜单项
        copy_action = menu.addAction("复制")
        copy_icon = icon_manager.get_icon("复制")
        if copy_icon:
            copy_action.setIcon(copy_icon)
            
        menu.addSeparator()
        
        add_action = menu.addAction("添加行")
        add_icon = icon_manager.get_icon("添加行")
        if add_icon:
            add_action.setIcon(add_icon)
            
        edit_action = menu.addAction("编辑行")
        edit_icon = icon_manager.get_icon("编辑行")
        if edit_icon:
            edit_action.setIcon(edit_icon)
            
        history_action = menu.addAction("查看历史密码修改记录")
        history_icon = icon_manager.get_icon("查看历史密码修改记录")
        if history_icon:
            history_action.setIcon(history_icon)
            
        delete_action = menu.addAction("删除行")
        delete_icon = icon_manager.get_icon("删除行")
        if delete_icon:
            delete_action.setIcon(delete_icon)
        
        self.account_menu = menu
        return menu
    
    def create_password_menu(self):
        """
        创建密码列右键菜单
        
        Returns:
            QMenu: 创建的菜单
        """
        # 创建菜单
        menu = QMenu(self.parent)
        
        # 设置样式
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                padding: 5px;
                border-radius: 3px;
            }
            QMenu::item {
                padding: 5px 30px 5px 20px;
                border: 1px solid transparent;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
            }
            QMenu::separator {
                height: 1px;
                background: #ccc;
                margin: 5px 15px;
            }
        """)
        
        # 导入图标管理器
        from utils.icon_manager import IconManager
        icon_manager = IconManager()
        
        # 添加菜单项
        copy_action = menu.addAction("复制")
        copy_icon = icon_manager.get_icon("复制")
        if copy_icon:
            copy_action.setIcon(copy_icon)
            
        generate_action = menu.addAction("生成16位随机密码\n并更新到服务器")
        generate_icon = icon_manager.get_icon("生成16位随机密码\n并更新到服务器")
        if generate_icon:
            generate_action.setIcon(generate_icon)
            
        menu.addSeparator()
        
        add_action = menu.addAction("添加行")
        add_icon = icon_manager.get_icon("添加行")
        if add_icon:
            add_action.setIcon(add_icon)
            
        edit_action = menu.addAction("编辑行")
        edit_icon = icon_manager.get_icon("编辑行")
        if edit_icon:
            edit_action.setIcon(edit_icon)
            
        history_action = menu.addAction("查看历史密码修改记录")
        history_icon = icon_manager.get_icon("查看历史密码修改记录")
        if history_icon:
            history_action.setIcon(history_icon)
            
        delete_action = menu.addAction("删除行")
        delete_icon = icon_manager.get_icon("删除行")
        if delete_icon:
            delete_action.setIcon(delete_icon)
        
        self.password_menu = menu
        return menu
        
    def capture_both_menus(self, images_dir=None):
        """
        捕获账号和密码菜单并保存为图片
        
        Args:
            images_dir (str, optional): 保存图片的目录，默认为项目根目录下的images文件夹
        
        Returns:
            tuple: (账号菜单图片路径, 密码菜单图片路径)
        """
        # 确定保存路径
        if images_dir is None:
            # 尝试找到合适的目录
            possible_dirs = [
                os.path.abspath(os.path.join(os.getcwd(), "images")),
                os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), "images"))
            ]
            
            # 检查是否存在某个目录，不存在则使用第一个
            images_dir = next((d for d in possible_dirs if os.path.exists(d)), possible_dirs[0])
        
        # 确保目录存在
        ensure_directory_exists(images_dir)
        
        # 文件路径
        account_path = os.path.join(images_dir, "account_menu.png")
        password_path = os.path.join(images_dir, "password_menu.png")
        
        # 创建账号菜单
        if not self.account_menu:
            self.create_account_menu()
            
        # 创建密码菜单
        if not self.password_menu:
            self.create_password_menu()
            
        # 使用定时器延迟截图，确保图标已加载完成
        app = QApplication.instance()
        
        # 添加短暂延迟，确保菜单和图标都完全加载和渲染
        def do_capture_account():
            logger.info("开始捕获账号菜单...")
            capture_menu_to_image(self.account_menu, account_path)
            
            # 延迟捕获密码菜单
            QTimer.singleShot(200, do_capture_password)
            
        def do_capture_password():
            logger.info("开始捕获密码菜单...")
            capture_menu_to_image(self.password_menu, password_path)
            logger.info("菜单捕获完成")
        
        # 首先显示菜单以触发图标加载，但不显示在屏幕上
        self.account_menu.popup(QPoint(-1000, -1000))  # 在屏幕外弹出
        self.account_menu.hide()  # 立即隐藏
        
        self.password_menu.popup(QPoint(-1000, -1000))  # 在屏幕外弹出
        self.password_menu.hide()  # 立即隐藏
        
        # 延迟500毫秒，确保图标完全加载
        QTimer.singleShot(500, do_capture_account)
        
        # 处理事件，直到捕获完成
        app.processEvents()
        
        return account_path, password_path 