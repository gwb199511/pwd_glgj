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
import pymysql
import time

from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QDialogButtonBox
from PyQt5.QtGui import QFont, QCursor, QIcon
from PyQt5.QtCore import Qt, QTimer

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

from config import LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_FORMAT, FONT_FAMILY, DATA_DIR, COLORS, APP_ICON_FILE
from ui.login.login_ui import LoginUI
from ui.password_manager.password_manager_ui import PasswordManagerUI
from core.user_settings import user_settings
from core.db_user_settings import db_user_settings
from core.db_manager import db_manager

# 添加ui组件的导入
from ui.components.ui_components import ModernButton, ModernLabel, HorizontalLine, show_message


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


def check_database_connection():
    """
    检查数据库连接状态，直接尝试连接数据库而不使用连接池
    
    Returns:
        Tuple[bool, str]: 连接状态和错误消息
    """
    try:
        # 获取数据库配置
        db_config = db_manager.get_config()
        
        logging.info("开始直接测试数据库连接...")
        # 设置连接超时更短，避免长时间等待
        connect_timeout = 3
        logging.info(f"连接目标: {db_config['host']}:{db_config['port']}/{db_config['database']}, 超时: {connect_timeout}秒")
        
        try:
            # 直接创建一个新连接，不使用连接池
            conn = pymysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                charset='utf8mb4',
                connect_timeout=connect_timeout  # 短超时时间，避免长时间等待
            )
            
            # 测试连接
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test_value")
                result = cursor.fetchone()
            
            # 关闭连接
            conn.close()
            
            # 验证结果，同时兼容字典和元组
            if result:
                # 如果结果存在，即连接成功
                logging.info("数据库连接测试成功")
                return True, ""
            else:
                # 没有结果，但也没有抛出异常
                logging.warning("数据库连接测试：查询返回空结果")
                return False, "连接建立但查询返回空结果"
        except pymysql.Error as e:
            error_code = getattr(e, 'args', [None])[0]
            if error_code == 2003:  # Can't connect to MySQL server
                error_message = f"无法连接到数据库服务器({db_config['host']}:{db_config['port']}): {str(e)}"
            elif error_code == 1045:  # Access denied
                error_message = f"访问被拒绝: 用户名或密码错误"
            elif error_code == 1049:  # Unknown database
                error_message = f"数据库不存在: {db_config['database']}"
            else:
                error_message = f"数据库连接错误: {str(e)}"
            
            logging.error(error_message)
            return False, error_message
    except Exception as e:
        error_message = f"检查数据库连接时发生异常: {str(e)}"
        logging.error(error_message)
        logging.error(traceback.format_exc())
        return False, error_message


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


