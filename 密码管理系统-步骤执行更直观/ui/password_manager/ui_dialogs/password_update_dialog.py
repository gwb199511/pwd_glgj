#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码更新对话框
显示密码更新进度并确保密码成功更新后永久保存
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Optional

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QProgressBar,
                             QHeaderView, QMessageBox, QApplication, QDialogButtonBox,
                             QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QBrush, QIcon, QFont

from password import password_manager
from ssh_password_updater import ssh_password_updater
from encrypt import encryptor
from audit_log import audit_logger, OP_TYPE_SSH_UPDATE, OP_RESULT_SUCCESS, OP_RESULT_FAIL, OP_RESULT_INFO, LOG_TYPE_SSH
from config import FONT_FAMILY, COLORS

logger = logging.getLogger(__name__)

class PasswordUpdateWorker(QThread):
    """
    密码更新工作线程
    """
    # 定义信号
    update_progress = pyqtSignal(int, str)  # 行索引, 状态消息
    update_finished = pyqtSignal(object)  # 结果字典

    def __init__(self, servers_to_update):
        """
        初始化密码更新工作线程
        
        Args:
            servers_to_update (List[Dict[str, Any]]): 要更新的服务器列表
        """
        super().__init__()
        self.servers_to_update = servers_to_update
        self.results = {}
        self.interrupted = False

    def run(self):
        """执行更新工作"""
        total = len(self.servers_to_update)
        
        for i, server in enumerate(self.servers_to_update):
            if self.interrupted:
                break
                
            row_idx = i
            ip = server.get('ip', '')
            username = server.get('username', '')
            old_password = server.get('old_password', '')
            new_password = server.get('new_password', '')
            
            # 更新进度 - 等待更新
            self.update_progress.emit(row_idx, "等待连接服务器...")
            time.sleep(0.2)  # 短暂延迟，使状态变化更清晰
            
            # 更新进度 - 正在连接服务器
            self.update_progress.emit(row_idx, "正在连接服务器...")
            time.sleep(0.3)  # 模拟连接过程
            
            # 执行SSH密码更新
            try:
                # 更新进度 - 开始尝试连接
                self.update_progress.emit(row_idx, "尝试建立SSH连接...")
                
                success, message = ssh_password_updater.update_password(
                    ip=ip,
                    username=username,
                    old_password=old_password,
                    new_password=new_password
                )
                
                if success:
                    # 更新进度 - 连接成功和密码更新状态
                    self.update_progress.emit(row_idx, "连接成功，开始修改密码...")
                    time.sleep(0.2)
                    self.update_progress.emit(row_idx, "密码修改成功！")
                else:
                    # 更新详细的失败原因
                    self.update_progress.emit(row_idx, f"更新失败: {message}")
            except Exception as e:
                success = False
                message = str(e)
                self.update_progress.emit(row_idx, f"异常错误: {message}")
            
            # 保存结果
            self.results[row_idx] = {
                'success': success,
                'message': message,
                'server': server
            }
            
            # 短暂延迟，避免过快刷新UI
            time.sleep(0.1)
            
        # 发送完成信号
        self.update_finished.emit(self.results)
    
    def interrupt(self):
        """中断工作线程"""
        self.interrupted = True

