#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理界面主类模块，整合各个UI组件
"""

import sys
import logging
from typing import Dict, Any, Callable, Optional

from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QIcon, QCloseEvent

from config import VERSION, WINDOW_WIDTH, WINDOW_HEIGHT
from password import password_manager
from user import user_manager
from ui.password_manager.ui_layout import PasswordManagerLayout
from ui.password_manager.ui_table import PasswordTable
from ui.password_manager.ui_operations import PasswordOperations
from ui_components import show_message

# 配置日志
logger = logging.getLogger(__name__)


class PasswordManagerUI(QMainWindow):
    """
    密码管理界面主类
    
    整合各个UI组件，协调各组件间的交互，处理用户界面事件。
    """

    def __init__(self, username: str):
        """
        初始化密码管理界面
        
        Args:
            username (str): 当前登录的用户名
        """
        super().__init__()
        self.username = username
        
        # 设置窗口属性
        self.setWindowTitle(f"密码管理系统 v{VERSION} - {username}")
        self.setMinimumSize(800, 500)
        
        # 创建界面组件
        self._create_ui_components()
        
        # 设置窗口大小为配置中定义的大小
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # 加载数据
        self._load_initial_data()
        
    def _create_ui_components(self):
        """
        创建界面组件
        """
        # 创建布局管理器
        self.layout_manager = PasswordManagerLayout(self)
        
        # 创建表格管理器
        self.table_manager = PasswordTable(self.layout_manager.password_table)
        # 设置当前用户名
        self.table_manager.current_owner = self.username
        
        # 创建操作管理器
        self.operations_manager = PasswordOperations(self, self.table_manager)
        
        # 设置回调函数
        self._setup_callbacks()
        
        # 调整窗口大小
        self.layout_manager.resize_to_default()
        
    def _setup_callbacks(self):
        """
        设置回调函数
        """
        callbacks = {
            # 人员列表相关
            "owner_selected": self.operations_manager.handle_owner_selection,
            
            # 表格操作相关
            "table_double_clicked": self.operations_manager.handle_table_double_click,
            
            # 搜索相关
            "search_changed": self.operations_manager.handle_search,
            "clear_search": self.operations_manager.clear_search
        }
        
        self.layout_manager.setup_connections(callbacks)
        
    def _load_initial_data(self):
        """
        加载初始数据
        """
        try:
            # 获取所有者列表
            owners = password_manager.get_all_owners()
            
            # 确保三个固定人员的数据存在
            fixed_owners = ["徐国明", "高文彬", "石帆"]
            for owner in fixed_owners:
                if owner not in owners:
                    # 如果数据不存在，创建空数据结构
                    password_manager.db.set(owner, [])
                    logger.info(f"为人员 {owner} 创建了初始数据结构")
            
            # 更新人员列表（函数内部已修改为仅显示三个固定人员）
            self.layout_manager.update_owner_list(fixed_owners)
            
            # 默认选择第一个人员
            self.layout_manager.owner_list_widget.setCurrentRow(0)
            
            # 触发选择事件
            current_item = self.layout_manager.owner_list_widget.currentItem()
            if current_item:
                self.operations_manager.handle_owner_selection(current_item)
                
            # 显示欢迎消息
            self.statusBar().showMessage(f"欢迎，{self.username}!", 5000)
            
        except Exception as e:
            logger.error(f"加载初始数据时出错: {str(e)}")
            show_message(self, "加载错误", f"加载数据时出错: {str(e)}", QMessageBox.Warning)
            
    def keyPressEvent(self, event):
        """
        处理键盘事件
        
        Args:
            event: 键盘事件
        """
        # 如果表格有焦点，让表格处理Ctrl+C复制事件
        if self.table_manager.table.hasFocus() and event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
            # 不处理，让事件过滤器处理
            super().keyPressEvent(event)
            return
        
        # Ctrl+F: 聚焦搜索框
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            self.layout_manager.search_edit.setFocus()
            
        # Delete: 删除选中的密码
        elif event.key() == Qt.Key_Delete:
            self.operations_manager.delete_password()
            
        # Escape: 取消编辑
        elif event.key() == Qt.Key_Escape and self.table_manager.editing_row >= 0:
            self.table_manager.cancel_editing()
            
        else:
            super().keyPressEvent(event)
            
    def closeEvent(self, event: QCloseEvent):
        """
        处理窗口关闭事件
        
        Args:
            event (QCloseEvent): 关闭事件
        """
        # 如果正在编辑，询问是否保存
        if self.table_manager.editing_row >= 0:
            reply = QMessageBox.question(
                self, 
                "确认退出", 
                "当前有未保存的编辑内容，是否退出？\n选择\"是\"将丢弃未保存的内容。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
                
        # 清除当前用户
        user_manager.logout()
        
        # 接受关闭事件
        event.accept()
        
    def run(self):
        """
        显示密码管理界面
        """
        # 确保窗口使用配置的默认大小
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.show()


def main():
    """
    主函数，用于独立测试密码管理界面
    """
    app = QApplication(sys.argv)
    # 使用测试用户名
    ui = PasswordManagerUI("测试用户")
    ui.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 