def show_database_error(app, message):
    """
    显示数据库错误对话框
    
    Args:
        app: QApplication实例
        message: 错误消息
        
    Returns:
        str: 用户选择的操作("retry", "config", "quit")
    """
    # 导入必要的模块
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit
    from PyQt5.QtCore import Qt
    from ui.components.ui_components import ModernButton, ModernLabel, HorizontalLine
    from config import COLORS
    from datetime import datetime
    from core.db_manager import db_manager
    
    # 创建一个完全模态的对话框
    dialog = QDialog(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
    dialog.setWindowTitle("数据库连接错误")
    dialog.setFixedSize(500, 400)  # 固定大小，避免调整问题
    dialog.setModal(True)  # 确保对话框是模态的
    
    # 主布局
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)
    
    # 标题
    title_label = ModernLabel("无法连接到数据库服务器", font_size=12, bold=True, color=COLORS["danger"])
    title_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(title_label)
    
    # 分隔线
    layout.addWidget(HorizontalLine())
    
    # 错误信息
    error_msg = ModernLabel(
        "程序无法连接到数据库，这会导致大部分功能不可用。\n"
        "您可以选择重试连接、修改连接信息或退出程序。",
        font_size=10
    )
    error_msg.setWordWrap(True)
    error_msg.setAlignment(Qt.AlignCenter)
    layout.addWidget(error_msg)
    layout.addSpacing(10)
    
    # 技术详情标签
    details_label = ModernLabel("技术详情：", font_size=10, bold=True, color=COLORS["secondary"])
    layout.addWidget(details_label)
    
    # 详细错误信息
    detailed_text = f"""错误信息: {message}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据库参数: {db_manager.config['host']}:{db_manager.config['port']}/{db_manager.config['database']}

可能的原因:
1. 数据库服务器未启动或不可访问
2. 防火墙阻止了连接
3. 数据库服务凭据错误
4. 网络连接问题

如果您确信数据库服务器已正确配置且运行正常，可能是连接配置错误，请使用"修改连接信息"按钮进行调整。"""
    
    details_text = QTextEdit()
    details_text.setPlainText(detailed_text)
    details_text.setReadOnly(True)
    details_text.setFont(QFont(FONT_FAMILY, 9))
    details_text.setStyleSheet(f"""
        QTextEdit {{
            background-color: {COLORS["light"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
            padding: 8px;
        }}
    """)
    layout.addWidget(details_text)
    
    # 按钮区域
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    
    retry_button = ModernButton("重试连接", color=COLORS["primary"])
    config_button = ModernButton("修改连接信息", color=COLORS["info"])
    quit_button = ModernButton("退出程序", color=COLORS["danger"])
    
    button_layout.addWidget(retry_button)
    button_layout.addWidget(config_button)
    button_layout.addWidget(quit_button)
    layout.addLayout(button_layout)
    
    # 设置对话框样式
    dialog.setStyleSheet(f"""
        QDialog {{
            background-color: white;
            border: 1px solid {COLORS["border"]};
            border-radius: 5px;
        }}
    """)
    
    # 结果变量
    result = ["quit"]  # 默认为退出
    
    # 按钮点击处理
    def on_retry():
        result[0] = "retry"
        dialog.accept()
    
    def on_config():
        result[0] = "config"
        dialog.accept()
    
    def on_quit():
        result[0] = "quit"
        dialog.accept()
    
    retry_button.clicked.connect(on_retry)
    config_button.clicked.connect(on_config)
    quit_button.clicked.connect(on_quit)
    
    # 显示对话框
    dialog.exec_()
    
    return result[0]


def load_storage_type():
    """
    在PyInstaller环境中从storage_type.conf加载存储类型配置
    """
    try:
        import sys
        import os
        import config
        
        # 判断是否在PyInstaller环境中
        if getattr(sys, 'frozen', False):
            # 使用程序所在目录的data子目录
            base_dir = os.path.dirname(sys.executable)
            storage_file = os.path.join(base_dir, 'data', 'storage_type.conf')
            
            if os.path.exists(storage_file):
                logging.info(f"在PyInstaller环境中找到存储类型配置文件: {storage_file}")
                try:
                    with open(storage_file, 'r', encoding='utf-8') as f:
                        storage_type = f.read().strip()
                    
                    if storage_type in ("local", "mysql"):
                        logging.info(f"从配置文件加载存储类型: {storage_type}")
                        config.STORAGE_TYPE = storage_type
                    else:
                        logging.warning(f"配置文件中的存储类型无效: {storage_type}，使用默认值")
                except Exception as e:
                    logging.error(f"读取存储类型配置文件时出错: {str(e)}")
        else:
            logging.debug("非PyInstaller环境，不需要额外加载存储类型配置")
    except Exception as e:
        logging.error(f"加载存储类型时出错: {str(e)}")
        logging.error(traceback.format_exc())


