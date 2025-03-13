#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SSH日志可视化查看器

提供图形界面，方便查看和分析SSH操作日志。
"""

import sys
import os
import datetime
import logging
from typing import List, Dict, Optional, Tuple

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTableWidget, 
                            QTableWidgetItem, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QLineEdit, QComboBox, 
                            QCheckBox, QTabWidget, QTextEdit, QSpinBox,
                            QFileDialog, QMessageBox, QHeaderView, QStyle, 
                            QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor, QFont

from view_ssh_logs import read_log_file, parse_log_line, filter_logs, analyze_logs

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SSHLogViewer(QMainWindow):
    """SSH日志查看器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.log_file = 'logs/ssh_operations.log'  # 默认日志文件
        self.logs = []  # 存储所有日志行
        self.filtered_logs = []  # 存储过滤后的日志行
        
        self.init_ui()
        self.load_logs()
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle('SSH日志查看器')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部控制区域
        control_layout = QHBoxLayout()
        
        # 日志文件选择
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("日志文件:"))
        self.file_path_edit = QLineEdit(self.log_file)
        self.file_path_edit.setReadOnly(True)
        file_layout.addWidget(self.file_path_edit)
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_button)
        control_layout.addLayout(file_layout)
        
        # 最大行数
        lines_layout = QHBoxLayout()
        lines_layout.addWidget(QLabel("显示行数:"))
        self.lines_spin = QSpinBox()
        self.lines_spin.setRange(0, 10000)
        self.lines_spin.setValue(0)
        self.lines_spin.setSpecialValueText("全部")
        lines_layout.addWidget(self.lines_spin)
        control_layout.addLayout(lines_layout)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.load_logs)
        control_layout.addWidget(refresh_button)
        
        main_layout.addLayout(control_layout)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 日志查看选项卡
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        
        # 过滤选项
        filter_group = QGroupBox("过滤条件")
        filter_layout = QGridLayout()
        
        # 级别过滤
        filter_layout.addWidget(QLabel("日志级别:"), 0, 0)
        self.level_combo = QComboBox()
        self.level_combo.addItem("全部", None)
        self.level_combo.addItem("INFO", "INFO")
        self.level_combo.addItem("ERROR", "ERROR")
        filter_layout.addWidget(self.level_combo, 0, 1)
        
        # IP地址过滤
        filter_layout.addWidget(QLabel("IP地址:"), 0, 2)
        self.ip_edit = QLineEdit()
        filter_layout.addWidget(self.ip_edit, 0, 3)
        
        # 用户名过滤
        filter_layout.addWidget(QLabel("用户名:"), 1, 0)
        self.username_edit = QLineEdit()
        filter_layout.addWidget(self.username_edit, 1, 1)
        
        # 成功/失败过滤
        self.success_check = QCheckBox("只显示成功")
        filter_layout.addWidget(self.success_check, 1, 2)
        self.error_check = QCheckBox("只显示错误")
        filter_layout.addWidget(self.error_check, 1, 3)
        
        # 应用过滤按钮
        filter_button = QPushButton("应用过滤")
        filter_button.clicked.connect(self.apply_filter)
        filter_layout.addWidget(filter_button, 2, 3)
        
        filter_group.setLayout(filter_layout)
        logs_layout.addWidget(filter_group)
        
        # 日志表格
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(6)
        self.log_table.setHorizontalHeaderLabels(["时间", "级别", "进程ID", "消息", "IP", "用户名"])
        self.log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        logs_layout.addWidget(self.log_table)
        
        # 详细信息区域
        detail_group = QGroupBox("日志详情")
        detail_layout = QVBoxLayout()
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        detail_group.setLayout(detail_layout)
        logs_layout.addWidget(detail_group)
        
        # 添加日志查看选项卡
        tab_widget.addTab(logs_tab, "日志查看")
        
        # 分析选项卡
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # 分析结果文本区域
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setFont(QFont("Consolas", 10))
        analysis_layout.addWidget(self.analysis_text)
        
        # 分析按钮
        analyze_button = QPushButton("分析日志")
        analyze_button.clicked.connect(self.analyze_logs)
        analysis_layout.addWidget(analyze_button)
        
        # 添加分析选项卡
        tab_widget.addTab(analysis_tab, "日志分析")
        
        # 将选项卡添加到主布局
        main_layout.addWidget(tab_widget)
        
        # 连接信号
        self.log_table.itemSelectionChanged.connect(self.show_log_details)
        self.success_check.stateChanged.connect(self.update_error_check_state)
        self.error_check.stateChanged.connect(self.update_success_check_state)
        
    def browse_file(self):
        """浏览选择日志文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择日志文件", os.path.dirname(self.log_file), 
            "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*.*)"
        )
        if file_path:
            self.log_file = file_path
            self.file_path_edit.setText(file_path)
            self.load_logs()
    
    def load_logs(self):
        """加载日志数据"""
        try:
            lines = self.lines_spin.value()
            self.logs = read_log_file(self.log_file, lines)
            self.apply_filter()
            self.statusBar().showMessage(f"已加载 {len(self.logs)} 行日志")
        except Exception as e:
            logger.error(f"加载日志失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载日志失败: {str(e)}")
    
    def apply_filter(self):
        """应用过滤条件"""
        level = self.level_combo.currentData()
        ip = self.ip_edit.text().strip() or None
        username = self.username_edit.text().strip() or None
        success_only = self.success_check.isChecked()
        error_only = self.error_check.isChecked()
        
        self.filtered_logs = filter_logs(
            self.logs, level=level, ip=ip, username=username,
            success_only=success_only, error_only=error_only
        )
        self.display_logs()
        self.statusBar().showMessage(f"显示 {len(self.filtered_logs)}/{len(self.logs)} 行日志")
    
    def display_logs(self):
        """在表格中显示日志数据"""
        self.log_table.setRowCount(0)  # 清空表格
        
        for row, log in enumerate(self.filtered_logs):
            parsed = parse_log_line(log)
            if not parsed:
                continue
                
            self.log_table.insertRow(row)
            
            # 设置单元格内容
            timestamp_item = QTableWidgetItem(parsed["timestamp"])
            level_item = QTableWidgetItem(parsed["level"])
            process_id_item = QTableWidgetItem(parsed["process_id"])
            message_item = QTableWidgetItem(parsed["message"])
            ip_item = QTableWidgetItem(parsed["ip_address"] or "")
            username_item = QTableWidgetItem(parsed["username"] or "")
            
            # 为日志级别设置颜色
            if parsed["level"] == "ERROR":
                level_item.setForeground(QColor("red"))
                message_item.setForeground(QColor("red"))
            
            # 添加项目到表格
            self.log_table.setItem(row, 0, timestamp_item)
            self.log_table.setItem(row, 1, level_item)
            self.log_table.setItem(row, 2, process_id_item)
            self.log_table.setItem(row, 3, message_item)
            self.log_table.setItem(row, 4, ip_item)
            self.log_table.setItem(row, 5, username_item)
        
        # 调整列宽
        self.log_table.resizeColumnsToContents()
    
    def show_log_details(self):
        """显示选中日志行的详细信息"""
        selected_rows = self.log_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        
        if 0 <= row < len(self.filtered_logs):
            log_line = self.filtered_logs[row]
            parsed = parse_log_line(log_line)
            
            if parsed:
                detail_text = f"时间: {parsed['timestamp']}\n"
                detail_text += f"级别: {parsed['level']}\n"
                detail_text += f"进程ID: {parsed['process_id']}\n"
                detail_text += f"消息: {parsed['message']}\n"
                
                if parsed["ip_address"]:
                    detail_text += f"IP地址: {parsed['ip_address']}\n"
                    
                if parsed["username"]:
                    detail_text += f"用户名: {parsed['username']}\n"
                    
                self.detail_text.setText(detail_text)
    
    def analyze_logs(self):
        """分析日志数据并显示结果"""
        try:
            analysis = analyze_logs(self.filtered_logs)
            
            # 格式化分析结果
            result_text = "==== SSH操作日志分析 ====\n\n"
            result_text += f"总日志行数: {analysis['总日志行数']}\n"
            result_text += f"信息日志数: {analysis['信息日志数']}\n"
            result_text += f"错误日志数: {analysis['错误日志数']}\n"
            result_text += f"成功操作数: {analysis['成功操作数']}\n"
            result_text += f"失败操作数: {analysis['失败操作数']}\n\n"
            
            if analysis["最早记录时间"] and analysis["最新记录时间"]:
                result_text += f"日志时间范围: {analysis['最早记录时间']} 至 {analysis['最新记录时间']}\n\n"
            
            result_text += "服务器IP统计:\n"
            for ip, count in analysis["服务器IP统计"].most_common(10):
                result_text += f"  {ip}: {count}次\n"
            
            result_text += "\n用户名统计:\n"
            for username, count in analysis["用户名统计"].most_common(10):
                result_text += f"  {username}: {count}次\n"
                
            result_text += "\n错误类型统计:\n"
            for error_type, count in analysis["错误类型统计"].most_common():
                result_text += f"  {error_type}: {count}次\n"
            
            self.analysis_text.setText(result_text)
            
        except Exception as e:
            logger.error(f"分析日志失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"分析日志失败: {str(e)}")
    
    def update_error_check_state(self, state):
        """更新错误选择框状态"""
        if state == Qt.Checked:
            self.error_check.setChecked(False)
    
    def update_success_check_state(self, state):
        """更新成功选择框状态"""
        if state == Qt.Checked:
            self.success_check.setChecked(False)


def main():
    """主函数"""
    try:
        app = QApplication(sys.argv)
        viewer = SSHLogViewer()
        viewer.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"程序执行异常: {str(e)}")
        print(f"程序执行异常: {str(e)}")


if __name__ == "__main__":
    main() 