#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码历史记录对话框模块
展示密码修改历史记录
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QComboBox, QDateTimeEdit, QHeaderView, 
    QAbstractItemView, QMessageBox, QWidget, QCheckBox, QSpacerItem,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from core.password import password_manager
from core.encrypt import encryptor
from core.data_storage import password_history_storage
from ui.password_manager.ui_utils import create_modern_button

# 配置日志
logger = logging.getLogger(__name__)

# 历史记录表格列
HISTORY_COLUMNS = ["IP地址", "修改前的密码", "修改后的密码", "修改人", "修改时间"]

class PasswordHistoryDialog(QDialog):
    """
    密码历史记录对话框
    
    展示指定密码记录的修改历史
    """
    
    def __init__(self, parent=None, owner="", row_index=-1):
        """
        初始化密码历史记录对话框
        
        Args:
            parent: 父窗口
            owner (str): 密码所有者
            row_index (int): 表格中的行索引
        """
        super().__init__(parent)
        self.owner = owner
        self.row_index = row_index
        self.page = 1
        self.page_size = 10
        self.total_records = 0
        self.current_records = []
        self.warning_message = ""  # 初始化警告消息
        
        # 设置窗口属性
        self.setWindowTitle("密码修改历史记录")
        self.resize(900, 500)
        self.setModal(True)
        
        # 初始化UI
        self.init_ui()
        
        # 加载数据
        self.load_history_data()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title_label = QLabel("密码修改历史记录")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 过滤器布局
        filter_layout = QHBoxLayout()
        
        # 时间范围
        filter_layout.addWidget(QLabel("开始时间:"))
        self.start_date = QDateTimeEdit(QDateTime.currentDateTime().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        filter_layout.addWidget(self.start_date)
        
        filter_layout.addWidget(QLabel("结束时间:"))
        self.end_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.end_date.setCalendarPopup(True)
        filter_layout.addWidget(self.end_date)
        
        # 筛选按钮
        self.filter_button = create_modern_button("筛选", 80, 30)
        self.filter_button.clicked.connect(self.filter_history)
        filter_layout.addWidget(self.filter_button)
        
        # 重置按钮
        self.reset_button = create_modern_button("重置", 80, 30)
        self.reset_button.clicked.connect(self.reset_filter)
        filter_layout.addWidget(self.reset_button)
        
        # 添加到主布局
        main_layout.addLayout(filter_layout)
        
        # 创建表格
        self.table = QTableWidget(0, len(HISTORY_COLUMNS))
        self.table.setHorizontalHeaderLabels(HISTORY_COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # 将列宽模式从Stretch改为ResizeToContents，使列宽自适应内容
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 设置表格样式
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #d6d9dc;
                border-radius: 4px;
                background-color: #ffffff;
                gridline-color: #e1e4e8;
                selection-background-color: #0366d6;
                selection-color: #ffffff;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e1e4e8;
            }
            QTableWidget::item:selected {
                background-color: #0366d6;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f6f8fa;
                color: #24292e;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #e1e4e8;
                border-right: 1px solid #e1e4e8;
                font-weight: bold;
            }
        """)
        
        main_layout.addWidget(self.table)
        
        # 分页控件布局
        pagination_layout = QHBoxLayout()
        
        # 添加导出按钮
        self.export_button = create_modern_button("导出", 80, 30)
        self.export_button.clicked.connect(self.export_history)
        pagination_layout.addWidget(self.export_button)
        
        # 添加间隔
        pagination_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # 当前页/总页数标签
        self.page_info_label = QLabel("第 1 页 / 共 1 页")
        pagination_layout.addWidget(self.page_info_label)
        
        # 上一页按钮
        self.prev_button = create_modern_button("上一页", 80, 30)
        self.prev_button.clicked.connect(self.go_prev_page)
        pagination_layout.addWidget(self.prev_button)
        
        # 下一页按钮
        self.next_button = create_modern_button("下一页", 80, 30)
        self.next_button.clicked.connect(self.go_next_page)
        pagination_layout.addWidget(self.next_button)
        
        # 添加页码选择器
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10条/页", "20条/页", "50条/页", "100条/页"])
        self.page_size_combo.currentIndexChanged.connect(self.change_page_size)
        pagination_layout.addWidget(self.page_size_combo)
        
        # 添加分页布局
        main_layout.addLayout(pagination_layout)
        
        # 底部按钮布局
        button_layout = QHBoxLayout()
        
        # 添加间隔
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # 关闭按钮
        self.close_button = create_modern_button("关闭", 100, 35)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        # 添加底部按钮布局
        main_layout.addLayout(button_layout)
        
    def load_history_data(self):
        """加载历史数据"""
        try:
            # 设置筛选时间
            start_time = self.start_date.dateTime().toString('yyyy-MM-dd hh:mm:ss')
            end_time = self.end_date.dateTime().toString('yyyy-MM-dd hh:mm:ss')
            
            # 记录调试信息
            logger.info(f"开始加载历史数据 - 所有者: {self.owner}, 行索引: {self.row_index}")
            logger.info(f"时间范围: {start_time} 至 {end_time}")
            
            # 获取历史记录
            result = password_manager.get_password_history(
                self.owner,
                self.row_index,
                page=self.page,
                page_size=self.page_size,
                start_time=start_time,
                end_time=end_time
            )
            
            # 更新总记录数和当前页记录
            self.total_records = result.get('total', 0)
            self.current_records = result.get('records', [])
            
            # 清除之前的警告消息
            self.warning_message = ""
            
            # 记录结果信息
            logger.info(f"历史记录查询结果 - 总记录数: {self.total_records}, 当前页记录数: {len(self.current_records)}")
            
            # 处理警告和错误信息
            if 'warning' in result:
                self.warning_message = result['warning']
                logger.warning(f"查询警告: {self.warning_message}")
                
            if 'error' in result:
                error_message = result['error']
                logger.error(f"查询出错: {error_message}")
                QMessageBox.critical(self, "错误", f"加载历史记录失败: {error_message}")
            
            # 更新页码信息
            self.update_page_info()
            
            # 填充表格
            self.populate_table()
            
        except Exception as e:
            logger.error(f"加载历史记录失败: {str(e)}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"加载历史记录失败: {str(e)}")
    
    def populate_table(self):
        """填充表格数据"""
        # 清空表格
        self.table.setRowCount(0)
        
        # 添加调试日志
        logger.info(f"populate_table开始填充表格，记录数：{len(self.current_records)}")
        if self.current_records:
            logger.info(f"第一条记录内容: {self.current_records[0]}")
        
        if not self.current_records:
            # 如果没有记录，添加一行提示
            self.table.setRowCount(1)
            
            # 检查是否有警告信息
            message = "没有找到历史记录"
            if hasattr(self, 'warning_message') and self.warning_message:
                message = self.warning_message
                
            no_data_item = QTableWidgetItem(message)
            no_data_item.setTextAlignment(Qt.AlignCenter)
            font = QFont()
            font.setItalic(True)
            no_data_item.setFont(font)
            self.table.setSpan(0, 0, 1, len(HISTORY_COLUMNS))
            self.table.setItem(0, 0, no_data_item)
            return
        
        # 设置行数
        self.table.setRowCount(len(self.current_records))
        
        # 填充数据
        for i, record in enumerate(self.current_records):
            # IP地址
            ip_item = QTableWidgetItem(record.get('ip_address', ''))
            ip_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, ip_item)
            
            # 修改前的密码
            old_pwd_item = QTableWidgetItem(record.get('old_password', ''))
            old_pwd_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, old_pwd_item)
            
            # 修改后的密码
            new_pwd_item = QTableWidgetItem(record.get('new_password', ''))
            new_pwd_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, new_pwd_item)
            
            # 修改人 (原本是索引4，现在变为索引3)
            user_item = QTableWidgetItem(record.get('modify_user', ''))
            user_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, user_item)
            
            # 修改时间 (原本是索引5，现在变为索引4)
            time_str = record.get('modify_time', '')
            if isinstance(time_str, datetime):
                time_str = time_str.strftime('%Y-%m-%d %H:%M:%S')
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, time_item)
            
            # 高亮显示密码差异
            self.highlight_password_diff(old_pwd_item, new_pwd_item)
    
    def highlight_password_diff(self, old_item, new_item):
        """
        高亮显示密码差异
        
        Args:
            old_item (QTableWidgetItem): 旧密码单元格
            new_item (QTableWidgetItem): 新密码单元格
        """
        # 获取密码文本
        old_pwd = old_item.text()
        new_pwd = new_item.text()
        
        # 如果密码相同，不需要高亮
        if old_pwd == new_pwd:
            return
        
        # 设置新旧密码的字体
        old_font = QFont()
        old_font.setBold(True)
        old_item.setFont(old_font)
        old_item.setForeground(QColor("#d73a49"))  # 删除的内容用红色
        
        new_font = QFont()
        new_font.setBold(True)
        new_item.setFont(new_font)
        new_item.setForeground(QColor("#28a745"))  # 新增的内容用绿色
    
    def update_page_info(self):
        """更新分页信息"""
        # 计算总页数
        total_pages = (self.total_records + self.page_size - 1) // self.page_size
        if total_pages == 0:
            total_pages = 1
        
        # 更新页码标签
        self.page_info_label.setText(f"第 {self.page} 页 / 共 {total_pages} 页")
        
        # 启用/禁用分页按钮
        self.prev_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < total_pages)
    
    def go_prev_page(self):
        """前往上一页"""
        if self.page > 1:
            self.page -= 1
            self.load_history_data()
    
    def go_next_page(self):
        """前往下一页"""
        # 计算总页数
        total_pages = (self.total_records + self.page_size - 1) // self.page_size
        if self.page < total_pages:
            self.page += 1
            self.load_history_data()
    
    def change_page_size(self, index):
        """
        更改每页显示条数
        
        Args:
            index (int): 下拉框选中项的索引
        """
        # 根据索引设置页大小
        page_sizes = [10, 20, 50, 100]
        if 0 <= index < len(page_sizes):
            self.page_size = page_sizes[index]
            self.page = 1  # 重置为第一页
            self.load_history_data()
    
    def filter_history(self):
        """按时间范围筛选历史记录"""
        self.page = 1  # 重置为第一页
        self.load_history_data()
    
    def reset_filter(self):
        """重置筛选条件"""
        # 重置时间范围
        self.start_date.setDateTime(QDateTime.currentDateTime().addMonths(-1))
        self.end_date.setDateTime(QDateTime.currentDateTime())
        
        # 重新加载数据
        self.page = 1
        self.load_history_data()
    
    def export_history(self):
        """导出历史记录"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            import csv
            import os
            
            # 选择保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出历史记录", "", "CSV文件 (*.csv)"
            )
            
            if not file_path:
                return
                
            # 添加.csv后缀如果没有
            if not file_path.endswith('.csv'):
                file_path += '.csv'
            
            # 获取所有历史记录（不分页）
            start_time = self.start_date.dateTime().toString('yyyy-MM-dd hh:mm:ss')
            end_time = self.end_date.dateTime().toString('yyyy-MM-dd hh:mm:ss')
            
            # 使用一个大的页大小来获取所有符合条件的记录
            result = password_manager.get_password_history(
                self.owner,
                self.row_index,
                page=1,
                page_size=10000,  # 使用一个较大的值
                start_time=start_time,
                end_time=end_time
            )
            
            records = result.get('records', [])
            
            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(HISTORY_COLUMNS)
                
                # 写入数据
                for record in records:
                    # 处理时间格式
                    time_str = record.get('modify_time', '')
                    if isinstance(time_str, datetime):
                        time_str = time_str.strftime('%Y-%m-%d %H:%M:%S')
                    
                    row = [
                        record.get('ip_address', ''),
                        record.get('old_password', ''),
                        record.get('new_password', ''),
                        record.get('modify_user', ''),
                        time_str
                    ]
                    writer.writerow(row)
            
            QMessageBox.information(self, "导出成功", f"历史记录已成功导出到:\n{file_path}")
            
        except Exception as e:
            logger.error(f"导出历史记录失败: {str(e)}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "导出失败", f"导出历史记录失败: {str(e)}") 