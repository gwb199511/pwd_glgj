#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理系统引导对话框模块
提供用户引导功能
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional, Callable

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QCheckBox, QPushButton, QFrame, QStackedWidget,
    QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont, QIcon

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from ui_components import ModernButton, ModernLabel, HorizontalLine
from config import COLORS
# 使用直接导入模块，避免循环导入
import user_settings

# 配置日志
logger = logging.getLogger(__name__)


class GuidePage(QWidget):
    """
    引导页面组件
    
    表示引导流程中的一个步骤
    """
    
    def __init__(self, title: str, description: str, image_path: Optional[str] = None, parent=None):
        """
        初始化引导页面
        
        Args:
            title (str): 页面标题
            description (str): 页面描述
            image_path (str, optional): 图片路径。默认为None
            parent: 父窗口
        """
        super().__init__(parent)
        self.title = title
        self.description = description
        self.image_path = image_path
        self._setup_ui()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # 标题
        title_label = ModernLabel(self.title, font_size=14, bold=True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 分隔线
        line = HorizontalLine()
        layout.addWidget(line)
        layout.addSpacing(5)
        
        # 图片（如果有）
        if self.image_path:
            try:
                image_label = QLabel()
                pixmap = QPixmap(self.image_path)
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                layout.addWidget(image_label)
                layout.addSpacing(10)
            except Exception as e:
                logger.error(f"加载图片失败: {str(e)}")
        
        # 描述
        desc_label = ModernLabel(self.description, font_size=11)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(desc_label)
        
        # 使描述标签能够扩展填充剩余空间
        desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.setLayout(layout)


class GuideDialog(QDialog):
    """
    引导对话框
    
    提供分步式引导界面，帮助用户了解功能
    """
    
    def __init__(self, guide_key: str, pages: List[Dict[str, Any]], parent=None):
        """
        初始化引导对话框
        
        Args:
            guide_key (str): 引导键名，用于保存状态
            pages (List[Dict[str, Any]]): 页面数据列表
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.guide_key = guide_key
        self.pages = pages
        self.current_page = 0
        
        # 设置窗口属性
        self.setWindowTitle("功能引导")
        self.resize(500, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置用户界面"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建页面容器
        self.page_container = QStackedWidget()
        
        # 添加所有页面
        for page_data in self.pages:
            page = GuidePage(
                title=page_data.get("title", ""),
                description=page_data.get("description", ""),
                image_path=page_data.get("image_path"),
                parent=self
            )
            self.page_container.addWidget(page)
        
        main_layout.addWidget(self.page_container)
        
        # 添加分隔线
        line = HorizontalLine()
        main_layout.addWidget(line)
        
        # 底部控件
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(20, 15, 20, 15)
        
        # 不再显示选项
        self.dont_show_checkbox = QCheckBox("不再显示此引导")
        self.dont_show_checkbox.setStyleSheet(f"color: {COLORS['secondary']};")
        bottom_layout.addWidget(self.dont_show_checkbox)
        
        # 填充空间
        bottom_layout.addStretch()
        
        # 上一步按钮
        self.prev_button = ModernButton("上一步", color=COLORS["secondary"])
        self.prev_button.clicked.connect(self._go_prev)
        self.prev_button.setEnabled(False)
        bottom_layout.addWidget(self.prev_button)
        
        # 下一步/完成按钮
        self.next_button = ModernButton("下一步", color=COLORS["primary"])
        self.next_button.clicked.connect(self._go_next)
        bottom_layout.addWidget(self.next_button)
        
        # 添加底部布局
        bottom_container = QWidget()
        bottom_container.setLayout(bottom_layout)
        main_layout.addWidget(bottom_container)
        
        self.setLayout(main_layout)
        
        # 显示第一页
        self.page_container.setCurrentIndex(0)
        self._update_buttons()
        
    def _go_next(self):
        """转到下一页"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.page_container.setCurrentIndex(self.current_page)
            self._update_buttons()
        else:
            self.accept()
            
    def _go_prev(self):
        """转到上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.page_container.setCurrentIndex(self.current_page)
            self._update_buttons()
            
    def _update_buttons(self):
        """更新按钮状态"""
        # 更新上一步按钮
        self.prev_button.setEnabled(self.current_page > 0)
        
        # 更新下一步/完成按钮
        if self.current_page == len(self.pages) - 1:
            self.next_button.setText("完成")
        else:
            self.next_button.setText("下一步")
            
    def accept(self):
        """接受对话框"""
        # 保存引导完成状态
        # 无论是否勾选"不再显示"，只要用户点击了"完成"按钮，就标记为已完成
        user_settings.user_settings.mark_guide_completed(self.guide_key)
        
        # 记录日志
        if self.dont_show_checkbox.isChecked():
            logger.info(f"用户选择不再显示引导: {self.guide_key}")
        else:
            logger.info(f"用户已完成引导: {self.guide_key}")
            
        super().accept()
        

# 密码更新引导信息
PASSWORD_UPDATE_GUIDE = [
    {
        "title": "欢迎使用密码管理系统",
        "description": """这是一个密码更新引导，帮助您了解如何安全地管理和更新密码。

密码管理系统可以帮助您：
• 安全地存储所有密码
• 生成高强度随机密码
• 自动同步更新服务器密码
• 防止密码泄露和遗忘"""
    },
    {
        "title": "密码编辑基础",
        "description": """编辑密码记录时，您需要注意以下几点：

• 项目名称、账户和密码为必填字段
• 密码会自动加密存储，保障安全
• 编辑完成后点击"确认"按钮保存
• 点击"取消"可放弃当前编辑

提示：双击表格行或右键选择"编辑行"可以开始编辑"""
    },
    {
        "title": "密码生成和更新",
        "description": """系统提供了方便的密码生成和更新功能：

• 在密码单元格上右键，选择"生成随机密码"
• 选择"生成16位随机密码并更新到服务器(SSH)"可以同时更新服务器密码
• 生成的密码包含大小写字母、数字和特殊字符，安全性高

注意：只有填写了正确IP地址和账户的记录才能同步更新到服务器"""
    },
    {
        "title": "服务器密码同步",
        "description": """当您需要更新服务器密码时：

1. 确保填写了正确的服务器IP地址
2. 确保填写了正确的服务器账户名称
3. 右键点击密码单元格，选择"生成16位随机密码并更新到服务器(SSH)"
4. 系统会先验证当前密码，成功后自动更新密码
5. 完成后会验证新密码是否生效

所有操作都有详细日志记录，确保安全可追溯"""
    }
]

# 首次编辑引导信息
FIRST_EDIT_GUIDE = [
    {
        "title": "表格编辑功能",
        "description": """您正在使用编辑功能，以下是一些操作提示：

• 标黄色背景的字段为必填项
• 修改完成后点击"确认"按钮保存
• 点击"取消"可放弃当前编辑
• 编辑状态下，其他操作将被暂时禁用"""
    }
]

# 密码字段引导信息
PASSWORD_FIELD_GUIDE = [
    {
        "title": "密码字段编辑",
        "description": """您正在编辑密码字段，请注意：

• 密码将以加密形式存储，保障安全
• 建议使用右键菜单中的"生成随机密码"功能
• 强密码应包含大小写字母、数字和特殊字符
• 如需更新服务器密码，请使用"生成16位随机密码并更新到服务器(SSH)"选项"""
    }
]

# IP地址字段引导信息
IP_FIELD_GUIDE = [
    {
        "title": "IP地址字段编辑",
        "description": """您正在编辑IP地址字段，请注意：

• 填写正确的IP地址格式(如 192.168.1.1)
• 填写IP地址后，可以启用密码的服务器同步功能
• 服务器同步需要同时填写正确的账户名
• 更新服务器密码前，请确保当前密码正确无误"""
    }
]


def show_guide_if_needed(guide_key: str, parent=None, force: bool = False) -> bool:
    """
    如果需要或强制要求，显示引导对话框
    
    Args:
        guide_key (str): 引导键名
        parent: 父窗口
        force (bool): 是否强制显示，即使用户已完成该引导
        
    Returns:
        bool: 如果显示了引导返回True，否则返回False
    """
    if not force and user_settings.user_settings.is_guide_completed(guide_key):
        logger.info(f"用户已完成引导: {guide_key}，跳过显示")
        return False
        
    # 选择对应的引导内容
    guide_content = None
    if guide_key == "password_update":
        guide_content = PASSWORD_UPDATE_GUIDE
    elif guide_key == "first_edit":
        guide_content = FIRST_EDIT_GUIDE
    elif guide_key == "password_field":
        guide_content = PASSWORD_FIELD_GUIDE
    elif guide_key == "ip_field":
        guide_content = IP_FIELD_GUIDE
    else:
        logger.warning(f"未找到引导内容: {guide_key}")
        return False
        
    # 显示引导对话框
    dialog = GuideDialog(guide_key, guide_content, parent)
    
    # 如果是强制显示，初始时取消选中"不再显示"复选框
    if force and hasattr(dialog, "dont_show_checkbox"):
        dialog.dont_show_checkbox.setChecked(False)
        
    result = dialog.exec_()
    
    logger.info(f"显示引导: {guide_key}, 结果: {'接受' if result else '拒绝'}")
    return result == QDialog.Accepted 