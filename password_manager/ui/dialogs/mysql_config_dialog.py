#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MySQL配置对话框模块，提供MySQL连接配置界面
"""

import logging
import threading
from typing import Tuple, Dict, Any, Optional
import traceback

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QSpinBox, QPushButton, 
                           QMessageBox, QApplication, QCheckBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread

from config import COLORS, FONT_FAMILY
from ui.components.ui_components import ModernButton, ModernLineEdit, ModernLabel, HorizontalLine, show_message
from core.db_manager import db_manager

# 配置日志
logger = logging.getLogger(__name__)


class MySQLConfigDialog(QDialog):
    """
    MySQL配置对话框
    
    提供配置MySQL连接参数的界面，支持测试连接和保存配置。
    """
    
    # 定义信号：存储模式变更信号
    storage_mode_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """
        初始化MySQL配置对话框
        
        Args:
            parent (QWidget, optional): 父控件. 默认为 None.
        """
        super().__init__(parent)
        self.setWindowTitle("MySQL连接配置")
        self.resize(500, 400)
        
        # 加载当前配置
        self.current_config = db_manager.get_config()
        
        # 初始化界面
        self.init_ui()
        
        # 加载配置到界面
        self.load_config_to_ui()
    
    def init_ui(self):
        """初始化界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 添加标题
        title_label = ModernLabel("MySQL数据库连接配置", font_size=14, bold=True)
        main_layout.addWidget(title_label)
        
        # 添加说明
        desc_label = ModernLabel("配置MySQL数据库连接参数，支持将数据存储方式从本地文件切换到MySQL数据库。", 
                               color=COLORS["secondary"])
        main_layout.addWidget(desc_label)
        
        # 添加水平分隔线
        main_layout.addWidget(HorizontalLine())
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # 主机
        self.host_input = ModernLineEdit(placeholder="数据库主机地址")
        form_layout.addRow(ModernLabel("主机:"), self.host_input)
        
        # 端口
        self.port_input = QSpinBox()
        self.port_input.setMinimum(1)
        self.port_input.setMaximum(65535)
        self.port_input.setValue(3306)
        self.port_input.setFixedHeight(30)
        form_layout.addRow(ModernLabel("端口:"), self.port_input)
        
        # 用户名
        self.user_input = ModernLineEdit(placeholder="数据库用户名")
        form_layout.addRow(ModernLabel("用户名:"), self.user_input)
        
        # 密码
        self.password_input = ModernLineEdit(placeholder="数据库密码", password_mode=True)
        form_layout.addRow(ModernLabel("密码:"), self.password_input)
        
        # 数据库名
        self.database_input = ModernLineEdit(placeholder="数据库名称")
        form_layout.addRow(ModernLabel("数据库:"), self.database_input)
        
        # 添加表单到主布局
        main_layout.addLayout(form_layout)
        
        # 添加水平分隔线
        main_layout.addWidget(HorizontalLine())
        
        # 添加按钮
        button_layout = QHBoxLayout()
        
        # 测试连接按钮
        self.test_button = ModernButton("测试连接", color=COLORS["info"])
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)
        
        # 初始化数据库按钮
        self.init_db_button = ModernButton("初始化数据库", color=COLORS["primary"])
        self.init_db_button.clicked.connect(self.initialize_database)
        button_layout.addWidget(self.init_db_button)
        
        # 取消按钮
        self.cancel_button = ModernButton("取消", color=COLORS["secondary"])
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # 保存按钮
        self.save_button = ModernButton("保存", color=COLORS["success"])
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)
        
        # 添加按钮布局到主布局
        main_layout.addLayout(button_layout)
        
        # 设置对话框布局
        self.setLayout(main_layout)
        
        # 设置连接
        self.connect_signals()
    
    def connect_signals(self):
        """连接信号"""
        # 当字段变化时更新按钮状态
        self.host_input.textChanged.connect(self.update_buttons_state)
        self.user_input.textChanged.connect(self.update_buttons_state)
        self.password_input.textChanged.connect(self.update_buttons_state)
        self.database_input.textChanged.connect(self.update_buttons_state)
    
    def update_buttons_state(self):
        """更新按钮状态"""
        # 检查是否所有必填字段都已填写
        has_required_fields = bool(
            self.host_input.text() and
            self.user_input.text() and
            self.database_input.text()
        )
        
        # 更新按钮状态
        self.test_button.setEnabled(has_required_fields)
        self.init_db_button.setEnabled(has_required_fields)
        self.save_button.setEnabled(has_required_fields)
    
    def load_config_to_ui(self):
        """加载配置到界面"""
        if self.current_config:
            self.host_input.setText(self.current_config.get('host', ''))
            self.port_input.setValue(self.current_config.get('port', 3306))
            self.user_input.setText(self.current_config.get('user', ''))
            self.password_input.setText(self.current_config.get('password', ''))
            self.database_input.setText(self.current_config.get('database', ''))
        
        # 更新按钮状态
        self.update_buttons_state()
    
    def get_config_from_ui(self) -> Dict[str, Any]:
        """
        从界面获取配置
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            'host': self.host_input.text().strip(),
            'port': self.port_input.value(),
            'user': self.user_input.text().strip(),
            'password': self.password_input.text().strip(),
            'database': self.database_input.text().strip()
        }
    
    def test_connection(self):
        """测试数据库连接"""
        # 获取配置
        config = self.get_config_from_ui()
        
        # 禁用按钮
        self.test_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # 更新按钮文本
        original_text = self.test_button.text()
        self.test_button.setText("正在连接...")
        
        # 使用简化的方法在主线程中处理
        # 创建工作线程
        def worker():
            # 更新配置
            success = False
            message = ""
            try:
                # 先应用配置但不测试连接
                db_manager.config = config.copy()
                # 重置连接尝试时间
                db_manager._last_connection_attempt = 0
                # 测试连接
                success, message = db_manager.test_connection()
            except Exception as e:
                success = False
                message = str(e)
                logger.error(f"测试连接时出错: {str(e)}")
                logger.error(traceback.format_exc())
            
            # 在主线程中更新UI (使用QApplication.processEvents而不是跨线程操作UI)
            return success, message
        
        try:
            # 直接在当前线程执行，避免线程问题
            success, message = worker()
            
            # 更新UI
            self.test_button.setText(original_text)
            self.test_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            
            # 显示结果
            if success:
                show_message(self, "连接成功", f"MySQL连接测试成功！\n{message}", QMessageBox.Information)
            else:
                show_message(self, "连接失败", f"MySQL连接测试失败：\n{message}", QMessageBox.Critical)
        except Exception as e:
            self.test_button.setText(original_text)
            self.test_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            show_message(self, "错误", f"测试连接时出错: {str(e)}", QMessageBox.Critical)
    
    def initialize_database(self):
        """初始化数据库和表结构"""
        # 获取配置
        config = self.get_config_from_ui()
        
        # 禁用按钮
        self.init_db_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # 更新按钮文本
        original_text = self.init_db_button.text()
        self.init_db_button.setText("正在初始化...")
        
        # 使用简化的方法在主线程中处理
        def worker():
            success = False
            message = ""
            try:
                # 更新配置
                db_manager.update_config(config)
                
                # 创建数据库
                logger.info(f"尝试创建/连接数据库: {config['database']} 在服务器: {config['host']}:{config['port']}")
                db_success, db_message = db_manager.create_database()
                
                if db_success:
                    logger.info(f"数据库创建/连接成功: {db_message}")
                    # 初始化表结构
                    logger.info("开始初始化表结构...")
                    table_success, table_message = db_manager.initialize_tables()
                    
                    # 如果表结构初始化成功，添加默认用户
                    if table_success:
                        logger.info("表结构初始化成功，开始创建默认用户...")
                        self._create_default_users()
                        logger.info("默认用户创建完成")
                    else:
                        logger.error(f"表结构初始化失败: {table_message}")
                    
                    success = table_success
                    message = table_message
                else:
                    logger.error(f"数据库创建/连接失败: {db_message}")
                    success = db_success
                    message = db_message
            except Exception as e:
                logger.error(f"初始化过程发生异常: {str(e)}")
                logger.error(traceback.format_exc())
                success = False
                message = f"初始化数据库时出错: {str(e)}"
                
            return success, message
        
        try:
            # 直接在当前线程执行，避免线程问题
            success, message = worker()
            
            # 更新UI
            self.init_db_button.setText(original_text)
            self.init_db_button.setEnabled(True)
            self.test_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            
            # 显示结果
            if success:
                show_message(self, "初始化成功", "数据库和表结构初始化成功！默认用户已创建，用户名：admin，密码：admin。", QMessageBox.Information)
            else:
                show_message(self, "初始化失败", f"数据库初始化失败：\n{message}", QMessageBox.Critical)
        except Exception as e:
            self.init_db_button.setText(original_text)
            self.init_db_button.setEnabled(True)
            self.test_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            show_message(self, "错误", f"初始化数据库时出错: {str(e)}", QMessageBox.Critical)
    
    def _create_default_users(self):
        """创建默认用户"""
        try:
            # 检查用户表中是否已存在admin用户
            check_sql = "SELECT * FROM users WHERE username = 'admin'"
            result = db_manager.execute_query(check_sql)
            
            if not result:
                # 创建默认admin用户
                insert_sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
                db_manager.execute_insert(insert_sql, ("admin", "admin"))
                logger.info("创建了默认管理员用户: admin")
                
            # 确保三个固定人员的数据存在
            fixed_owners = ["徐国明", "高文彬", "石帆"]
            for owner in fixed_owners:
                # 检查密码表中是否已存在此人员的记录
                check_sql = "SELECT COUNT(*) as count FROM passwords WHERE owner = %s"
                result = db_manager.execute_query(check_sql, (owner,))
                
                # 如果没有记录，添加一条空记录
                if result and result[0]['count'] == 0:
                    insert_sql = """
                    INSERT INTO passwords 
                    (owner, project_name, func_desc, ip_address, account, password, area, network_type, other_info) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (owner, "示例项目", "功能说明", "127.0.0.1", "username", "password", "北京", "内网", "备注信息")
                    db_manager.execute_insert(insert_sql, params)
                    logger.info(f"为人员 {owner} 创建了示例数据")
                    
            logger.info("默认数据初始化完成")
            return True
        except Exception as e:
            logger.error(f"创建默认用户时出错: {str(e)}")
            logger.exception(e)
            return False
    
    def save_config(self):
        """保存配置"""
        # 获取配置
        config = self.get_config_from_ui()
        
        try:
            # 保存配置，不进行连接测试
            if not db_manager._save_config(config):
                show_message(self, "保存失败", "保存配置文件失败，请检查文件权限或磁盘空间", QMessageBox.Critical)
                return
                
            # 更新内部配置对象
            db_manager.config = config
            
            # 关闭现有连接池
            if db_manager._connection_pool is not None:
                db_manager._connection_pool.close_all()
                db_manager._connection_pool = None
            
            # 尝试进行测试连接，但即使失败也继续
            success, message = db_manager.test_connection()
            if not success:
                logger.warning(f"配置已保存，但连接测试失败: {message}")
                # 显示警告，但不阻止保存
                show_message(self, "配置已保存", f"配置已保存，但连接测试失败：\n{message}\n\n您可能需要初始化数据库。", QMessageBox.Warning)
            
            # 设置存储类型为mysql
            storage_type = "mysql"
            
            # 修改配置文件中的存储模式
            self._update_storage_type(storage_type)
            
            # 发送存储模式变更信号
            self.storage_mode_changed.emit(storage_type)
            
            # 关闭对话框
            self.accept()
        except Exception as e:
            error_message = f"保存配置时出错: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            show_message(self, "保存失败", error_message, QMessageBox.Critical)
    
    def _update_storage_type(self, storage_type: str) -> None:
        """
        更新配置文件中的存储类型
        
        Args:
            storage_type (str): 存储类型，"local"或"mysql"
        """
        try:
            import config
            
            # 直接修改内存中的配置，而不是修改文件
            config.STORAGE_TYPE = storage_type
            logger.info(f"存储类型已更新为: {storage_type}")
            
            # 尝试修改配置文件，但如果失败也不影响程序运行
            try:
                import os
                import sys
                
                # 判断是否在PyInstaller环境中
                if getattr(sys, 'frozen', False):
                    logger.info("检测到PyInstaller环境，跳过修改配置文件")
                    return
                    
                # 直接使用已导入的config模块的文件路径
                config_file = os.path.abspath(config.__file__)
                logger.info(f"使用配置文件路径: {config_file}")
                
                # 确保文件存在并且可写
                if os.path.exists(config_file) and os.access(config_file, os.W_OK):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 替换存储类型
                    import re
                    new_content = re.sub(
                        r'STORAGE_TYPE\s*=\s*"[^"]*"',
                        f'STORAGE_TYPE = "{storage_type}"',
                        content
                    )
                    
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    logger.info(f"配置文件已更新")
                else:
                    logger.warning(f"配置文件不存在或不可写: {config_file}")
            except Exception as e:
                logger.warning(f"更新配置文件时出错，但不影响程序运行: {str(e)}")
                
        except Exception as e:
            logger.error(f"更新存储类型时出错: {str(e)}")
            show_message(self, "配置更新失败", f"更新存储类型时出错: {str(e)}", QMessageBox.Critical)


def main():
    """测试函数"""
    import sys
    app = QApplication(sys.argv)
    dialog = MySQLConfigDialog()
    result = dialog.exec_()
    print(f"Dialog result: {result}")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.DEBUG)
    main() 