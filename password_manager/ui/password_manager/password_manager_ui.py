#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理UI模块主类
提供密码管理的界面功能
"""

import sys
import os
import logging
import traceback
from typing import Dict, Callable, Optional, List, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QMessageBox, QAction, QMenu,
    QDialog, QFileDialog, QShortcut
)
from PyQt5.QtCore import Qt, QModelIndex, QEvent, pyqtSignal, QTimer
from PyQt5.QtGui import QCloseEvent, QKeySequence, QFont, QPixmap, QIcon

from ui.password_manager.ui_layout import PasswordManagerLayout
from ui.password_manager.ui_table import PasswordTable
from ui.password_manager.ui_operations import PasswordOperations
from ui.password_manager.ui_guide import start_walkthrough
from core.password import password_manager
from core.user import user_manager
from config import WINDOW_WIDTH, WINDOW_HEIGHT, VERSION, COLORS, FONT_FAMILY, PASSWORD_COLUMNS, APP_ICON_FILE, STORAGE_TYPE
from core.user_settings import user_settings
from ui.components.ui_components import show_message, show_confirmation, ModernLabel, HorizontalLine, ModernButton

# 为了解决导入问题，添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 导入MySQL配置对话框
from ui.dialogs.mysql_config_dialog import MySQLConfigDialog

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
        # 设置窗口标题栏图标 (如果有)
        # self.setWindowIcon(QIcon("icon.png"))
        
        # 创建中心窗口部件
        self.widget = QWidget()
        
        # 创建布局管理器
        self.layout_manager = PasswordManagerLayout(self)
        
        # 创建密码表格管理器
        self.table_manager = PasswordTable(self.layout_manager.password_table)
        
        # 创建操作管理器
        self.operations_manager = PasswordOperations(self, self.table_manager)
        
        # 设置回调函数
        self._setup_callbacks()
        
        # 创建菜单
        self._create_menus()
        
        # 检查并更新requirements.txt
        self._check_excel_requirements()
        
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
        # 设置窗口图标
        try:
            if os.path.exists(APP_ICON_FILE):
                self.setWindowIcon(QIcon(APP_ICON_FILE))
        except Exception as e:
            logging.warning(f"设置密码管理窗口图标时出错: {str(e)}")

        # 确保窗口使用配置的默认大小
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.show()
        
        # 添加短暂延迟后显示主界面操作引导
        QTimer.singleShot(1000, self._show_main_features_guide)
        
    def _show_main_features_guide(self):
        """显示主界面功能引导"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 检查引导是否已完成
        from core.user_settings import user_settings
        is_completed = user_settings.is_guide_completed("main_features")
        logger.info(f"检查main_features引导状态: {'已完成' if is_completed else '未完成'}")
        
        # 获取关键UI元素
        target_widgets = {
            "owners_list": self.layout_manager.owner_list_widget,
            "password_table": self.layout_manager.password_table,
            "search_edit": self.layout_manager.search_edit,
            "action_buttons": self.layout_manager.splitter,
            "toolbar": self.layout_manager.toolbar
        }
        
        # 启动步骤引导
        result = start_walkthrough("main_features", self, target_widgets)
        logger.info(f"启动main_features引导结果: {'成功' if result else '已跳过'}")
        
        # 强制刷新用户设置，确保状态及时保存
        user_settings.flush_all_changes()

    def _reset_all_guides(self):
        """重置引导状态"""
        # 确认重置
        result = QMessageBox.question(
            self,
            "重置引导",
            "确定要重置引导状态吗？\n\n这将使所有引导对话框在相应操作时再次显示。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            user_settings.reset_guides()
            QMessageBox.information(
                self,
                "重置完成",
                "引导状态已重置。\n\n在执行相应操作时，引导对话框将再次显示。",
                QMessageBox.Ok
            )

    def _show_about_dialog(self):
        """显示关于对话框"""
        from config import VERSION, BUILD_DATE, COLORS, STORAGE_TYPE
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QSpacerItem, QSizePolicy, QGridLayout, QMessageBox
        from PyQt5.QtGui import QPixmap, QFont, QIcon
        from PyQt5.QtCore import Qt, QUrl
        from ui.components.ui_components import ModernLabel, HorizontalLine, ModernButton
        import os
        import platform
        
        # 创建自定义关于对话框
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("关于密码管理系统")
        about_dialog.setMinimumWidth(520)
        about_dialog.setMinimumHeight(450)
        about_dialog.setWindowFlags(about_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 主布局
        layout = QVBoxLayout(about_dialog)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # 标题部分
        title_layout = QHBoxLayout()
        
        # Logo
        try:
            # 尝试使用应用图标
            if os.path.exists(APP_ICON_FILE):
                logo_label = QLabel()
                pixmap = QPixmap(APP_ICON_FILE)
                if not pixmap.isNull():
                    logo_label.setPixmap(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    title_layout.addWidget(logo_label)
                else:
                    # 如果无法加载，使用图标文字
                    icon_label = QLabel("🔐")
                    icon_label.setFont(QFont("Arial", 40))
                    icon_label.setStyleSheet(f"color: {COLORS['primary']};")
                    title_layout.addWidget(icon_label)
            else:
                # 使用图标文字
                icon_label = QLabel("🔐")
                icon_label.setFont(QFont("Arial", 40))
                icon_label.setStyleSheet(f"color: {COLORS['primary']};")
                title_layout.addWidget(icon_label)
        except Exception as e:
            # 使用图标文字作为后备
            icon_label = QLabel("🔐")
            icon_label.setFont(QFont("Arial", 40))
            icon_label.setStyleSheet(f"color: {COLORS['primary']};")
            title_layout.addWidget(icon_label)
        
        # 标题文字
        title_text = QVBoxLayout()
        title = ModernLabel("密码管理系统", font_size=18, bold=True, color=COLORS["primary"])
        subtitle = ModernLabel(f"版本 {VERSION}", font_size=10)
        
        title_text.addWidget(title)
        title_text.addWidget(subtitle)
        title_layout.addLayout(title_text)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        layout.addWidget(HorizontalLine())
        
        # 信息部分
        info_box = QGroupBox("软件信息")
        info_box.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {COLORS['primary']};
                font-weight: bold;
            }}
        """)
        
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(10)
        
        # 信息表格布局
        info_grid = QGridLayout()
        info_grid.setColumnStretch(0, 0)
        info_grid.setColumnStretch(1, 1)
        info_grid.setHorizontalSpacing(10)
        info_grid.setVerticalSpacing(8)
        
        # 构建日期
        build_label = QLabel("<b>构建日期:</b>")
        build_label.setTextFormat(Qt.RichText)
        build_value = QLabel(BUILD_DATE)
        info_grid.addWidget(build_label, 0, 0, Qt.AlignLeft)
        info_grid.addWidget(build_value, 0, 1, Qt.AlignLeft)
        
        # 系统信息
        sys_label = QLabel("<b>操作系统:</b>")
        sys_label.setTextFormat(Qt.RichText)
        sys_value = QLabel(f"{platform.system()} {platform.version()}")
        info_grid.addWidget(sys_label, 1, 0, Qt.AlignLeft)
        info_grid.addWidget(sys_value, 1, 1, Qt.AlignLeft)
        
        # Python版本
        py_label = QLabel("<b>Python版本:</b>")
        py_label.setTextFormat(Qt.RichText)
        py_value = QLabel(platform.python_version())
        info_grid.addWidget(py_label, 2, 0, Qt.AlignLeft)
        info_grid.addWidget(py_value, 2, 1, Qt.AlignLeft)
        
        # 数据存储
        db_label = QLabel("<b>数据存储:</b>")
        db_label.setTextFormat(Qt.RichText)
        db_value = QLabel("MySQL数据库" if STORAGE_TYPE == "mysql" else "本地JSON文件")
        info_grid.addWidget(db_label, 3, 0, Qt.AlignLeft)
        info_grid.addWidget(db_value, 3, 1, Qt.AlignLeft)
        
        info_layout.addLayout(info_grid)
        
        # 描述
        description = QLabel(
            "密码管理系统是一个安全、高效的密码存储与管理工具，"
            "专为组织内部使用设计，提供便捷的密码记录、搜索和导出功能。"
            "系统支持多用户管理，并提供详细的操作审计日志，确保数据安全性和可追溯性。"
        )
        description.setWordWrap(True)
        description.setTextFormat(Qt.RichText)
        info_layout.addWidget(description)
        
        # 功能部分        
        features_box = QGroupBox("主要功能")
        features_box.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {COLORS['primary']};
                font-weight: bold;
            }}
        """)
        
        features_layout = QVBoxLayout(features_box)
        
        features = QLabel(
            "• <b>多人员密码管理</b>: 按人员分类管理多种系统密码<br>"
            "• <b>强大的搜索功能</b>: 快速定位所需密码信息<br>"
            "• <b>Excel导入导出</b>: 支持Excel格式数据导入导出<br>"
            "• <b>安全的数据存储</b>: 使用加密技术保障数据安全<br>"
            "• <b>操作审计日志</b>: 记录所有用户操作，便于追溯<br>"
            "• <b>密码生成器</b>: 快速生成符合规则的强密码"
        )
        features.setTextFormat(Qt.RichText)
        features_layout.addWidget(features)
        
        layout.addWidget(info_box)
        layout.addWidget(features_box)
        
        # 技术栈部分
        tech_layout = QHBoxLayout()
        tech_label = ModernLabel("技术栈:", font_size=9, bold=True)
        tech_value = ModernLabel("Python, PyQt5, MySQL", font_size=9)
        
        tech_layout.addWidget(tech_label)
        tech_layout.addWidget(tech_value)
        tech_layout.addStretch()
        
        # 操作区域
        action_box = QHBoxLayout()
        
        # 创建链接按钮
        help_button = ModernButton("用户手册", color=COLORS["info"], flat=True)
        help_button.setFixedWidth(90)
        help_button.clicked.connect(lambda: QMessageBox.information(about_dialog, "用户手册", "用户手册功能开发中，敬请期待！"))
        
        report_button = ModernButton("问题反馈", color=COLORS["secondary"], flat=True)
        report_button.setFixedWidth(90)
        report_button.clicked.connect(lambda: QMessageBox.information(about_dialog, "问题反馈", "如遇到问题，请与系统管理员联系。"))
        
        update_button = ModernButton("检查更新", color=COLORS["info"], flat=True)
        update_button.setFixedWidth(90)
        update_button.clicked.connect(lambda: QMessageBox.information(about_dialog, "检查更新", f"当前版本 {VERSION} 已是最新版本。"))
        
        action_box.addWidget(help_button)
        action_box.addWidget(report_button)
        action_box.addWidget(update_button)
        action_box.addStretch()
        
        layout.addLayout(tech_layout)
        layout.addLayout(action_box)
        
        # 版权信息
        copyright_layout = QHBoxLayout()
        copyright_info = ModernLabel("© 2025 首信科技，保留所有权利。", color=COLORS["secondary"])
        copyright_info.setAlignment(Qt.AlignCenter)
        copyright_layout.addStretch()
        copyright_layout.addWidget(copyright_info)
        copyright_layout.addStretch()
        
        layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(HorizontalLine())
        layout.addLayout(copyright_layout)
        
        # 添加确定按钮
        button_layout = QHBoxLayout()
        ok_button = ModernButton("确定", color=COLORS["primary"])
        ok_button.setFixedWidth(120)
        ok_button.clicked.connect(about_dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        about_dialog.exec_()

    def _open_password_generator(self):
        """打开密码生成器"""
        try:
            from ui.dialogs.password_generator_dialog import PasswordGeneratorDialog
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
            from features.ssh.ssh_log_viewer import SSHLogViewer
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
                from features.audit.audit_log_viewer import AuditLogViewer
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

    def _check_excel_requirements(self):
        """
        检查Excel相关的依赖是否已安装
        """
        try:
            import pandas
            import openpyxl
            logger.info("Excel依赖已安装")
        except ImportError:
            logger.warning("Excel依赖未安装，导入导出功能可能无法正常工作")
            # 提示用户安装依赖
            message = ("Excel导入导出功能需要安装额外的依赖。\n"
                     "请运行以下命令安装：\n\n"
                     "pip install pandas openpyxl xlsxwriter")
            show_message(self, "缺少依赖", message, QMessageBox.Warning)

    def _create_menus(self):
        """
        创建菜单
        """
        # 获取布局中的菜单对象
        file_menu = self.layout_manager.file_menu
        tools_menu = self.layout_manager.tools_menu
        help_menu = self.layout_manager.help_menu
        
        # 清除默认菜单项
        file_menu.clear()
        tools_menu.clear()
        help_menu.clear()
        
        # 文件菜单
        # Excel导入导出子菜单
        excel_menu = QMenu("导入/导出", self)
        
        # 导入Excel
        import_action = QAction("从Excel导入", self)
        import_action.triggered.connect(self._import_from_excel)
        excel_menu.addAction(import_action)
        
        # 导出Excel（支持单人导出和多人导出）
        export_action = QAction("导出到Excel", self)
        export_action.triggered.connect(self._export_to_excel)
        excel_menu.addAction(export_action)
        
        file_menu.addMenu(excel_menu)
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        # 数据库配置
        db_config_action = QAction("数据库配置", self)
        db_config_action.triggered.connect(self._open_mysql_config)
        tools_menu.addAction(db_config_action)
        
        # 密码生成器
        password_generator_action = QAction("密码生成器", self)
        password_generator_action.triggered.connect(self._open_password_generator)
        tools_menu.addAction(password_generator_action)
        
        # 审计日志查看
        audit_log_action = QAction("审计日志", self)
        audit_log_action.triggered.connect(self._open_audit_log_viewer)
        tools_menu.addAction(audit_log_action)
        
        # 添加重置引导选项
        tools_menu.addSeparator()
        
        # 显示主界面引导
        show_main_guide_action = QAction("显示主界面引导", self)
        show_main_guide_action.triggered.connect(self._show_main_guide_directly)
        tools_menu.addAction(show_main_guide_action)
        
        reset_guides_action = QAction("重置所有引导", self)
        reset_guides_action.triggered.connect(self._reset_all_guides)
        tools_menu.addAction(reset_guides_action)
        
        # 帮助菜单
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _import_from_excel(self):
        """
        从Excel导入密码记录
        """
        try:
            # 获取当前选中的所有者
            current_owner = self.layout_manager.get_selected_owner()
            if not current_owner:
                show_message(self, "错误", "无法获取当前选中的人员", QMessageBox.Warning)
                return
            
            # 如果正在编辑，先询问是否取消编辑
            if self.table_manager.editing_row >= 0:
                if not self._confirm_cancel_editing():
                    return
            
            # 导入Excel对话框
            # 使用绝对路径导入模块，防止导入错误
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from ui.dialogs.excel_dialog import ImportDialog
            
            # 使用当前选中的人员作为默认所有者，但允许在对话框中更改
            dialog = ImportDialog(self, default_owner=current_owner)
            
            # 连接导入完成信号
            dialog.import_completed.connect(self._handle_import_completed)
            
            # 显示对话框
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"导入Excel时出错: {str(e)}")
            logger.error(f"导入错误详情: {traceback.format_exc()}")
            show_message(self, "导入失败", f"导入Excel时出错: {str(e)}", QMessageBox.Warning)
        
    def _handle_import_completed(self, success, message, records):
        """
        处理Excel导入完成事件
        
        Args:
            success (bool): 导入是否成功
            message (str): 导入结果消息
            records (List[List[str]]): 导入的记录列表
        """
        if success:
            # 获取当前所有者
            current_owner = self.layout_manager.get_selected_owner()
            
            try:
                # 导入密码管理器模块
                import sys
                import os
                import traceback
                
                # 获取当前文件的绝对路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                
                # 获取项目根目录，向上两级
                root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
                
                # 将根目录添加到Python路径
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)
                    
                # 导入密码管理器模块
                from core.password import password_manager
                
                # 记录导入结果
                logging.info(f"Excel导入成功: {message}")
                logging.info(f"导入记录数: {len(records)}")
                
                # 获取现有数据
                existing_records = password_manager.get_passwords_by_owner(current_owner)
                
                # 确认是否替换
                is_replace_mode = True
                if existing_records:
                    is_replace_mode = QMessageBox.question(
                        self, 
                        "导入模式确认", 
                        f"您已有 {len(existing_records)} 条记录。您希望:\n\n" +
                        "点击 [是] 替换现有记录\n" +
                        "点击 [否] 追加到现有记录",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    ) == QMessageBox.Yes
                
                if is_replace_mode:
                    # 替换模式：直接用导入的记录替换现有记录
                    result = password_manager.db.set(current_owner, records)
                    if not result:
                        raise Exception("保存数据失败")
                    
                    # 刷新表格
                    self.table_manager.load_passwords(current_owner)
                    self.statusBar().showMessage(f"成功导入并替换 {len(records)} 条记录")
                else:
                    # 追加模式：添加导入的记录到现有记录
                    added_count = 0
                    for record in records:
                        # 使用add_password添加记录
                        result, err_msg = password_manager.add_password(current_owner, record)
                        if result:
                            added_count += 1
                        else:
                            logging.error(f"添加记录失败: {err_msg}")
                    
                    # 刷新表格
                    self.table_manager.load_passwords(current_owner)
                    self.statusBar().showMessage(f"成功导入并追加 {added_count} 条记录")
                
                # 记录到审计日志
                try:
                    from features.audit.audit_log import AuditLogger
                    
                    audit_logger = AuditLogger()
                    mode = "replace" if is_replace_mode else "append"
                    audit_logger.log_operation(
                        operation_type="import",
                        result="success",
                        details=f"从Excel导入 {len(records)} 条记录 ({mode}模式)",
                        user=self.username,
                        target=current_owner
                    )
                except Exception as e:
                    logging.error(f"记录审计日志时出错: {str(e)}")
                
            except Exception as e:
                logging.error(f"处理导入记录时出错: {str(e)}")
                logging.error(traceback.format_exc())
                QMessageBox.warning(self, "导入错误", f"处理导入记录时出错: {str(e)}")
        else:
            # 导入失败
            logging.error(f"Excel导入失败: {message}")
            QMessageBox.warning(self, "导入失败", message)

    def _export_to_excel(self):
        """导出密码记录到Excel文件（支持单人和多人）"""
        try:
            # 如果必要，动态调整Python系统路径以找到excel_dialog模块
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
            
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            # 导入多人员导出对话框
            from ui.dialogs.excel_dialog import MultiExportDialog
                
            # 显示导出对话框（使用多人导出对话框，已预选当前人员）
            export_dlg = MultiExportDialog(self, preselect_current=True)
            export_dlg.exec_()
            
        except ImportError as e:
            logger.error(f"导入MultiExportDialog模块失败: {str(e)}")
            QMessageBox.critical(self, "导出失败", f"缺少Excel导出模块: {str(e)}")
        except Exception as e:
            logger.error(f"导出Excel出错: {traceback.format_exc()}")
            QMessageBox.critical(self, "导出错误", f"导出密码记录时出错: {str(e)}")
            
    def _confirm_cancel_editing(self) -> bool:
        """
        确认是否取消编辑
        
        Returns:
            bool: 是否确认取消
        """
        result = QMessageBox.question(
            self,
            "取消编辑",
            "当前正在编辑，执行此操作将丢失未保存的更改。是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            self.table_manager.cancel_editing()
            return True
        
        return False

    def _show_main_guide_directly(self):
        """直接显示主界面功能引导，无论设置状态如何"""
        # 临时设置强制显示标志
        self.force_walkthrough = True
        
        # 获取关键UI元素
        target_widgets = {
            "owners_list": self.layout_manager.owner_list_widget,
            "password_table": self.layout_manager.password_table,
            "search_edit": self.layout_manager.search_edit,
            "action_buttons": self.layout_manager.splitter,
            "toolbar": self.layout_manager.toolbar
        }
        
        # 启动步骤引导
        start_walkthrough("main_features", self, target_widgets)
        
        # 清除强制显示标志
        self.force_walkthrough = False


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