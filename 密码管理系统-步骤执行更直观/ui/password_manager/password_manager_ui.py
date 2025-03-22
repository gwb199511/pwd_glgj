#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理界面主类模块，整合各个UI组件
"""

import sys
import logging
from typing import Dict, Any, Callable, Optional

from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QAction
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QIcon, QCloseEvent

from config import VERSION, WINDOW_WIDTH, WINDOW_HEIGHT
from password import password_manager
from user import user_manager
from user_settings import user_settings
from ui.password_manager.ui_layout import PasswordManagerLayout
from ui.password_manager.ui_table import PasswordTable
from ui.password_manager.ui_operations import PasswordOperations
from ui_components import show_message
from ui.password_manager.ui_guide import show_guide_if_needed, PASSWORD_UPDATE_GUIDE

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
        
        # 创建菜单栏
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('选项')
        
        # 退出动作
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        # 密码生成器动作
        password_gen_action = QAction('密码生成器', self)
        password_gen_action.triggered.connect(self._open_password_generator)
        tools_menu.addAction(password_gen_action)
        
        # SSH日志查看器动作
        ssh_log_action = QAction('SSH操作日志', self)
        ssh_log_action.triggered.connect(self._open_ssh_log_viewer)
        tools_menu.addAction(ssh_log_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        # 引导帮助子菜单
        guide_submenu = help_menu.addMenu('引导帮助')
        
        # 密码更新引导
        password_update_guide_action = QAction('密码更新引导', self)
        password_update_guide_action.triggered.connect(lambda: self._show_specific_guide("password_update"))
        guide_submenu.addAction(password_update_guide_action)
        
        # 编辑功能引导
        first_edit_guide_action = QAction('表格编辑功能引导', self)
        first_edit_guide_action.triggered.connect(lambda: self._show_specific_guide("first_edit"))
        guide_submenu.addAction(first_edit_guide_action)
        
        # 密码字段引导
        password_field_guide_action = QAction('密码字段引导', self)
        password_field_guide_action.triggered.connect(lambda: self._show_specific_guide("password_field"))
        guide_submenu.addAction(password_field_guide_action)
        
        # IP地址字段引导
        ip_field_guide_action = QAction('IP地址字段引导', self)
        ip_field_guide_action.triggered.connect(lambda: self._show_specific_guide("ip_field"))
        guide_submenu.addAction(ip_field_guide_action)
        
        # 重置所有引导动作
        reset_guides_action = QAction('重置所有引导', self)
        reset_guides_action.triggered.connect(self._reset_all_guides)
        help_menu.addAction(reset_guides_action)
        
        # 关于动作
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
        
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
        
        # 显示密码更新引导
        self._show_password_update_guide()
        
    def _show_password_update_guide(self):
        """显示密码更新引导"""
        show_guide_if_needed("password_update", self)
        
    def _reset_all_guides(self):
        """重置所有引导状态"""
        # 确认重置
        result = QMessageBox.question(
            self,
            "重置引导",
            "确定要重置所有引导状态吗？\n\n这将使所有引导对话框在相应操作时再次显示。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            user_settings.reset_guides()
            QMessageBox.information(
                self,
                "重置完成",
                "所有引导状态已重置。\n\n在执行相应操作时，引导对话框将再次显示。",
                QMessageBox.Ok
            )

    def _show_about_dialog(self):
        """显示关于对话框"""
        from config import VERSION, BUILD_DATE
        QMessageBox.about(
            self,
            "关于密码管理系统",
            f"<h3>密码管理系统</h3>"
            f"<p>版本: {VERSION}</p>"
            f"<p>构建日期: {BUILD_DATE}</p>"
            f"<p>一个安全、易用的密码管理工具</p>"
        )

    def _open_password_generator(self):
        """打开密码生成器"""
        try:
            from password_generator_dialog import PasswordGeneratorDialog
            dialog = PasswordGeneratorDialog(self)
            dialog.show()
            logger.debug("已打开密码生成器对话框")
        except Exception as e:
            logger.error(f"打开密码生成器时出错: {str(e)}")
            show_message(
                self,
                "打开失败",
                f"无法打开密码生成器: {str(e)}",
                QMessageBox.Warning
            )

    def _open_ssh_log_viewer(self):
        """打开SSH日志查看器"""
        try:
            from ssh_log_viewer import SSHLogViewer
            log_viewer = SSHLogViewer()
            log_viewer.show()
        except Exception as e:
            logger.error(f"打开SSH日志查看器时出错: {str(e)}")
            show_message(
                self,
                "打开失败",
                f"无法打开SSH日志查看器: {str(e)}",
                QMessageBox.Warning
            )

    def _show_specific_guide(self, guide_type: str):
        """
        显示特定类型的引导
        
        从菜单主动选择查看引导时，总是显示引导内容，不管用户是否已经看过
        
        Args:
            guide_type (str): 引导类型
        """
        show_guide_if_needed(guide_type, self, force=True)


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