def main():
    """
    主函数，程序入口点
    """
    # 加载存储类型配置（在PyInstaller环境中）
    load_storage_type()
    
    # 设置日志系统
    setup_logging()
    
    # 导入必需的组件
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
    from PyQt5.QtCore import Qt
    from ui.components.ui_components import ModernButton, ModernLabel, HorizontalLine, show_message
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    try:
        from PyQt5.QtGui import QIcon
        if os.path.exists(APP_ICON_FILE):
            app_icon = QIcon(APP_ICON_FILE)
            app.setWindowIcon(app_icon)
            logging.info(f"已成功加载应用程序图标: {APP_ICON_FILE}")
        else:
            logging.warning(f"应用程序图标文件不存在: {APP_ICON_FILE}")
    except Exception as e:
        logging.warning(f"设置应用程序图标时出错: {str(e)}")
    
    # 设置全局字体
    font = QFont(FONT_FAMILY)
    app.setFont(font)
    
    # 导入环境变量状态
    disable_auto_connect = os.environ.get('PM_DISABLE_AUTO_DB_CONNECT', '0') == '1'
    logging.info(f"数据库自动连接状态: {'已禁用' if disable_auto_connect else '已启用'}")
    
    # 创建错误消息处理函数，确保任何错误都能在GUI中显示
    def show_critical_error(title, message, details=None):
        # 创建自定义对话框
        dialog = QDialog(None, Qt.WindowStaysOnTopHint)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(450)
        dialog.setMinimumHeight(250)
        dialog.setModal(True)
        
        # 主布局
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 添加标题
        title_label = ModernLabel(title, font_size=12, bold=True, color=COLORS["danger"])
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(5)
        layout.addWidget(HorizontalLine())
        layout.addSpacing(5)
        
        # 错误消息
        msg_label = ModernLabel(message, font_size=10, color=COLORS["danger"])
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        
        # 如果有详细信息，添加详细信息区域
        if details:
            layout.addSpacing(10)
            details_label = ModernLabel("详细信息:", font_size=9, bold=True, color=COLORS["secondary"])
            layout.addWidget(details_label)
            
            details_text = QTextEdit()
            details_text.setPlainText(details)
            details_text.setReadOnly(True)
            details_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {COLORS["light"]};
                    border: 1px solid {COLORS["border"]};
                    border-radius: 4px;
                    padding: 8px;
                    font-family: {FONT_FAMILY};
                    font-size: 9pt;
                }}
            """)
            layout.addWidget(details_text)
        
        layout.addSpacing(15)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = ModernButton("确定", color=COLORS["primary"])
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 设置对话框样式
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: white;
                border: 1px solid {COLORS["border"]};
                border-radius: 5px;
            }}
        """)
        
        # 显示对话框
        dialog.exec_()
    
    # 检查数据库连接状态
    db_connected = False
    
    # 显式启用自动连接
    logging.info("准备尝试数据库连接...")
    
    # 安全启用自动连接
    try:
        db_manager.enable_auto_connect()
        logging.info("已启用数据库自动连接")
    except Exception as e:
        logging.error(f"启用数据库自动连接时发生错误: {str(e)}")
        show_critical_error(
            "数据库连接错误", 
            f"启用数据库连接时出错: {str(e)}",
            traceback.format_exc()
        )
    
    # 强制立即检查数据库连接
    try:
        # 直接测试数据库连接，不依赖连接池
        logging.info("开始检查数据库连接状态...")
        success, error_message = check_database_connection()
        
        if success:
            db_connected = True
            logging.info("数据库连接成功，继续启动程序")
        else:
            logging.error(f"无法连接到数据库: {error_message}")
            
            # 显示错误对话框
            action = show_database_error(app, error_message)
            
            if action == "retry":
                # 用户选择重试，手动进行重试循环
                while not db_connected:
                    logging.info("正在尝试重新连接数据库...")
                    
                    # 创建更美观的进度对话框，替换简单的QProgressDialog
                    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel
                    
                    # 创建自定义对话框
                    connecting_dialog = QDialog(None, Qt.WindowStaysOnTopHint)
                    connecting_dialog.setWindowTitle("正在重新连接")
                    connecting_dialog.setFixedSize(350, 150)
                    connecting_dialog.setModal(True)
                    
                    # 设置主布局
                    layout = QVBoxLayout(connecting_dialog)
                    layout.setContentsMargins(20, 20, 20, 20)
                    
                    # 添加标题标签
                    title_label = ModernLabel("正在连接到数据库...", font_size=11, bold=True, color=COLORS["primary"])
                    layout.addWidget(title_label)
                    
                    # 添加描述标签
                    desc_label = ModernLabel("请稍候，系统正在尝试重新连接到数据库", font_size=9)
                    desc_label.setWordWrap(True)
                    layout.addWidget(desc_label)
                    
                    layout.addSpacing(10)
                    
                    # 添加进度条
                    progress_bar = QProgressBar()
                    progress_bar.setRange(0, 0)  # 不确定的进度条
                    progress_bar.setMinimumHeight(15)
                    progress_bar.setStyleSheet(f"""
                        QProgressBar {{
                            border: 1px solid {COLORS["border"]};
                            border-radius: 4px;
                            text-align: center;
                            background-color: {COLORS["light"]};
                        }}
                        QProgressBar::chunk {{
                            background-color: {COLORS["primary"]};
                            border-radius: 3px;
                        }}
                    """)
                    layout.addWidget(progress_bar)
                    
                    # 显示对话框但不阻塞
                    connecting_dialog.show()
                    
                    # 确保UI更新
                    app.processEvents()
                    
                    # 进行重试
                    success, error_message = check_database_connection()
                    
                    # 关闭对话框
                    connecting_dialog.close()
                    app.processEvents()
                    
                    if success:
                        db_connected = True
                        logging.info("数据库重新连接成功")
                        
                        # 显示更美观的成功消息对话框
                        success_dialog = QDialog(None, Qt.WindowStaysOnTopHint)
                        success_dialog.setWindowTitle("连接成功")
                        success_dialog.setFixedSize(350, 180)
                        success_dialog.setModal(True)
                        
                        layout = QVBoxLayout(success_dialog)
                        layout.setContentsMargins(20, 20, 20, 20)
                        
                        # 添加标题标签
                        title_label = ModernLabel("数据库连接成功", font_size=12, bold=True, color=COLORS["success"])
                        title_label.setAlignment(Qt.AlignCenter)
                        layout.addWidget(title_label)
                        
                        layout.addSpacing(5)
                        layout.addWidget(HorizontalLine())
                        layout.addSpacing(10)
                        
                        # 添加成功消息
                        success_msg = ModernLabel(
                            "已成功连接到数据库服务器，系统将继续启动。",
                            font_size=10
                        )
                        success_msg.setWordWrap(True)
                        success_msg.setAlignment(Qt.AlignCenter)
                        layout.addWidget(success_msg)
                        
                        layout.addStretch()
                        
                        # 添加确定按钮
                        button_layout = QHBoxLayout()
                        button_layout.addStretch()
                        
                        ok_button = ModernButton("确定", color=COLORS["primary"])
                        ok_button.clicked.connect(success_dialog.accept)
                        button_layout.addWidget(ok_button)
                        
                        button_layout.addStretch()
                        layout.addLayout(button_layout)
                        
                        # 显示对话框
                        success_dialog.exec_()
                        break
                    else:
                        # 连接失败，询问用户是否重试、修改配置或退出
                        action = show_database_error(app, error_message)
                        
                        if action == "config":
                            # 用户选择修改连接信息，退出重试循环
                            break
                        elif action == "quit":
                            logging.info("用户选择退出程序")
                            sys.exit(0)
                        # 如果是retry则继续循环
            
            elif action == "config":
                # 用户选择修改连接信息
                logging.info("用户选择修改数据库连接信息")
                
                # 导入MySQL配置对话框
                from ui.dialogs.mysql_config_dialog import MySQLConfigDialog
                
                # 创建配置对话框
                config_dialog = MySQLConfigDialog(None)
                
                # 定义配置保存后的回调函数
                def on_config_saved():
                    # 在函数内部导入需要的组件，使用不同的变量名避免作用域问题
                    from PyQt5.QtWidgets import QDialog as ConfigDialog
                    from PyQt5.QtWidgets import QVBoxLayout, QProgressBar
                    from PyQt5.QtCore import Qt
                    from ui.components.ui_components import ModernLabel
                    
                    logging.info("数据库配置已保存，尝试使用新配置连接")
                    nonlocal db_connected
                    
                    # 使用不同名称的QDialog
                    connecting_dialog = ConfigDialog(None)
                    connecting_dialog.setWindowFlags(connecting_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
                    connecting_dialog.setWindowTitle("正在连接")
                    connecting_dialog.setFixedSize(350, 150)
                    connecting_dialog.setModal(True)
                    
                    # 设置主布局
                    layout = QVBoxLayout(connecting_dialog)
                    layout.setContentsMargins(20, 20, 20, 20)
                    
                    # 添加标题标签
                    title_label = ModernLabel("正在使用新配置连接...", font_size=11, bold=True)
                    layout.addWidget(title_label)
                    
                    # 添加进度条
                    progress_bar = QProgressBar()
                    progress_bar.setRange(0, 0)  # 不确定的进度条
                    progress_bar.setStyleSheet(f"""
                        QProgressBar {{
                            border: 1px solid {COLORS["border"]};
                            border-radius: 4px;
                            background-color: {COLORS["light"]};
                        }}
                        QProgressBar::chunk {{
                            background-color: {COLORS["primary"]};
                            border-radius: 3px;
                        }}
                    """)
                    layout.addWidget(progress_bar)
                    
                    # 显示对话框但不阻塞
                    connecting_dialog.show()
                    app.processEvents()
                    
                    # 测试连接
                    success, error_message = check_database_connection()
                    
                    # 关闭进度对话框
                    connecting_dialog.close()
                    
                    if success:
                        db_connected = True
                        logging.info("使用新配置连接数据库成功")
                        
                        # 显示成功消息
                        show_message(
                            None, 
                            "连接成功", 
                            "已成功连接到数据库服务器，系统将继续启动。",
                            QMessageBox.Information
                        )
                    else:
                        # 连接失败，回到主流程
                        logging.error(f"使用新配置连接数据库失败: {error_message}")
                        
                        # 询问用户是否继续尝试
                        action = show_database_error(app, error_message)
                        if action == "retry":
                            # 继续尝试连接
                            while not db_connected:
                                # 重复之前的重试逻辑...
                                # 这里省略重复代码，实际应用中应该将重试逻辑提取为单独的函数
                                pass
                        elif action == "config":
                            # 再次显示配置对话框
                            config_dialog = MySQLConfigDialog(None)
                            config_dialog.exec_()
                            on_config_saved()  # 递归调用，处理新的配置
                        else:  # quit
                            sys.exit(0)
                
                # 连接配置对话框的确认信号
                config_dialog.accepted.connect(on_config_saved)
                
                # 显示配置对话框
                if config_dialog.exec_() == QDialog.Rejected:
                    # 用户取消了配置
                    logging.info("用户取消了数据库配置")
                    
                    # 询问用户是否继续尝试连接
                    action = show_database_error(app, error_message)
                    if action == "retry":
                        # 用户选择重试
                        # 这里应该调用重试逻辑，但为了避免代码重复，可以简化处理
                        success, error_message = check_database_connection()
                        if success:
                            db_connected = True
                        else:
                            # 还是失败，退出程序
                            logging.error("重试连接失败，退出程序")
                            sys.exit(0)
                    elif action == "config":
                        # 用户再次选择配置，重新显示配置对话框
                        config_dialog = MySQLConfigDialog(None)
                        config_dialog.accepted.connect(on_config_saved)
                        config_dialog.exec_()
                    else:  # quit
                        sys.exit(0)
            
            elif action == "quit":
                logging.info("用户选择退出程序")
                sys.exit(0)
    except Exception as e:
        logging.error(f"检查数据库连接时发生异常: {str(e)}")
        logging.error(traceback.format_exc())
        # 捕获任何异常，显示错误对话框
        show_critical_error(
            "数据库连接错误", 
            f"检查数据库连接时出错: {str(e)}",
            traceback.format_exc()
        )
        action = show_database_error(app, str(e))
        if action == "quit":
            sys.exit(0)
    
    # 迁移用户设置（如果需要并且数据库已连接）
    if db_connected:
        migrate_user_settings_if_needed()
    
    # 确保用户设置模块已经初始化
    logging.info(f"初始化用户设置模块...")
    try:
        # 访问设置以触发初始化
        _ = user_settings.get("version", "未知")
        logging.info(f"用户设置模块已初始化")
    except Exception as e:
        logging.error(f"初始化用户设置模块时出错: {str(e)}")
        show_critical_error(
            "初始化错误", 
            f"初始化用户设置模块时出错: {str(e)}",
            traceback.format_exc()
        )

    # 检查是否有重置引导记录的命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--reset-guides":
        user_settings.reset_guides()
        logging.info("已重置引导记录")

    # 创建登录界面 - 移除db_connected参数
    login_window = LoginUI()  # 不再传递连接状态参数，因为已经移除离线模式支持
    
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