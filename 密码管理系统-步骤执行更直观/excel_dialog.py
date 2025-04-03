#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Excel导入导出对话框模块，提供导入导出的用户界面
"""

import os
import sys
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QRadioButton, QProgressBar, QMessageBox, QFileDialog, 
                            QButtonGroup, QCheckBox, QGroupBox, QGridLayout, QTextEdit,
                            QListWidget, QListWidgetItem, QAbstractItemView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 导入UI组件
from ui_components import ModernButton, ModernLabel, HorizontalLine, show_message
from config import COLORS

# 配置日志
logger = logging.getLogger(__name__)

class ExcelWorkerThread(QThread):
    """
    Excel工作线程
    
    处理Excel导入/导出操作的后台线程
    """
    
    # 结果信号
    result_signal = pyqtSignal(bool, str)
    
    # 进度信号
    progress_signal = pyqtSignal(int)
    
    # 数据导入信号
    data_imported_signal = pyqtSignal(list)
    
    def __init__(self, parent=None):
        """
        初始化工作线程
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.operation = None  # 'import', 'export', 'template'
        self.file_path = None
        self.owner = None
        self.owners_data = {}
        self.hide_passwords = False
        
    def run(self):
        """执行操作"""
        try:
            # 获取当前文件的绝对路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 获取项目根目录
            root_dir = os.path.abspath(current_dir)
            
            # 将根目录添加到Python路径
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            
            # 导入Excel工具
            from excel_utils import ExcelExporter, ExcelImporter
            
            # 根据操作类型执行相应功能
            if self.operation == 'create_template':
                self.create_template()
            elif self.operation == 'import':
                self.import_from_excel()
            elif self.operation == 'export':
                self.export_to_excel()
            elif self.operation == 'export_multiple':
                self.export_multiple_to_excel()
            else:
                self.result_signal.emit(False, f"未知操作: {self.operation}")
        except Exception as e:
            import traceback
            logger.error(f"Excel工作线程出错: {str(e)}")
            logger.error(traceback.format_exc())
            self.result_signal.emit(False, f"操作失败: {str(e)}")
        
    def create_template(self):
        """创建Excel模板"""
        try:
            # 导入Excel工具
            from excel_utils import ExcelExporter
            
            # 创建导出工具
            exporter = ExcelExporter()
            
            # 更新进度
            self.update_progress(30)
            
            # 创建模板
            success, message = exporter.generate_template(self.file_path)
            
            # 处理结果
            self.update_progress(100)
            self.handle_result(success, message)
        except Exception as e:
            import traceback
            logger.error(f"创建Excel模板时出错: {str(e)}")
            logger.error(traceback.format_exc())
            self.handle_result(False, f"创建模板失败: {str(e)}")
            
    def import_from_excel(self):
        """从Excel导入数据"""
        try:
            # 导入Excel工具
            from excel_utils import ExcelImporter
            
            # 创建导入工具
            importer = ExcelImporter()
            
            # 更新进度
            self.update_progress(30)
            
            # 导入数据
            success, message, records = importer.import_from_excel(
                self.file_path, self.owner
            )
            
            # 处理结果
            self.update_progress(70)
            
            if success:
                # 如果成功，发送导入的数据
                self.data_imported_signal.emit(records)
            else:
                self.handle_result(success, message)
        except Exception as e:
            import traceback
            logger.error(f"从Excel导入数据时出错: {str(e)}")
            logger.error(traceback.format_exc())
            self.handle_result(False, f"导入失败: {str(e)}")
            
    def export_to_excel(self):
        """导出数据到Excel"""
        try:
            # 导入Excel工具
            from excel_utils import ExcelExporter
            
            # 创建导出工具
            exporter = ExcelExporter()
            
            # 更新进度
            self.update_progress(30)
            
            # 导出数据
            success, message = exporter.export_to_excel(
                self.passwords, self.owner, self.file_path, self.hide_passwords
            )
            
            # 处理结果
            self.update_progress(100)
            self.handle_result(success, message)
        except Exception as e:
            import traceback
            logger.error(f"导出数据到Excel时出错: {str(e)}")
            logger.error(traceback.format_exc())
            self.handle_result(False, f"导出失败: {str(e)}")
    
    def export_multiple_to_excel(self):
        """导出多个人员数据到Excel"""
        try:
            # 导入Excel工具
            from excel_utils import ExcelExporter
            
            # 创建导出工具
            exporter = ExcelExporter()
            
            # 更新进度
            self.update_progress(30)
            
            # 导出数据
            success, message = exporter.export_multiple_to_excel(
                self.owners_data, self.file_path, self.hide_passwords
            )
            
            # 处理结果
            self.update_progress(100)
            self.handle_result(success, message)
        except Exception as e:
            import traceback
            logger.error(f"导出多个人员数据到Excel时出错: {str(e)}")
            logger.error(traceback.format_exc())
            self.handle_result(False, f"导出失败: {str(e)}")

    def update_progress(self, value):
        """
        更新进度条
        
        Args:
            value (int): 进度值
        """
        self.progress_signal.emit(value)
        
    def handle_result(self, success, message):
        """
        处理导出结果
        
        Args:
            success (bool): 是否成功
            message (str): 结果消息
        """
        # 更新界面状态
        self.progress_signal.emit(100)
        self.result_signal.emit(success, message)


