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
                             QSizePolicy, QWhatsThis, QTextBrowser)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QEvent
from PyQt5.QtGui import QColor, QBrush, QIcon, QFont, QCursor

from password import password_manager
from ssh_password_updater import ssh_password_updater
from encrypt import encryptor
from audit_log import audit_logger, OP_TYPE_SSH_UPDATE, OP_RESULT_SUCCESS, OP_RESULT_FAIL, OP_RESULT_INFO, LOG_TYPE_SSH
from config import FONT_FAMILY, COLORS

logger = logging.getLogger(__name__)

# 定义状态常量
STATUS_WAITING = "等待更新..."
STATUS_CONNECTING = "尝试连接服务器..."
STATUS_CONNECTED = "连接成功，开始修改密码..."
STATUS_MODIFYING = "正在修改密码..."
STATUS_MODIFIED = "密码修改成功，开始验证..."
STATUS_VERIFYING = "开始验证修改..."
STATUS_VERIFY_CONNECTING = "尝试使用新密码连接..."
STATUS_VERIFY_CONNECTED = "新密码连接成功..."
STATUS_VERIFY_SUCCESS = "更新成功！！！"
STATUS_SUCCESS = "密码修改成功！"
STATUS_FAILED = "更新失败: {0}"
STATUS_CONNECT_FAILED = "连接失败: {0}"

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
            self.update_progress.emit(row_idx, STATUS_WAITING)
            
            # 更新进度 - 尝试连接服务器
            self.update_progress.emit(row_idx, STATUS_CONNECTING)
            
            # 执行SSH密码更新
            try:
                # 创建SSH客户端
                from paramiko import SSHClient, AutoAddPolicy
                import socket
                
                ssh = SSHClient()
                ssh.set_missing_host_key_policy(AutoAddPolicy())
                
                # 设置连接超时
                connect_timeout = 10  # 10秒超时
                
                # 尝试连接
                try:
                    ssh.connect(
                        ip, 
                        username=username, 
                        password=old_password, 
                        timeout=connect_timeout
                    )
                    
                    # 连接成功，更新状态
                    self.update_progress.emit(row_idx, STATUS_CONNECTED)
                    
                    # 关闭连接
                    ssh.close()
                    
                    # 开始修改密码
                    self.update_progress.emit(row_idx, STATUS_MODIFYING)
                    
                    # 创建自定义消息监听器
                    class StatusMonitor:
                        def __init__(self, worker, row_idx):
                            self.worker = worker
                            self.row_idx = row_idx
                            self.last_log_line = ""
                            
                        def check_ssh_log(self, log_file_path):
                            try:
                                with open(log_file_path, 'r', encoding='utf-8') as f:
                                    # 读取最后几行
                                    lines = f.readlines()[-20:]
                                    for line in reversed(lines):
                                        if line != self.last_log_line:
                                            self.last_log_line = line
                                            # 根据日志内容更新UI状态
                                            if "密码修改成功，开始验证" in line:
                                                self.worker.update_progress.emit(self.row_idx, STATUS_MODIFIED)
                                            elif "开始验证修改" in line:
                                                self.worker.update_progress.emit(self.row_idx, STATUS_VERIFYING)
                                            elif "尝试使用新密码连接" in line:
                                                self.worker.update_progress.emit(self.row_idx, STATUS_VERIFY_CONNECTING)
                                            elif "新密码连接成功" in line:
                                                self.worker.update_progress.emit(self.row_idx, STATUS_VERIFY_CONNECTED)
                                            # 一旦找到最新的状态就跳出
                                            break
                            except Exception as e:
                                # 静默忽略监控错误
                                pass
                    
                    # 创建状态监控器
                    monitor = StatusMonitor(self, row_idx)
                    
                    # 获取SSH日志文件路径
                    ssh_log_path = ssh_password_updater.get_log_file_path()
                    
                    # 启动后台监控线程
                    import threading
                    stop_monitoring = threading.Event()
                    
                    def monitor_log():
                        while not stop_monitoring.is_set():
                            monitor.check_ssh_log(ssh_log_path)
                            time.sleep(0.1)  # 100ms检查一次
                    
                    monitor_thread = threading.Thread(target=monitor_log)
                    monitor_thread.daemon = True
                    monitor_thread.start()

                    # 调用密码更新方法
                    try:
                        success, message, verify_success = ssh_password_updater.update_password(
                            ip=ip,
                            username=username,
                            old_password=old_password,
                            new_password=new_password
                        )
                        
                        if success:
                            if verify_success:
                                self.update_progress.emit(row_idx, STATUS_VERIFY_SUCCESS)
                            else:
                                self.update_progress.emit(row_idx, STATUS_SUCCESS)
                        else:
                            self.update_progress.emit(row_idx, STATUS_FAILED.format(message))
                    finally:
                        # 停止监控线程
                        stop_monitoring.set()
                        # 确保等待线程结束
                        monitor_thread.join(timeout=0.5)
                    
                except socket.timeout:
                    self.update_progress.emit(row_idx, STATUS_CONNECT_FAILED.format(f"连接超时（超过{connect_timeout}秒）"))
                    success = False
                    message = f"连接超时（超过{connect_timeout}秒）"
                    verify_success = False
                except Exception as e:
                    self.update_progress.emit(row_idx, STATUS_CONNECT_FAILED.format(str(e)))
                    success = False
                    message = str(e)
                    verify_success = False
                    
            except Exception as e:
                success = False
                message = str(e)
                verify_success = False
                self.update_progress.emit(row_idx, STATUS_FAILED.format(message))
            
            # 保存结果
            self.results[row_idx] = {
                'success': success,
                'message': message,
                'verify_success': verify_success,
                'server': server
            }
            
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
        
        # 设置帮助按钮在标题栏上显示
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)
        
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
        title_layout.addWidget(title_label)
        
        # 描述标签
        desc_label = QLabel('以下是将要更新的密码列表，点击"开始更新"按钮开始更新密码。')
        desc_label.setFont(QFont(FONT_FAMILY, 10))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #555555;")
        
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
        self.progress_bar.setFormat("%p%")  # 显示百分比
        progress_layout.addWidget(self.progress_bar)
        
        info_layout.addLayout(progress_layout)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont(FONT_FAMILY, 10))
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 4px;")
        info_layout.addWidget(self.status_label)
        
        # 添加提示信息
        notice_label = QLabel("温馨提示：密码更新成功的服务器将在数据库中记录新密码，更新失败的服务器将保持旧密码不变。\n更新完成后，请点击下方\"完成并关闭\"按钮，完成记录操作。")
        notice_label.setFont(QFont(FONT_FAMILY, 9))
        notice_label.setAlignment(Qt.AlignCenter)
        notice_label.setStyleSheet("""
            color: #dc3545; 
            background-color: #f8d7da; 
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 8px;
            margin: 5px 0;
        """)
        info_layout.addWidget(notice_label)
        
        layout.addLayout(info_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(50, 10, 50, 10)  # 左右增加边距
        
        # 开始更新按钮
        self.start_button = QPushButton("开始更新")
        self.start_button.setMinimumWidth(200)  # 增加按钮宽度
        self.start_button.setMinimumHeight(40)  # 增加按钮高度
        self.start_button.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        self.start_button.setCursor(Qt.PointingHandCursor)  # 设置鼠标悬停时为手型指针
        self.start_button.clicked.connect(self.start_update)
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.start_button)
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
            old_password_display = old_password if old_password else ''  # 直接显示明文密码
            old_password_item = QTableWidgetItem(old_password_display)
            old_password_item.setTextAlignment(Qt.AlignCenter)
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
            
        # 禁用开始按钮
        self.start_button.setEnabled(False)
        self.start_button.setText("更新中...")
        
        # 更新状态
        self.status_label.setText("正在更新密码...")
        
        # 创建工作线程
        self.worker = PasswordUpdateWorker(self.servers_to_update)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.update_finished.connect(self.update_finished)
        
        # 开始工作线程
        self.worker.start()
        
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 如果更新过程正在进行中
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认关闭", 
                "密码更新正在进行中，关闭窗口将会中断更新过程。是否确认关闭？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 中断更新过程
                self.worker.interrupt()
                event.accept()
            else:
                event.ignore()
        # 如果更新完成，但有未保存的更改
        elif hasattr(self, 'successful_updates') and self.successful_updates and not hasattr(self, 'results'):
            reply = QMessageBox.question(
                self, "保存更改", 
                "有成功更新的密码尚未保存，是否保存这些更改？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.save_successful_updates()
            
            event.accept()
        else:
            event.accept()

    def update_progress(self, row_idx, status):
        """更新进度"""
        # 更新表格中的状态单元格
        status_item = self.table.item(row_idx, 5)
        
        if status_item:
            # 设置状态文本
            status_item.setText(status)
            
            # 简化的颜色逻辑
            if "成功" in status:
                status_item.setForeground(QColor("#28a745"))  # 绿色
                row_brush = QBrush(QColor("#d4edda"))  # 浅绿色背景
                
                # 将此行标记为成功
                if row_idx not in self.successful_updates:
                    self.successful_updates.append(row_idx)
            elif "失败" in status or "错误" in status:
                status_item.setForeground(QColor("#dc3545"))  # 红色
                row_brush = QBrush(QColor("#f8d7da"))  # 浅红色背景
            elif "连接成功" in status:
                status_item.setForeground(QColor("#17a2b8"))  # 青色
                row_brush = QBrush(QColor("#d1ecf1"))  # 浅蓝色背景
            else:
                status_item.setForeground(QColor("#fd7e14"))  # 橙色
                row_brush = QBrush(QColor("#fff3cd"))  # 浅黄色背景
                
            # 设置整行背景色
            for col in range(self.table.columnCount()):
                item = self.table.item(row_idx, col)
                if item:
                    item.setBackground(row_brush)
        
        # 定义每个状态对应的进度百分比
        status_progress = {
            STATUS_WAITING: 0,
            STATUS_CONNECTING: 10,
            STATUS_CONNECTED: 20,
            STATUS_MODIFYING: 30,
            STATUS_MODIFIED: 60,
            STATUS_VERIFYING: 70,
            STATUS_VERIFY_CONNECTING: 80,
            STATUS_VERIFY_CONNECTED: 90,
            STATUS_VERIFY_SUCCESS: 100,
            STATUS_SUCCESS: 95,  # 修改成功但未完全验证
            STATUS_FAILED: 100,  # 虽然失败但进度已完成
            STATUS_CONNECT_FAILED: 100  # 连接失败也视为进度完成
        }
        
        # 更新总进度 - 考虑每个服务器的当前进度
        total = len(self.servers_to_update)
        total_progress = 0
        
        for i in range(total):
            status_cell = self.table.item(i, 5)
            if status_cell:
                current_status = status_cell.text()
                
                # 处理包含动态内容的状态，如错误消息
                if "失败" in current_status or "错误" in current_status:
                    cell_progress = 100
                else:
                    # 检查状态是否在我们定义的映射中
                    matched = False
                    for key, value in status_progress.items():
                        if key in current_status:
                            cell_progress = value
                            matched = True
                            break
                    
                    # 如果没有匹配项，默认为0
                    if not matched:
                        cell_progress = 0
            else:
                cell_progress = 0
                
            total_progress += cell_progress
        
        # 计算平均进度百分比
        average_progress = int(total_progress / total) if total > 0 else 0
        self.progress_bar.setValue(average_progress)
        
        # 更新状态标签
        current_count = sum(1 for i in range(total) if self.table.item(i, 5) and 
                          any(s in self.table.item(i, 5).text() for s in ["成功", "失败", "错误"]))
        
        # 显示进度百分比和当前状态
        self.status_label.setText(f"总进度: {average_progress}% - 已完成: {current_count}/{total} - {status}")
        
        # 确保UI更新
        QApplication.processEvents()

    def update_finished(self, results):
        """更新完成"""
        self.results = results
        
        # 计算成功和失败的数量
        success_count = sum(1 for r in results.values() if r.get('success', False))
        verified_count = sum(1 for r in results.values() if r.get('success', False) and r.get('verify_success', False))
        fail_count = len(results) - success_count
        
        # 计算最终的进度百分比 - 所有操作已完成，应为100%
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("100%  完成")
        
        # 给进度条一个完成的颜色状态
        if verified_count == len(results):  # 全部成功且验证
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #28a745;  /* 绿色 */
                    border-radius: 2px;
                }
            """)
        elif success_count > 0:  # 部分成功
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #ffc107;  /* 黄色 */
                    border-radius: 2px;
                }
            """)
        else:  # 全部失败
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #dc3545;  /* 红色 */
                    border-radius: 2px;
                }
            """)
        
        # 更新状态
        if verified_count == success_count and success_count == len(results):
            status = f"全部更新成功并验证成功: {success_count} 个服务器"
        elif success_count > 0 and verified_count < success_count:
            status = f"更新完成: {success_count} 成功 (其中 {verified_count} 个验证成功), {fail_count} 失败"
        else:
            status = f"更新完成: {success_count} 成功, {fail_count} 失败"
            
        self.status_label.setText(status)
        self.status_label.setStyleSheet("""
            padding: 8px; 
            border-radius: 4px; 
            font-weight: bold; 
            color: white; 
            background-color: #4a86e8;
        """)
        
        # 修改按钮
        self.start_button.setText("完成并关闭")
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
        
        # 记录审计日志
        owner = self.owner if hasattr(self, 'owner') else "未知"
        audit_logger.log_operation(
            operation_type=OP_TYPE_SSH_UPDATE,
            result=OP_RESULT_SUCCESS if success_count == len(results) else OP_RESULT_FAIL,
            details=f"批量SSH密码更新完成: {success_count}成功, {fail_count}失败",
            target=f"{owner}/批量更新",
            log_type=LOG_TYPE_SSH
        )
    
    def save_successful_updates(self):
        """保存成功的更新到数据库"""
        if not self.results:
            return
            
        owner = self.owner
        success_count = 0
        
        for row_idx, result in self.results.items():
            if result.get('success', False):
                server = result.get('server', {})
                real_index = server.get('real_index')
                new_password = server.get('new_password')
                ip = server.get('ip')
                
                if real_index is not None and new_password and owner:
                    # 获取原始记录
                    passwords = password_manager.get_passwords_by_owner(owner)
                    
                    if 0 <= real_index < len(passwords):
                        # 更新密码字段
                        passwords[real_index][4] = new_password
                        
                        # 保存到数据库，跳过服务器同步
                        db_success, _ = password_manager.update_password(
                            owner, real_index, passwords[real_index], skip_server_sync=True
                        )
                        
                        if db_success:
                            success_count += 1
                            logger.info(f"成功保存密码到数据库 - 服务器: {ip}, 索引: {real_index}")
                        else:
                            logger.error(f"保存密码到数据库失败 - 服务器: {ip}, 索引: {real_index}")
        
        current_status = self.status_label.text()
        self.status_label.setText(f"{current_status} | {success_count} 个密码已保存到数据库")
    
    def save_and_close(self):
        """完成并关闭对话框"""
        # 再次保存，以防有未保存的更新
        self.save_successful_updates()
        
        # 关闭对话框并返回成功
        self.accept()

    def event(self, event):
        """处理事件，包括帮助事件"""
        if event.type() == QEvent.EnterWhatsThisMode:
            self.show_help()
            return True
        return super().event(event)

    def show_help(self):
        """显示帮助信息对话框"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("密码更新帮助")
        help_dialog.resize(500, 600)
        help_dialog.setStyleSheet("background-color: #f5f5f7; color: #333333;")
        
        layout = QVBoxLayout(help_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("密码更新流程说明")
        title.setFont(QFont(FONT_FAMILY, 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2a66c8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 使用QTextBrowser支持富文本
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        text_browser.setStyleSheet("""
            background-color: white;
            border: 1px solid #cccccc;
            border-radius: 5px;
            padding: 10px;
        """)
        
        # 帮助内容
        help_content = """
        <div style='font-family: Microsoft YaHei; font-size: 12px;'>
        <h3 style='color: #2a66c8;'>密码更新流程说明</h3>
        <p><b>更新流程:</b></p>
        <ol>
        <li><span style='color: #fd7e14;'><b>等待更新</b></span>: 准备更新密码 (0%)</li>
        <li><span style='color: #fd7e14;'><b>尝试连接服务器</b></span>: 正在连接到目标服务器 (10%)</li>
        <li><span style='color: #17a2b8;'><b>连接成功</b></span>: 已成功连接到服务器 (20%)</li>
        <li><span style='color: #fd7e14;'><b>开始修改密码</b></span>: 正在执行修改密码的命令 (30%)</li>
        <li><span style='color: #fd7e14;'><b>密码修改成功</b></span>: 密码已修改，准备验证 (60%)</li>
        <li><span style='color: #fd7e14;'><b>开始验证修改</b></span>: 正在验证新密码是否生效 (70%)</li>
        <li><span style='color: #fd7e14;'><b>尝试使用新密码连接</b></span>: 正在尝试使用新密码连接 (80%)</li>
        <li><span style='color: #fd7e14;'><b>新密码连接成功</b></span>: 使用新密码已成功连接 (90%)</li>
        <li><span style='color: #28a745;'><b>更新成功</b></span>: 密码修改和验证都已完成 (100%)</li>
        </ol>

        <p><b>状态颜色说明:</b></p>
        <ul>
        <li><span style='color: #fd7e14;'>■</span> <b>橙色</b>: 进行中的状态</li>
        <li><span style='color: #17a2b8;'>■</span> <b>蓝色</b>: 连接成功状态</li>
        <li><span style='color: #28a745;'>■</span> <b>绿色</b>: 完成/成功状态</li>
        <li><span style='color: #dc3545;'>■</span> <b>红色</b>: 失败/错误状态</li>
        </ul>

        <p><b>重要提示:</b><br>
        当更新完成后，请点击"<span style='color: #28a745;'><b>完成并关闭</b></span>"按钮，<br>
        确保新密码能够保存到数据库中。</p>
        </div>
        """
        
        text_browser.setHtml(help_content)
        layout.addWidget(text_browser)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
        """)
        close_button.clicked.connect(help_dialog.close)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        button_layout.addStretch(1)
        
        layout.addLayout(button_layout)
        
        help_dialog.setLayout(layout)
        help_dialog.exec_()

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