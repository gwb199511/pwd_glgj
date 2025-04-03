#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
菜单截图工具 - 为引导步骤创建右键菜单截图
"""

import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QMenu, QAction
from PyQt5.QtGui import QPainter, QColor, QPixmap
from PyQt5.QtCore import Qt, QRect, QPoint, QSize

class MenuScreenshotTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("菜单截图工具")
        self.setGeometry(300, 300, 600, 400)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 创建按钮
        account_button = QPushButton("生成账号列菜单截图")
        account_button.clicked.connect(lambda: self.generate_menu_screenshot("account"))
        
        password_button = QPushButton("生成密码列菜单截图")
        password_button.clicked.connect(lambda: self.generate_menu_screenshot("password"))
        
        # 添加按钮到布局
        layout.addWidget(account_button)
        layout.addWidget(password_button)
        
    def generate_menu_screenshot(self, menu_type):
        """生成指定类型的菜单截图"""
        # 创建菜单
        menu = QMenu(self)
        
        # 添加通用菜单项
        copy_action = QAction("复制", self)
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        # 添加密码列特有菜单项
        if menu_type == "password":
            ssh_update_action = QAction("生成16位随机密码\n并更新到服务器", self)
            menu.addAction(ssh_update_action)
            menu.addSeparator()
        
        # 添加通用子菜单
        add_menu = menu.addMenu("添加行")
        add_above_action = QAction("在上方添加行", self)
        add_below_action = QAction("在下方添加行", self)
        add_last_action = QAction("在末尾添加行", self)
        add_menu.addAction(add_above_action)
        add_menu.addAction(add_below_action)
        add_menu.addAction(add_last_action)
        
        menu.addSeparator()
        
        edit_action = QAction("编辑行", self)
        menu.addAction(edit_action)
        
        delete_action = QAction("删除行", self)
        menu.addAction(delete_action)
        
        # 计算菜单尺寸
        menu.adjustSize()
        size = menu.sizeHint()
        size.setWidth(max(size.width(), 160))  # 确保至少160像素宽
        
        # 创建透明背景的pixmap
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        
        # 设置菜单位置和大小
        menu.resize(size)
        
        # 将菜单渲染到pixmap
        menu.render(pixmap, QPoint(0, 0))
        
        # 保存截图
        save_dir = "images"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        filename = f"{menu_type}_menu.png"
        filepath = os.path.join(save_dir, filename)
        
        # 保存PNG
        pixmap.save(filepath, "PNG")
        print(f"已保存菜单截图: {filepath}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    tool = MenuScreenshotTool()
    tool.show()
    sys.exit(app.exec_())