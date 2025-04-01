#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理界面主类模块，整合各个UI组件
"""

import sys
import os
import logging
from typing import Dict, Any, Callable, Optional

from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QAction
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QFont, QIcon, QCloseEvent

from config import VERSION, WINDOW_WIDTH, WINDOW_HEIGHT
from password import password_manager
from user import user_manager
from user_settings import user_settings
from ui.password_manager.ui_layout import PasswordManagerLayout
from ui.password_manager.ui_table import PasswordTable
from ui.password_manager.ui_operations import PasswordOperations
from ui_components import show_message
from ui.password_manager.ui_guide import start_walkthrough

# 为了解决导入问题，添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 导入MySQL配置对话框
from mysql_config_dialog import MySQLConfigDialog

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
        file_menu = menubar.addMenu('文件')
        
        # 导出动作
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.operations_manager.export_data)
        file_menu.addAction(export_action)
        
        # 导入动作
        import_action = QAction('导入数据', self)
        import_action.triggered.connect(self.operations_manager.import_data)
        file_menu.addAction(import_action)
        
        # 分隔线
        file_menu.addSeparator()
        
        # 退出动作
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        # 密码生成器动作
        password_generator_action = QAction('密码生成器', self)
        password_generator_action.triggered.connect(self._open_password_generator)
        tools_menu.addAction(password_generator_action)
        
        # SSH日志查看器动作
        ssh_log_viewer_action = QAction('SSH日志查看器', self)
        ssh_log_viewer_action.triggered.connect(self._open_ssh_log_viewer)
        tools_menu.addAction(ssh_log_viewer_action)
        
        # 日志审计动作
        audit_log_action = QAction('查看审计日志', self)
        audit_log_action.triggered.connect(self._open_audit_log_viewer)
        tools_menu.addAction(audit_log_action)
        
        # 数据库配置动作
        mysql_config_action = QAction('数据库配置', self)
        mysql_config_action.triggered.connect(self._open_mysql_config)
        tools_menu.addAction(mysql_config_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        # 引导帮助子菜单
        guide_submenu = help_menu.addMenu('引导帮助')
        
        # 主界面功能引导
        main_features_guide_action = QAction('主界面功能引导', self)
        main_features_guide_action.triggered.connect(self._show_main_features_guide)
        guide_submenu.addAction(main_features_guide_action)
        
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
        
        # 添加短暂延迟后显示主界面操作引导
        QTimer.singleShot(1000, self._show_main_features_guide)
        
    def _show_main_features_guide(self):
        """显示主界面功能引导"""
        # 获取关键UI元素
        target_widgets = {
            "owners_list": self.layout_manager.owner_list_widget,
            "password_table": self.layout_manager.password_table,
            "search_box": self.layout_manager.search_edit,
            "action_buttons": self.layout_manager.splitter,
            "menu_bar": self.menuBar()
        }
        
        # 启动步骤引导
        start_walkthrough("main_features", self, target_widgets)
        
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

    def _open_audit_log_viewer(self):
        """打开日志审计查看器"""
        try:
            # 优先使用内嵌方式打开
            try:
                from audit_log_viewer import AuditLogViewer
                logger.info("使用内嵌方式打开审计日志查看器")
                
                viewer = AuditLogViewer()
                viewer.setWindowModality(Qt.NonModal)  # 非模态窗口
                viewer.show()
                
                # 保持窗口引用，防止被垃圾回收
                if not hasattr(self, '_audit_log_viewers'):
                    self._audit_log_viewers = []
                self._audit_log_viewers.append(viewer)
                
                return
            except Exception as inner_err:
                logger.error(f"内嵌方式启动审计日志查看器失败: {str(inner_err)}")
                logger.info("尝试使用独立进程方式启动")
            
            # 使用独立的审计日志查看器脚本
            import sys
            import subprocess
            import os
            
            # 获取Python解释器路径
            python_executable = sys.executable
            
            # 获取独立的日志审计查看器脚本路径
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            script_path = os.path.join(base_dir, 'audit_log_viewer_standalone.py')
            
            # 检查脚本是否存在
            if not os.path.exists(script_path):
                logger.warning(f"审计日志查看器脚本不存在: {script_path}")
                show_message(
                    self,
                    "文件不存在",
                    "审计日志查看器脚本不存在，请检查安装",
                    QMessageBox.Warning
                )
                return
            
            # 复制当前环境变量，包括Qt插件路径
            env = os.environ.copy()
            
            # 确保至少有这些Qt环境变量
            if "QT_PLUGIN_PATH" in env:
                logger.info(f"使用已有Qt插件路径: {env['QT_PLUGIN_PATH']}")
            
            # 启动新进程运行独立脚本
            logger.info(f"启动审计日志查看器: {script_path}")
            subprocess.Popen([python_executable, script_path], env=env)
            
        except Exception as e:
            logger.error(f"打开日志审计查看器时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            show_message(
                self,
                "打开失败",
                f"无法打开日志审计查看器: {str(e)}",
                QMessageBox.Warning
            )

    def _show_specific_guide(self, guide_type: str):
        """
        显示特定类型的引导
        
        从菜单主动选择查看引导时，总是显示引导内容，不管用户是否已经看过
        
        Args:
            guide_type (str): 引导类型
        """
        if guide_type == "main_features":
            # 设置强制显示标志
            self.force_walkthrough = True
            self._show_main_features_guide()
            self.force_walkthrough = False

    def _open_mysql_config(self):
        """打开MySQL配置对话框"""
        try:
            dialog = MySQLConfigDialog(self)
            
            # 连接存储模式变更信号
            dialog.storage_mode_changed.connect(self._handle_storage_mode_changed)
            
            result = dialog.exec_()
            
            if result:
                self.statusBar().showMessage("MySQL配置已更新", 5000)
        except Exception as e:
            logger.error(f"打开MySQL配置对话框时出错: {str(e)}")
            show_message(self, "错误", f"打开MySQL配置对话框时出错: {str(e)}", QMessageBox.Critical)

    def _handle_storage_mode_changed(self, mode: str):
        """
        处理存储模式变更
        
        Args:
            mode (str): 新的存储模式，"local"或"mysql"
        """
        message = f"存储模式已切换到: {'MySQL数据库' if mode == 'mysql' else '本地文件'}"
        self.statusBar().showMessage(message, 5000)
        
        # 如果需要，可以在这里添加其他处理逻辑
        # 例如重新加载数据等


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