class ExportDialog(QDialog):
    """
    Excel导出对话框
    
    提供将密码记录导出为Excel文件的用户界面
    """
    
    def __init__(self, parent=None, owner=None, passwords=None):
        """
        初始化导出对话框
        
        Args:
            parent: 父窗口
            owner (str): 所有者
            passwords (List[List[str]]): 密码记录列表
        """
        super().__init__(parent)
        self.owner = owner
        self.passwords = passwords
        self.file_path = None
        self.worker_thread = None
        
        self.setWindowTitle("导出到Excel")
        self.setMinimumWidth(450)
        self.setup_ui()
        
    def setup_ui(self):
        """
        设置界面
        """
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 标题
        title_label = ModernLabel("导出密码记录到Excel文件", font_size=12, bold=True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明
        desc_label = ModernLabel(f"即将导出 {self.owner} 的密码记录，共 {len(self.passwords)} 条")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        layout.addWidget(HorizontalLine())
        
        # 导出选项
        options_group = QGroupBox("导出选项")
        options_layout = QVBoxLayout()
        
        # 密码处理选项
        self.hide_password_cb = QCheckBox("隐藏密码（导出为 ******** 形式）")
        self.hide_password_cb.setChecked(True)  # 默认隐藏密码
        options_layout.addWidget(self.hide_password_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.export_btn = ModernButton("导出", color=COLORS["primary"])
        self.export_btn.clicked.connect(self.export_to_excel)
        
        self.cancel_btn = ModernButton("取消", color=COLORS["secondary"])
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def export_to_excel(self):
        """
        导出到Excel文件
        """
        # 获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel文件", f"{self.owner}的密码记录.xlsx",
            "Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if not file_path:
            return
            
        # 如果未指定.xlsx扩展名，添加它
        if not file_path.lower().endswith('.xlsx'):
            file_path += '.xlsx'
            
        self.file_path = file_path
        self.hide_passwords = self.hide_password_cb.isChecked()
        
        # 更新界面状态
        self.export_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        
        # 创建并启动工作线程
        self.worker_thread = ExcelWorkerThread(self)
        self.worker_thread.operation = 'export'
        self.worker_thread.file_path = self.file_path
        self.worker_thread.owner = self.owner
        self.worker_thread.passwords = self.passwords
        self.worker_thread.hide_passwords = self.hide_passwords
        
        # 连接信号
        self.worker_thread.progress_signal.connect(self.update_progress)
        self.worker_thread.result_signal.connect(self.handle_result)
        
        # 启动线程
        self.worker_thread.start()
        
    def update_progress(self, value):
        """
        更新进度条
        
        Args:
            value (int): 进度值
        """
        self.progress_bar.setValue(value)
        
    def handle_result(self, success, message):
        """
        处理导出结果
        
        Args:
            success (bool): 是否成功
            message (str): 结果消息
        """
        # 更新界面状态
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.cancel_btn.setText("关闭")
        
        # 显示结果
        if success:
            show_message(self, "导出成功", f"{message}\n文件已保存至:\n{self.file_path}", QMessageBox.Information)
            self.accept()
        else:
            show_message(self, "导出失败", message, QMessageBox.Warning)


class ImportDialog(QDialog):
    """
    Excel导入对话框
    
    提供从Excel文件导入密码记录的用户界面
    """
    
    # 导入完成信号
    import_completed = pyqtSignal(bool, str, list)
    
    def __init__(self, parent=None, default_owner=None):
        """
        初始化导入对话框
        
        Args:
            parent: 父窗口
            default_owner (str): 默认选中的所有者
        """
        super().__init__(parent)
        self.default_owner = default_owner
        self.owner = default_owner  # 将在load_owners中更新为实际选择
        self.file_path = None
        self.worker_thread = None
        self.imported_records = []
        self.owner_radios = {}  # 用于存储人员单选按钮
        
        self.setWindowTitle("从Excel导入")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_owners()
        
    def setup_ui(self):
        """
        设置界面
        """
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 标题
        title_label = ModernLabel("从Excel文件导入密码记录", font_size=12, bold=True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明
        desc_layout = QVBoxLayout()
        desc_label = ModernLabel("导入的数据将添加到所选人员的密码记录中")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_layout.addWidget(desc_label)
        
        # 模板下载链接
        template_layout = QHBoxLayout()
        template_label = ModernLabel("没有Excel模板？")
        self.download_template_btn = ModernButton("下载模板", color=COLORS["info"])
        self.download_template_btn.clicked.connect(self.download_template)
        template_layout.addWidget(template_label)
        template_layout.addWidget(self.download_template_btn)
        template_layout.addStretch()
        desc_layout.addLayout(template_layout)
        
        layout.addLayout(desc_layout)
        layout.addWidget(HorizontalLine())
        
        # 人员选择区域
        owner_group = QGroupBox("选择导入到哪个人员")
        self.radio_layout = QHBoxLayout()  # 使用水平布局而不是垂直布局
        self.radio_layout.setSpacing(20)   # 设置按钮之间的间距
        self.radio_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
        owner_group.setLayout(self.radio_layout)
        layout.addWidget(owner_group)
        
        # 导入选项
        options_group = QGroupBox("导入选项")
        options_layout = QVBoxLayout()
        
        # 导入方式选项
        self.replace_rb = QRadioButton("替换模式 - 删除现有记录，仅保留导入的记录")
        self.append_rb = QRadioButton("追加模式 - 将新记录添加到现有记录后")
        
        # 默认选择追加模式
        self.append_rb.setChecked(True)
        
        options_layout.addWidget(self.replace_rb)
        options_layout.addWidget(self.append_rb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 文件选择按钮
        file_layout = QHBoxLayout()
        self.file_path_label = ModernLabel("未选择文件")
        self.browse_btn = ModernButton("选择文件", color=COLORS["primary"])
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path_label, 1)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 导入结果文本框（初始隐藏）
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setVisible(False)
        self.result_text.setMaximumHeight(150)
        layout.addWidget(self.result_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.import_btn = ModernButton("导入", color=COLORS["primary"])
        self.import_btn.clicked.connect(self.import_from_excel)
        self.import_btn.setEnabled(False)  # 初始禁用
        
        self.cancel_btn = ModernButton("取消", color=COLORS["secondary"])
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.import_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def load_owners(self):
        """加载人员列表"""
        try:
            # 固定人员列表
            fixed_owners = ["徐国明", "高文彬", "石帆"]
            
            # 创建单选按钮组
            self.owner_button_group = QButtonGroup(self)
            
            # 清除现有的单选按钮
            for radio in self.owner_radios.values():
                self.radio_layout.removeWidget(radio)
                radio.deleteLater()
            self.owner_radios.clear()
            
            # 为每个人员创建单选按钮
            for owner in fixed_owners:
                radio = QRadioButton(owner)
                radio.setStyleSheet("QRadioButton { font-size: 12pt; margin: 0 15px; }")
                self.owner_radios[owner] = radio
                self.radio_layout.addWidget(radio)
                self.owner_button_group.addButton(radio)
                
                # 如果是默认所有者，选中此按钮
                if owner == self.default_owner:
                    radio.setChecked(True)
            
            # 确保至少有一个按钮被选中
            if self.default_owner is None and fixed_owners:
                self.owner_radios[fixed_owners[0]].setChecked(True)
                
            # 连接单选按钮组的信号
            self.owner_button_group.buttonClicked.connect(self.on_owner_selected)
            
            # 初始化owner属性
            self.update_selected_owner()
                
        except Exception as e:
            logger.error(f"加载人员列表出错: {str(e)}")
            show_message(self, "加载错误", f"加载人员列表出错: {str(e)}", QMessageBox.Warning)
            
    def on_owner_selected(self, button):
        """处理人员选择变更"""
        self.update_selected_owner()
        
    def update_selected_owner(self):
        """更新当前选中的人员"""
        for owner, radio in self.owner_radios.items():
            if radio.isChecked():
                self.owner = owner
                return
        
        # 如果没有选中任何人员（理论上不应该发生）
        if self.owner_radios:
            first_owner = list(self.owner_radios.keys())[0]
            self.owner_radios[first_owner].setChecked(True)
            self.owner = first_owner
            
    def browse_file(self):
        """
        浏览文件
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if file_path:
            self.file_path = file_path
            self.file_path_label.setText(os.path.basename(file_path))
            self.import_btn.setEnabled(True)
            
    def download_template(self):
        """
        下载导入模板
        """
        # 获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存模板文件", "密码记录导入模板.xlsx",
            "Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if not file_path:
            return
            
        # 如果未指定.xlsx扩展名，添加它
        if not file_path.lower().endswith('.xlsx'):
            file_path += '.xlsx'
            
        # 创建并启动工作线程
        self.worker_thread = ExcelWorkerThread(self)
        self.worker_thread.operation = 'template'
        self.worker_thread.file_path = file_path
        
        # 连接信号
        self.worker_thread.result_signal.connect(self.handle_template_result)
        
        # 启动线程
        self.worker_thread.start()
        
    def handle_template_result(self, success, message):
        """
        处理模板生成结果
        
        Args:
            success (bool): 是否成功
            message (str): 结果消息
        """
        if success:
            show_message(self, "模板生成成功", f"{message}\n\n您可以使用Excel打开此文件，按照模板格式填写密码记录，然后保存并使用导入功能导入。", QMessageBox.Information)
        else:
            show_message(self, "模板生成失败", message, QMessageBox.Warning)
            
    def import_from_excel(self):
        """
        从Excel文件导入
        """
        if not self.file_path or not os.path.exists(self.file_path):
            show_message(self, "文件错误", "请选择有效的Excel文件", QMessageBox.Warning)
            return
            
        # 确认导入
        is_replace_mode = self.replace_rb.isChecked()
        confirm_message = "确定要导入Excel数据吗？" 
        
        if is_replace_mode:
            confirm_message = "您选择了替换模式，这将删除所有现有数据！确定要继续吗？"
            
        if QMessageBox.question(
            self, "确认导入", confirm_message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
            
        # 更新界面状态
        self.import_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.download_template_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        
        # 创建并启动工作线程
        self.worker_thread = ExcelWorkerThread(self)
        self.worker_thread.operation = 'import'
        self.worker_thread.file_path = self.file_path
        self.worker_thread.owner = self.owner
        
        # 连接信号
        self.worker_thread.progress_signal.connect(self.update_progress)
        self.worker_thread.result_signal.connect(self.handle_result)
        self.worker_thread.data_imported_signal.connect(self.process_imported_data)
        
        # 启动线程
        self.worker_thread.start()
        
    def update_progress(self, value):
        """
        更新进度条
        
        Args:
            value (int): 进度值
        """
        self.progress_bar.setValue(value)
        
    def handle_result(self, success, message):
        """
        处理导入结果
        
        Args:
            success (bool): 是否成功
            message (str): 结果消息
        """
        # 更新界面状态
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("关闭")
        
        # 显示结果
        self.result_text.setVisible(True)
        if success:
            self.result_text.setHtml(f"<font color='green'><b>✓ {message}</b></font>")
        else:
            self.result_text.setHtml(f"<font color='red'><b>✗ {message}</b></font>")
            
    def process_imported_data(self, records):
        """处理导入的数据"""
        self.progress_bar.setValue(80)

        try:
            # 导入密码管理器模块
            import sys
            import os
            
            # 获取当前文件的绝对路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 获取项目根目录
            root_dir = os.path.abspath(current_dir)
            
            # 将根目录添加到Python路径
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
                
            # 导入密码管理器模块
            from password import password_manager
            
            # 保存导入的记录
            self.imported_records = records
            
            # 获取现有数据
            existing_records = password_manager.get_passwords_by_owner(self.owner)
            
            # 根据选择的模式处理数据
            is_replace_mode = self.replace_rb.isChecked()
            
            if is_replace_mode:
                # 替换模式：直接用导入的记录替换现有记录
                result = password_manager.db.set(self.owner, records)
                if not result:
                    raise Exception("保存数据失败")
            else:
                # 追加模式：添加导入的记录到现有记录
                for record in records:
                    # 使用add_password添加记录
                    result, message = password_manager.add_password(self.owner, record)
                    if not result:
                        logger.error(f"添加记录失败: {message}")
            
            # 记录导入操作到审计日志
            try:
                from audit_log import AuditLogger
                audit_logger = AuditLogger()
                
                mode = "replace" if self.replace_rb.isChecked() else "append"
                operation_details = f"导入Excel文件 '{os.path.basename(self.file_path)}' 到 '{self.owner}' ({mode}模式), 共{len(records)}条记录"
                
                audit_logger.log_operation(
                    operation_type="import",
                    result="success",
                    details=operation_details,
                    target=self.owner
                )
            except Exception as e:
                logger.error(f"记录导入操作到审计日志时出错: {str(e)}")
            
            # 发送信号
            self.import_completed.emit(True, f"成功导入 {len(records)} 条记录", records)
            self.progress_bar.setValue(100)
            
            # 关闭对话框
            self.accept()
            
        except ImportError as e:
            error_message = f"导入密码管理器模块失败: {str(e)}"
            self.import_completed.emit(False, error_message, [])
            show_message(self, "导入错误", error_message, QMessageBox.Critical)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)
            self.import_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
        except Exception as e:
            logger.error(f"处理导入数据时出错: {str(e)}")
            error_message = f"导入失败: {str(e)}"
            self.import_completed.emit(False, error_message, [])
            show_message(self, "导入错误", error_message, QMessageBox.Critical)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)
            self.import_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)


class MultiExportDialog(QDialog):
    """
    多人员导出对话框
    
    提供导出多个人员的密码记录到Excel文件的功能
    """
    
    def __init__(self, parent=None, preselect_current=False):
        """
        初始化多人员导出对话框
        
        Args:
            parent: 父窗口
            preselect_current: 是否预选当前用户
        """
        super().__init__(parent)
        self.parent = parent
        self.preselect_current = preselect_current
        self.setWindowTitle("导出到Excel")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        self.file_path = ""
        self.hide_passwords = False
        self.owners_data = {}
        self.owner_checkboxes = {}  # 用于存储人员复选框
        
        self.setup_ui()
        self.load_owners()
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 标题
        title_label = ModernLabel("导出密码记录到Excel文件", font_size=12, bold=True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明
        desc_label = ModernLabel("可以选择一个或多个人员，导出到同一个Excel文件的不同工作表中")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        layout.addWidget(HorizontalLine())
        
        # 人员选择区域
        owner_group = QGroupBox("选择要导出的人员")
        owner_layout = QVBoxLayout()
        
        # 选择全部按钮
        select_all_layout = QHBoxLayout()
        self.select_all_btn = ModernButton("全选", color=COLORS["info"])
        self.select_all_btn.clicked.connect(self.select_all_owners)
        
        self.deselect_all_btn = ModernButton("取消全选", color=COLORS["secondary"])
        self.deselect_all_btn.clicked.connect(self.deselect_all_owners)
        
        select_all_layout.addWidget(self.select_all_btn)
        select_all_layout.addWidget(self.deselect_all_btn)
        select_all_layout.addStretch()
        owner_layout.addLayout(select_all_layout)
        
        # 人员复选框列表
        self.checkbox_layout = QVBoxLayout()
        self.checkbox_layout.setSpacing(8)  # 增加复选框之间的间距
        owner_layout.addLayout(self.checkbox_layout)
        
        owner_group.setLayout(owner_layout)
        layout.addWidget(owner_group)
        
        # 导出选项
        options_group = QGroupBox("导出选项")
        options_layout = QVBoxLayout()
        
        # 隐藏密码选项
        self.hide_password_cb = QCheckBox("隐藏密码（导出为 ******** 形式）")
        self.hide_password_cb.setChecked(True)
        options_layout.addWidget(self.hide_password_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.export_btn = ModernButton("导出", color=COLORS["primary"])
        self.export_btn.clicked.connect(self.export_to_excel)
        
        self.cancel_btn = ModernButton("取消", color=COLORS["secondary"])
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def load_owners(self):
        """加载人员列表"""
        try:
            # 先清除现有复选框
            for checkbox in self.owner_checkboxes.values():
                self.checkbox_layout.removeWidget(checkbox)
                checkbox.deleteLater()
            self.owner_checkboxes.clear()
            
            # 加载固定人员列表
            fixed_owners = ["徐国明", "高文彬", "石帆"]
            
            # 创建人员复选框
            for owner in fixed_owners:
                checkbox = QCheckBox(owner)
                checkbox.setStyleSheet("QCheckBox { font-size: 11pt; }")  # 设置字体大小
                
                # 如果需要预选当前用户
                if self.preselect_current and self.parent:
                    try:
                        # 获取当前选中的人员
                        current_owner = self.parent.layout_manager.get_selected_owner()
                        if current_owner and current_owner == owner:
                            checkbox.setChecked(True)
                    except Exception as e:
                        logger.error(f"预选当前用户时出错: {str(e)}")
                        
                self.owner_checkboxes[owner] = checkbox
                self.checkbox_layout.addWidget(checkbox)
                        
        except Exception as e:
            logger.error(f"加载人员列表出错: {str(e)}")
            show_message(self, "加载错误", f"加载人员列表出错: {str(e)}", QMessageBox.Warning)
            
    def select_all_owners(self):
        """选择所有人员"""
        for checkbox in self.owner_checkboxes.values():
            checkbox.setChecked(True)
            
    def deselect_all_owners(self):
        """取消选择所有人员"""
        for checkbox in self.owner_checkboxes.values():
            checkbox.setChecked(False)
            
    def get_selected_owners(self):
        """获取已选择的人员列表"""
        return [owner for owner, checkbox in self.owner_checkboxes.items() if checkbox.isChecked()]
            
    def export_to_excel(self):
        """
        导出到Excel文件
        """
        # 获取选中的人员
        selected_owners = self.get_selected_owners()
        if not selected_owners:
            show_message(self, "选择错误", "请至少选择一个人员", QMessageBox.Warning)
            return
            
        # 获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel文件", "密码记录汇总.xlsx",
            "Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if not file_path:
            return
            
        # 如果未指定.xlsx扩展名，添加它
        if not file_path.lower().endswith('.xlsx'):
            file_path += '.xlsx'
            
        self.file_path = file_path
        self.hide_passwords = self.hide_password_cb.isChecked()
        
        # 更新界面状态
        self.export_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        # 获取每个人员的密码记录
        self.progress_bar.setValue(20)
        self.owners_data = {}
        
        # 确保能访问密码管理器
        try:
            # 直接导入password模块而不是services.password_manager
            import sys
            import os
            
            # 获取当前文件的绝对路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 获取项目根目录
            root_dir = os.path.abspath(current_dir)
            
            # 将根目录添加到 Python 路径
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
                
            # 直接导入password模块
            from password import password_manager
            
            for owner in selected_owners:
                try:
                    passwords = password_manager.get_passwords_by_owner(owner)
                    if passwords:
                        self.owners_data[owner] = passwords
                except Exception as e:
                    logger.error(f"获取 {owner} 的密码记录时出错: {str(e)}")
            
            # 检查是否获取到数据
            if not self.owners_data:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(False)
                self.export_btn.setEnabled(True)
                self.cancel_btn.setEnabled(True)
                show_message(self, "导出失败", "所选人员没有可导出的密码记录", QMessageBox.Warning)
                return
                
        except ImportError as e:
            show_message(self, "导入错误", f"无法导入密码管理器: {str(e)}", QMessageBox.Critical)
            self.cancel_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
        except Exception as e:
            show_message(self, "错误", f"获取密码数据时出错: {str(e)}", QMessageBox.Critical)
            self.cancel_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
        
        # 创建并启动工作线程
        self.progress_bar.setValue(40)
        self.worker_thread = ExcelWorkerThread(self)
        self.worker_thread.operation = 'export_multiple'
        self.worker_thread.file_path = self.file_path
        self.worker_thread.owners_data = self.owners_data
        self.worker_thread.hide_passwords = self.hide_passwords
        
        # 连接信号
        self.worker_thread.progress_signal.connect(self.update_progress)
        self.worker_thread.result_signal.connect(self.handle_result)
        
        # 启动线程
        self.worker_thread.start()
        
    def update_progress(self, value):
        """
        更新进度条
        
        Args:
            value (int): 进度值
        """
        self.progress_bar.setValue(value)
        
    def handle_result(self, success, message):
        """
        处理导出结果
        
        Args:
            success (bool): 是否成功
            message (str): 结果消息
        """
        # 更新界面状态
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.cancel_btn.setText("关闭")
        
        # 显示结果
        if success:
            show_message(self, "导出成功", f"{message}\n文件已保存至:\n{self.file_path}", QMessageBox.Information)
            self.accept()
        else:
            show_message(self, "导出失败", message, QMessageBox.Warning) 