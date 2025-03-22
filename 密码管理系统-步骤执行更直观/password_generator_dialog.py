#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码生成器对话框模块，提供密码生成的用户界面
"""

import logging
import sys
from typing import List, Dict, Optional, Union

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QSpinBox, QCheckBox, QGroupBox, QRadioButton, 
    QComboBox, QListWidget, QProgressBar, QApplication, 
    QButtonGroup, QGridLayout, QFrame, QSizePolicy, QAction,
    QMenu, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QClipboard, QFont, QColor, QPalette

from password_generator import PasswordGenerator
from ui_components import show_message

# 配置日志
logger = logging.getLogger(__name__)


class PasswordStrengthIndicator(QProgressBar):
    """
    密码强度指示器
    
    显示密码强度的进度条
    """
    
    def __init__(self, parent=None):
        """
        初始化密码强度指示器
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setTextVisible(True)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setFormat("%v - %p%")
        
        # 设置样式
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            
            QProgressBar::chunk {
                background-color: #3add36;
                width: 1px;
            }
        """)
    
    def update_strength(self, strength: str, entropy: float):
        """
        更新密码强度显示
        
        Args:
            strength (str): 密码强度级别
            entropy (float): 密码熵值
        """
        # 基于熵值设置进度条值
        value = min(100, int(entropy * 1.25))  # 映射到0-100范围
        self.setValue(value)
        
        # 根据强度设置颜色
        color = "#ff4444"  # 红色 - 弱
        text = f"弱 ({entropy:.1f} 位)"
        
        if strength == '中':
            color = "#ffaa33"  # 橙色 - 中
            text = f"中等 ({entropy:.1f} 位)"
        elif strength == '强':
            color = "#33aa33"  # 绿色 - 强
            text = f"强 ({entropy:.1f} 位)"
        elif strength == '非常强':
            color = "#3333ff"  # 蓝色 - 非常强
            text = f"非常强 ({entropy:.1f} 位)"
        
        # 设置文本和颜色
        self.setFormat(text)
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #bbb;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }}
            
            QProgressBar::chunk {{
                background-color: {color};
                width: 1px;
            }}
        """)


