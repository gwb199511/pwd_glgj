#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
应用菜单图标脚本
为应用程序的所有菜单添加图标
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QMenu
from utils.icon_manager import IconManager

def main():
    """
    主函数，创建并应用菜单图标
    """
    # 创建Qt应用程序
    app = QApplication(sys.argv)
    
    # 创建图标管理器实例
    icon_manager = IconManager()
    
    # 创建示例窗口
    window = QMainWindow()
    window.setWindowTitle("菜单图标预览")
    window.resize(800, 600)
    
    # 创建菜单栏
    menu_bar = window.menuBar()
    
    # 创建文件菜单 - 使用实际应用中没有空格的特殊字符前缀
    file_menu = menu_bar.addMenu("□文件")
    
    # 创建导入/导出子菜单
    import_export_menu = QMenu("导入/导出", window)
    import_export_menu.addAction("从Excel导入")
    import_export_menu.addAction("导出到Excel")
    file_menu.addMenu(import_export_menu)
    
    file_menu.addAction("退出")
    
    # 创建工具菜单 - 使用实际应用中没有空格的特殊字符前缀
    tools_menu = menu_bar.addMenu("□工具")
    tools_menu.addAction("数据库配置")
    tools_menu.addAction("密码生成器")
    tools_menu.addAction("审计日志")  # 修正为审计日志
    tools_menu.addAction("显示字典引导")
    tools_menu.addAction("检查更新")
    
    # 创建帮助菜单 - 使用实际应用中没有空格的特殊字符前缀
    help_menu = menu_bar.addMenu("□帮助")
    help_menu.addAction("关于")
    
    # 应用图标
    icon_manager.apply_menu_icons(menu_bar)
    
    # 创建上下文菜单预览
    context_menu = QMenu("上下文菜单预览")
    context_menu.addAction("复制")
    context_menu.addAction("生成16位随机密码\n并更新到服务器")
    context_menu.addSeparator()
    
    # 添加子菜单
    add_menu = context_menu.addMenu("添加行")
    add_menu.addAction("在上方添加行")
    add_menu.addAction("在下方添加行")
    add_menu.addAction("在末尾添加行")
    
    context_menu.addAction("编辑行")
    context_menu.addAction("查看历史密码修改记录")
    context_menu.addAction("删除行")
    
    # 应用上下文菜单图标
    icon_manager.apply_context_menu_icons(context_menu)
    
    # 显示窗口
    window.show()
    
    # 显示上下文菜单
    context_menu.popup(window.geometry().center())
    
    # 运行应用
    logger.info("菜单图标已应用，请查看预览窗口和上下文菜单")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 