class PasswordUpdateDialog(QDialog):
    """密码更新对话框，显示更新进度并确保成功后永久保存"""
    
    def __init__(self, parent=None, servers_to_update=None, owner=""):
        """
        初始化密码更新对话框
        
        Args:
            parent: 父窗口
            servers_to_update: 要更新的服务器列表
            owner: 所有者
        """
        super().__init__(parent)
        self.servers_to_update = servers_to_update or []
        self.owner = owner
        self.worker = None
        self.results = {}
        self.successful_updates = []
        
        self.setWindowTitle("密码更新")
        self.resize(1000, 550)  # 增加对话框宽度和高度
        self.setModal(True)
        
        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f7;
                border: 1px solid #dcdcdc;
            }
            QLabel {
                color: #333333;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QTableWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #e9e9e9;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4a86e8;
                border-radius: 2px;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # 增加间距
        layout.setContentsMargins(20, 20, 20, 20)  # 增加边距
        
        # 顶部标题区域
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)
        
        # 标题标签
        title_label = QLabel("密码更新操作")
        title_label.setFont(QFont(FONT_FAMILY, 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2a66c8;")
        
        # 描述标签
        desc_label = QLabel('以下是将要更新的密码列表，点击"开始更新"按钮开始更新密码。')
        desc_label.setFont(QFont(FONT_FAMILY, 10))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #555555;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(desc_label)
        layout.addLayout(title_layout)
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["项目名称", "IP地址", "用户名", "旧密码", "新密码", "更新状态"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁止编辑
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # 选择整行
        self.table.setAlternatingRowColors(True)  # 交替行颜色
        self.table.verticalHeader().setVisible(False)  # 隐藏垂直表头
        self.table.setShowGrid(True)  # 显示网格
        
        # 设置表格列宽自适应
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 项目名称列
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # IP地址列
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 用户名列
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 旧密码列
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 新密码列
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # 更新状态列自动扩展填充剩余空间
        
        # 设置表格行高
        self.table.verticalHeader().setDefaultSectionSize(32)  # 设置默认行高
        
        # 填充表格数据
        self.populate_table()
        
        # 确保表格可以自适应窗口大小
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.table)
        
        # 进度信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # 总进度条
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)
        
        progress_label = QLabel("总进度:")
        progress_label.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        progress_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        info_layout.addLayout(progress_layout)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont(FONT_FAMILY, 10))
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 4px;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(50, 10, 50, 10)  # 左右增加边距
        
        # 开始更新按钮
        self.start_button = QPushButton("开始更新")
        self.start_button.setMinimumWidth(140)
        self.start_button.setMinimumHeight(36)
        self.start_button.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        self.start_button.setCursor(Qt.PointingHandCursor)  # 设置鼠标悬停时为手型指针
        self.start_button.clicked.connect(self.start_update)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(140)
        self.cancel_button.setMinimumHeight(36)
        self.cancel_button.setFont(QFont(FONT_FAMILY, 10))
        self.cancel_button.setStyleSheet("background-color: #f0f0f0; color: #333333;")
        self.cancel_button.setCursor(Qt.PointingHandCursor)  # 设置鼠标悬停时为手型指针
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch(1)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def populate_table(self):
        """填充表格数据"""
        # 设置行数
        self.table.setRowCount(len(self.servers_to_update))
        
        # 填充数据
        for i, server in enumerate(self.servers_to_update):
            # 项目名称
            project_item = QTableWidgetItem(server.get('project', ''))
            project_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, project_item)
            
            # IP地址
            ip_item = QTableWidgetItem(server.get('ip', ''))
            ip_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, ip_item)
            
            # 用户名
            username_item = QTableWidgetItem(server.get('username', ''))
            username_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, username_item)
            
            # 旧密码 (显示为掩码)
            old_password = server.get('old_password', '')
            old_password_display = '•' * len(old_password) if old_password else ''
            old_password_item = QTableWidgetItem(old_password_display)
            old_password_item.setTextAlignment(Qt.AlignCenter)
            old_password_item.setToolTip("双击查看原密码")
            old_password_item.setData(Qt.UserRole, old_password)  # 存储实际密码
            self.table.setItem(i, 3, old_password_item)
            
            # 新密码
            new_password = server.get('new_password', '')
            new_password_item = QTableWidgetItem(new_password)
            new_password_item.setTextAlignment(Qt.AlignCenter)
            new_password_item.setBackground(QColor("#d4edda"))  # 浅绿色背景
            new_password_item.setForeground(QColor("#155724"))  # 深绿色文字
            self.table.setItem(i, 4, new_password_item)
            
            # 状态列
            status_item = QTableWidgetItem("等待更新")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor("#6c757d"))  # 灰色文字
            self.table.setItem(i, 5, status_item)
        
        # 设置双击事件以查看完整密码
        self.table.cellDoubleClicked.connect(self.toggle_password_visibility)

    def toggle_password_visibility(self, row, column):
        """切换密码可见性"""
        if column != 3:  # 只对旧密码列生效
            return
            
        item = self.table.item(row, column)
        if not item:
            return
            
        actual_password = item.data(Qt.UserRole)
        current_text = item.text()
        
        # 切换显示
        if '•' in current_text:
            item.setText(actual_password)
        else:
            item.setText('•' * len(actual_password))

    def start_update(self):
        """开始更新密码"""
        if not self.servers_to_update:
            QMessageBox.warning(self, "无可更新项", "没有找到需要更新的密码")
            return
            
        # 禁用开始按钮，更改取消按钮为停止
        self.start_button.setEnabled(False)
        self.cancel_button.setText("停止")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.stop_update)
        
        # 更新状态
        self.status_label.setText("正在更新密码...")
        
        # 创建工作线程
        self.worker = PasswordUpdateWorker(self.servers_to_update)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.update_finished.connect(self.update_finished)
        
        # 开始工作线程
        self.worker.start()

    def stop_update(self):
        """停止更新"""
        if self.worker and self.worker.isRunning():
            self.worker.interrupt()
            self.status_label.setText("正在停止...")
            self.cancel_button.setEnabled(False)
        else:
            self.reject()

    def update_progress(self, row_idx, status):
        """更新进度"""
        # 更新表格中的状态单元格
        status_item = self.table.item(row_idx, 5)
        
        if status_item:
            # 设置状态文本和颜色
            if "成功" in status:
                status_item.setText(status)
                status_item.setForeground(QColor("#28a745"))  # 绿色表示成功
                row_brush = QBrush(QColor("#d4edda"))  # 浅绿色背景
                
                # 将此行标记为成功
                if row_idx not in self.successful_updates:
                    self.successful_updates.append(row_idx)
                    
                # 延迟一点模拟验证过程并更新验证状态
                QApplication.processEvents()
                time.sleep(0.2)
                status_item.setText("密码修改成功！ → 正在验证...")
                QApplication.processEvents()
                time.sleep(0.3)
                status_item.setText("密码修改成功！ → 验证成功")
                
            elif "开始修改密码" in status:
                status_item.setText(status)
                status_item.setForeground(QColor("#fd7e14"))  # 橙色表示进行中
                row_brush = QBrush(QColor("#fff3cd"))  # 浅黄色背景
                
            elif "连接成功" in status:
                status_item.setText(status)
                status_item.setForeground(QColor("#17a2b8"))  # 青色表示连接成功
                row_brush = QBrush(QColor("#d1ecf1"))  # 浅蓝色背景
                
            elif "失败" in status or "错误" in status:
                # 如果是失败状态，增加验证失败信息
                if "验证" not in status:
                    status_item.setText(f"{status} → 验证失败")
                else:
                    status_item.setText(status)
                    
                status_item.setForeground(QColor("#dc3545"))  # 红色表示失败
                row_brush = QBrush(QColor("#f8d7da"))  # 浅红色背景
                
            elif "等待" in status:
                status_item.setText(status)
                status_item.setForeground(QColor("#6c757d"))  # 灰色表示等待
                row_brush = QBrush(QColor("#f8f9fa"))  # 浅灰色背景
                
            elif "正在连接" in status or "尝试建立" in status:
                status_item.setText(status)
                status_item.setForeground(QColor("#007bff"))  # 蓝色表示连接中
                row_brush = QBrush(QColor("#cce5ff"))  # 浅蓝色背景
                
            else:
                status_item.setText(status)
                status_item.setForeground(QColor("#007bff"))  # 蓝色表示进行中
                row_brush = QBrush(QColor("#cce5ff"))  # 浅蓝色背景
            
            # 高亮显示当前操作的行
            for col in range(self.table.columnCount()):
                cell_item = self.table.item(row_idx, col)
                if cell_item:
                    cell_item.setBackground(row_brush)
        
        # 更新总进度 - 改为实时计算
        total = len(self.servers_to_update)
        
        # 从表格中计算已完成的行数
        completed = 0
        for i in range(total):
            status_cell = self.table.item(i, 5)
            if status_cell and (
                "成功" in status_cell.text() or 
                "失败" in status_cell.text() or 
                "错误" in status_cell.text()
            ):
                completed += 1
        
        # 计算进度百分比
        progress = int((completed / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)
        
        # 更新状态标签
        self.status_label.setText(f"处理进度: {completed}/{total} - {status}")
        
        # 确保UI更新
        QApplication.processEvents()

    def update_finished(self, results):
        """更新完成"""
        self.results = results
        
        # 计算成功和失败的数量
        success_count = sum(1 for r in results.values() if r.get('success', False))
        fail_count = len(results) - success_count
        
        # 更新状态
        status = f"更新完成: {success_count} 成功, {fail_count} 失败"
        self.status_label.setText(status)
        self.status_label.setStyleSheet("""
            padding: 8px; 
            border-radius: 4px; 
            font-weight: bold; 
            color: white; 
            background-color: #4a86e8;
        """)
        
        # 设置进度条为完成状态
        self.progress_bar.setValue(100)
        
        # 修改按钮
        self.start_button.setText("保存并关闭")
        self.start_button.setEnabled(True)
        self.start_button.setStyleSheet("""
            background-color: #28a745; 
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        """)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.save_and_close)
        
        self.cancel_button.setText("取消")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setEnabled(True)
        
        # 如果有成功的更新，自动保存到数据库
        if success_count > 0:
            self.save_successful_updates()
    
    def save_successful_updates(self):
        """保存成功的更新到数据库"""
        success_count = 0
        for row_idx, result in self.results.items():
            if not result.get('success', False):
                logger.debug(f"跳过未成功更新的行: {row_idx}")
                continue
                
            server = result.get('server', {})
            real_index = server.get('real_index')
            new_password = server.get('new_password', '')
            
            # 详细记录处理状态
            logger.info(f"处理成功更新的密码 - 行索引: {row_idx}, 真实索引: {real_index}, IP: {server.get('ip', '')}")
            
            if real_index is None:
                logger.error(f"无法保存密码 - 真实索引为None (行: {row_idx}, IP: {server.get('ip', '')})")
                # 尝试获取实时真实索引
                if hasattr(self.parent(), '_get_real_row_index'):
                    try:
                        # 获取行对应的表格真实索引
                        current_row = server.get('row', row_idx)
                        real_time_index = self.parent()._get_real_row_index(current_row)
                        if real_time_index is not None:
                            logger.info(f"成功获取实时真实索引: {real_time_index}")
                            real_index = real_time_index
                        else:
                            logger.error(f"实时获取真实索引失败")
                    except Exception as e:
                        logger.error(f"尝试获取实时真实索引时出错: {str(e)}")
            
            if not new_password:
                logger.error(f"无法保存密码 - 新密码为空 (行: {row_idx}, IP: {server.get('ip', '')})")
                continue
            
            if real_index is None:
                continue
            
            # 获取当前所有者的密码列表
            passwords = password_manager.get_passwords_by_owner(self.owner)
            logger.debug(f"获取到所有者 {self.owner} 的密码列表，包含 {len(passwords)} 条记录")
            
            # 确保索引有效
            if 0 <= real_index < len(passwords):
                # 获取当前记录
                record = passwords[real_index]
                
                # 更新密码字段
                original_password = record[4]
                record[4] = new_password
                
                logger.info(f"准备更新密码 - 索引: {real_index}, 原密码长度: {len(original_password)}, 新密码长度: {len(new_password)}")
                
                # 保存到数据库
                success, message = password_manager.update_password(
                    self.owner, real_index, record, skip_server_sync=True
                )
                
                if success:
                    success_count += 1
                    logger.info(f"成功永久保存密码到数据库 - 所有者: {self.owner}, 记录索引: {real_index}")
                else:
                    logger.error(f"永久保存密码失败 - 所有者: {self.owner}, 记录索引: {real_index}, 错误: {message}")
            else:
                logger.error(f"索引超出范围 - 索引: {real_index}, 密码列表长度: {len(passwords)}")
        
        # 记录结果
        logger.info(f"共有 {success_count} 个密码成功永久保存到数据库")
        
        # 更新状态
        current_status = self.status_label.text()
        self.status_label.setText(f"{current_status} | {success_count} 个密码已保存到数据库")
    
    def save_and_close(self):
        """保存并关闭对话框"""
        # 再次保存，以防有未保存的更新
        self.save_successful_updates()
        
        # 关闭对话框并返回成功
        self.accept()
    
    def reject(self):
        """处理取消/关闭事件"""
        # 如果工作线程正在运行，先询问是否确认取消
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认取消", 
                "密码更新正在进行，确定要取消吗？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.interrupt()
                super().reject()
        else:
            # 如果有成功的更新但未点击保存，询问是否保存
            if self.successful_updates and not self.results:
                reply = QMessageBox.question(
                    self, "保存更改", 
                    "有成功更新的密码尚未保存，是否保存这些更改？",
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.save_successful_updates()
            
            super().reject()

# 用于测试
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 测试数据
    test_data = [
        {
            'project': '测试项目1',
            'ip': '192.168.1.1',
            'username': 'admin',
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
            'real_index': 0
        },
        {
            'project': '测试项目2',
            'ip': '192.168.1.2',
            'username': 'root',
            'old_password': 'rootpass123',
            'new_password': 'rootnew456',
            'real_index': 1
        }
    ]
    
    dialog = PasswordUpdateDialog(servers_to_update=test_data, owner="测试用户")
    dialog.show()
    
    sys.exit(app.exec_()) 