class PasswordGeneratorDialog(QDialog):
    """
    密码生成器对话框
    
    提供用户友好的界面生成各种类型的密码
    """
    
    def __init__(self, parent=None):
        """
        初始化密码生成器对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.password_generator = PasswordGenerator()
        self.generated_passwords = []
        
        self.init_ui()
        
    def init_ui(self):
        """
        初始化用户界面
        """
        # 设置窗口标题和大小
        self.setWindowTitle("密码生成器")
        self.resize(600, 500)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 密码长度选择区域
        length_group = QGroupBox("密码长度")
        length_layout = QHBoxLayout()
        
        # 预设长度选择
        self.length_preset_group = QButtonGroup(self)
        
        self.radio_8 = QRadioButton("8 位")
        self.radio_16 = QRadioButton("16 位")
        self.radio_32 = QRadioButton("32 位")
        self.radio_custom = QRadioButton("自定义")
        
        self.length_preset_group.addButton(self.radio_8)
        self.length_preset_group.addButton(self.radio_16)
        self.length_preset_group.addButton(self.radio_32)
        self.length_preset_group.addButton(self.radio_custom)
        
        # 默认选择16位
        self.radio_16.setChecked(True)
        
        # 自定义长度输入框
        self.length_spinbox = QSpinBox()
        self.length_spinbox.setRange(1, 128)
        self.length_spinbox.setValue(16)
        self.length_spinbox.setEnabled(False)  # 初始禁用
        
        # 添加到布局中
        length_layout.addWidget(self.radio_8)
        length_layout.addWidget(self.radio_16)
        length_layout.addWidget(self.radio_32)
        length_layout.addWidget(self.radio_custom)
        length_layout.addWidget(self.length_spinbox)
        
        length_group.setLayout(length_layout)
        
        # 字符类型选择区域
        char_group = QGroupBox("字符类型")
        char_layout = QGridLayout()
        
        self.check_lowercase = QCheckBox("小写字母 (a-z)")
        self.check_uppercase = QCheckBox("大写字母 (A-Z)")
        self.check_digits = QCheckBox("数字 (0-9)")
        self.check_symbols = QCheckBox("特殊符号 (!@#$...)")
        self.check_exclude_similar = QCheckBox("排除相似字符 (Il1O0o)")
        
        # 默认全选
        self.check_lowercase.setChecked(True)
        self.check_uppercase.setChecked(True)
        self.check_digits.setChecked(True)
        self.check_symbols.setChecked(True)
        
        char_layout.addWidget(self.check_lowercase, 0, 0)
        char_layout.addWidget(self.check_uppercase, 0, 1)
        char_layout.addWidget(self.check_digits, 1, 0)
        char_layout.addWidget(self.check_symbols, 1, 1)
        char_layout.addWidget(self.check_exclude_similar, 2, 0, 1, 2)
        
        char_group.setLayout(char_layout)
        
        # 密码生成区域
        gen_group = QGroupBox("密码生成")
        gen_layout = QVBoxLayout()
        
        # 单个密码生成
        single_pass_layout = QHBoxLayout()
        single_pass_layout.addWidget(QLabel("生成的密码:"))
        
        self.password_edit = QLineEdit()
        self.password_edit.setReadOnly(True)
        self.password_edit.setPlaceholderText("点击生成按钮生成密码")
        
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setEnabled(False)
        
        single_pass_layout.addWidget(self.password_edit)
        single_pass_layout.addWidget(self.copy_btn)
        
        # 密码强度
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("密码强度:"))
        
        self.strength_indicator = PasswordStrengthIndicator()
        strength_layout.addWidget(self.strength_indicator)
        
        # 生成多个密码
        multi_label_layout = QHBoxLayout()
        multi_label_layout.addWidget(QLabel("生成多个密码:"))
        
        self.count_spinbox = QSpinBox()
        self.count_spinbox.setRange(1, 20)
        self.count_spinbox.setValue(5)
        
        multi_label_layout.addWidget(self.count_spinbox)
        multi_label_layout.addStretch()
        
        # 密码历史列表
        self.password_list = QListWidget()
        self.password_list.setAlternatingRowColors(True)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("生成单个密码")
        self.generate_multi_btn = QPushButton("生成多个密码")
        self.clear_btn = QPushButton("清空历史")
        self.clear_btn.setEnabled(False)
        
        btn_layout.addWidget(self.generate_btn)
        btn_layout.addWidget(self.generate_multi_btn)
        btn_layout.addWidget(self.clear_btn)
        
        # 添加所有子布局到生成区域
        gen_layout.addLayout(single_pass_layout)
        gen_layout.addLayout(strength_layout)
        gen_layout.addLayout(multi_label_layout)
        gen_layout.addWidget(self.password_list)
        gen_layout.addLayout(btn_layout)
        
        gen_group.setLayout(gen_layout)
        
        # 添加组到主布局
        main_layout.addWidget(length_group)
        main_layout.addWidget(char_group)
        main_layout.addWidget(gen_group)
        
        # 设置对话框布局
        self.setLayout(main_layout)
        
        # 连接信号和槽
        self.connect_signals()
        
    def connect_signals(self):
        """
        连接信号和槽
        """
        # 长度选择逻辑
        self.radio_8.toggled.connect(lambda: self.on_length_preset_changed(8))
        self.radio_16.toggled.connect(lambda: self.on_length_preset_changed(16))
        self.radio_32.toggled.connect(lambda: self.on_length_preset_changed(32))
        self.radio_custom.toggled.connect(self.on_custom_length_toggled)
        
        # 生成按钮
        self.generate_btn.clicked.connect(self.generate_password)
        self.generate_multi_btn.clicked.connect(self.generate_multiple_passwords)
        
        # 复制按钮
        self.copy_btn.clicked.connect(self.copy_password)
        
        # 密码列表双击复制
        self.password_list.itemDoubleClicked.connect(self.copy_from_list)
        
        # 清空按钮
        self.clear_btn.clicked.connect(self.clear_history)
        
        # 右键菜单
        self.password_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.password_list.customContextMenuRequested.connect(self.show_context_menu)
        
    def on_length_preset_changed(self, length):
        """
        处理预设长度变化
        
        Args:
            length (int): 预设密码长度
        """
        if self.sender().isChecked():
            self.length_spinbox.setValue(length)
            self.length_spinbox.setEnabled(False)
    
    def on_custom_length_toggled(self, checked):
        """
        处理自定义长度选择
        
        Args:
            checked (bool): 是否勾选自定义长度
        """
        self.length_spinbox.setEnabled(checked)
    
    def get_current_settings(self) -> Dict[str, Union[int, bool]]:
        """
        获取当前设置
        
        Returns:
            Dict[str, Union[int, bool]]: 当前设置参数
        """
        # 获取密码长度
        length = self.length_spinbox.value()
        
        # 获取字符类型设置
        use_lowercase = self.check_lowercase.isChecked()
        use_uppercase = self.check_uppercase.isChecked()
        use_digits = self.check_digits.isChecked()
        use_symbols = self.check_symbols.isChecked()
        exclude_similar = self.check_exclude_similar.isChecked()
        
        # 确保至少选择了一种字符类型
        if not any([use_lowercase, use_uppercase, use_digits, use_symbols]):
            # 如果没有选择任何类型，默认使用小写字母
            use_lowercase = True
            self.check_lowercase.setChecked(True)
        
        return {
            'length': length,
            'use_lowercase': use_lowercase,
            'use_uppercase': use_uppercase,
            'use_digits': use_digits,
            'use_symbols': use_symbols,
            'exclude_similar': exclude_similar
        }
    
    def generate_password(self):
        """
        生成单个密码
        """
        try:
            # 获取当前设置
            settings = self.get_current_settings()
            
            # 生成密码
            password = self.password_generator.generate_password(**settings)
            
            # 更新界面
            self.password_edit.setText(password)
            self.copy_btn.setEnabled(True)
            
            # 评估密码强度
            strength_result = self.password_generator.evaluate_password_strength(password)
            self.strength_indicator.update_strength(
                strength_result['strength'], 
                strength_result['entropy']
            )
            
            # 添加到历史记录
            self.add_to_history(password)
            
            logger.debug(f"生成了长度为{settings['length']}的密码")
            
        except Exception as e:
            logger.error(f"生成密码时出错: {str(e)}")
            show_message(
                self,
                "生成错误",
                f"生成密码时出错: {str(e)}",
                QMessageBox.Warning
            )
    
    def generate_multiple_passwords(self):
        """
        生成多个密码
        """
        try:
            # 获取当前设置
            settings = self.get_current_settings()
            count = self.count_spinbox.value()
            
            # 生成多个密码
            passwords = self.password_generator.generate_multiple_passwords(count, **settings)
            
            # 更新界面
            if passwords:
                # 显示第一个密码
                self.password_edit.setText(passwords[0])
                self.copy_btn.setEnabled(True)
                
                # 评估第一个密码的强度
                strength_result = self.password_generator.evaluate_password_strength(passwords[0])
                self.strength_indicator.update_strength(
                    strength_result['strength'], 
                    strength_result['entropy']
                )
                
                # 添加所有密码到历史记录
                for password in passwords:
                    self.add_to_history(password)
                
                logger.debug(f"生成了{count}个长度为{settings['length']}的密码")
                
        except Exception as e:
            logger.error(f"生成多个密码时出错: {str(e)}")
            show_message(
                self,
                "生成错误",
                f"生成多个密码时出错: {str(e)}",
                QMessageBox.Warning
            )
    
    def add_to_history(self, password: str):
        """
        添加密码到历史记录
        
        Args:
            password (str): 要添加的密码
        """
        self.password_list.insertItem(0, password)
        self.generated_passwords.insert(0, password)
        self.clear_btn.setEnabled(True)
    
    def copy_password(self):
        """
        复制当前密码到剪贴板
        """
        password = self.password_edit.text()
        if password:
            clipboard = QApplication.clipboard()
            clipboard.setText(password)
            self.statusBar().showMessage("密码已复制到剪贴板", 3000)
            logger.debug("密码已复制到剪贴板")
    
    def copy_from_list(self, item):
        """
        从历史记录复制密码
        
        Args:
            item: 列表项
        """
        password = item.text()
        clipboard = QApplication.clipboard()
        clipboard.setText(password)
        self.statusBar().showMessage("密码已复制到剪贴板", 3000)
        logger.debug("从历史记录复制了密码")
    
    def clear_history(self):
        """
        清空历史记录
        """
        self.password_list.clear()
        self.generated_passwords.clear()
        self.clear_btn.setEnabled(False)
        logger.debug("清空了密码历史记录")
    
    def show_context_menu(self, position):
        """
        显示右键菜单
        
        Args:
            position: 鼠标位置
        """
        item = self.password_list.itemAt(position)
        if item:
            context_menu = QMenu(self)
            
            # 添加菜单项
            copy_action = QAction("复制", self)
            copy_action.triggered.connect(lambda: self.copy_from_list(item))
            
            remove_action = QAction("移除此项", self)
            remove_action.triggered.connect(lambda: self.remove_item(item))
            
            # 添加到菜单
            context_menu.addAction(copy_action)
            context_menu.addAction(remove_action)
            
            # 显示菜单
            context_menu.exec_(self.password_list.mapToGlobal(position))
    
    def remove_item(self, item):
        """
        从列表中移除项
        
        Args:
            item: 要移除的项
        """
        row = self.password_list.row(item)
        self.password_list.takeItem(row)
        if row < len(self.generated_passwords):
            del self.generated_passwords[row]
        
        # 如果列表为空，禁用清空按钮
        if self.password_list.count() == 0:
            self.clear_btn.setEnabled(False)
    
    def statusBar(self):
        """
        获取或创建状态栏
        
        Returns:
            QStatusBar: 状态栏
        """
        # 由于QDialog没有内置状态栏，我们创建一个标签来显示状态信息
        if not hasattr(self, '_status_bar'):
            self._status_bar = QLabel("", self)
            self._status_bar.setAlignment(Qt.AlignLeft)
            self._status_bar.setStyleSheet("font-style: italic; color: #666;")
            self.layout().addWidget(self._status_bar)
            self._status_timer = None
            
            # 为QLabel添加showMessage方法，以模拟QStatusBar的行为
            def show_message(message, timeout=0):
                self._status_bar.setText(message)
                # 如果存在之前的定时器，先清除
                if hasattr(self, '_status_timer') and self._status_timer is not None:
                    self._status_timer.stop()
                    self._status_timer = None
                
                # 如果设置了超时，创建定时器清除消息
                if timeout > 0:
                    self._status_timer = QTimer()
                    self._status_timer.setSingleShot(True)
                    self._status_timer.timeout.connect(lambda: self._status_bar.setText(""))
                    self._status_timer.start(timeout)
            
            # 将showMessage方法附加到QLabel对象
            self._status_bar.showMessage = show_message
            
        return self._status_bar


# 测试函数
def main():
    """
    测试函数
    """
    app = QApplication(sys.argv)
    dialog = PasswordGeneratorDialog()
    dialog.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.DEBUG)
    # 运行测试
    main() 