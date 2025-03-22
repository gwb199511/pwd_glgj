#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
审计日志查看器模块，提供日志查看和分析功能
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # 导入PyQt5模块
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
        QLabel, QComboBox, QLineEdit, QPushButton, QTabWidget,
        QTextEdit, QFrame, QDateTimeEdit, QCheckBox, QGroupBox,
        QFileDialog, QMessageBox, QDialog, QFormLayout
    )
    from PyQt5.QtCore import Qt, QDateTime, pyqtSignal
    from PyQt5.QtGui import QFont, QColor, QIcon
    
    # 导入项目模块
    from config import FONT_FAMILY, COLORS
    from audit_log import (
        audit_logger, LOG_TYPE_SYSTEM, LOG_TYPE_SSH, LOG_TYPE_ALL,
        OP_TYPE_LOGIN, OP_TYPE_LOGOUT, OP_TYPE_QUERY, OP_TYPE_ADD,
        OP_TYPE_UPDATE, OP_TYPE_DELETE, OP_TYPE_GENERATE, OP_TYPE_SSH_UPDATE,
        OP_TYPE_EXPORT, OP_TYPE_IMPORT, 
        OP_RESULT_SUCCESS, OP_RESULT_FAIL, OP_RESULT_WARNING, OP_RESULT_INFO
    )
    from ui_components import ModernLabel, ModernButton, ModernLineEdit, HorizontalLine, show_message
    
    logger.info("所有模块导入成功")
except Exception as e:
    logger.error(f"导入模块时出错: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    raise

class AuditLogViewer(QMainWindow):
    """
    审计日志查看器窗口
    
    提供查看和分析系统操作日志、SSH更新日志等功能
    """
    
    def __init__(self, parent=None):
        """
        初始化审计日志查看器窗口
        
        Args:
            parent (QWidget, optional): 父窗口. 默认为 None.
        """
        try:
            super().__init__(parent)
            self.setWindowTitle("日志审计")
            self.resize(1000, 600)
            
            # 初始化状态
            self.current_log_type = LOG_TYPE_SYSTEM
            self.current_logs = []
            self.current_page = 1
            self.page_size = 50
            
            # 创建界面
            self.init_ui()
            
            # 加载初始数据
            self.load_logs()
            
            logger.info("AuditLogViewer初始化成功")
        except Exception as e:
            logger.error(f"AuditLogViewer初始化失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def init_ui(self):
        """初始化界面"""
        try:
            # 创建中央部件
            central_widget = QWidget(self)
            self.setCentralWidget(central_widget)
            
            # 创建主布局
            main_layout = QVBoxLayout(central_widget)
            
            # 创建筛选控件
            filter_widget = self.create_filter_widget()
            main_layout.addWidget(filter_widget)
            
            # 创建分割器
            splitter = QSplitter(Qt.Horizontal)
            
            # 创建日志表格
            self.log_table = self.create_log_table()
            splitter.addWidget(self.log_table)
            
            # 创建右侧面板
            right_panel = QTabWidget()
            right_panel.setFont(QFont(FONT_FAMILY, 9))
            
            # 创建详情面板
            detail_widget = self.create_detail_widget()
            right_panel.addTab(detail_widget, "详情")
            
            # 创建统计面板
            stats_widget = self.create_stats_widget()
            right_panel.addTab(stats_widget, "统计")
            
            splitter.addWidget(right_panel)
            
            # 设置分割器比例
            splitter.setSizes([600, 400])
            
            # 添加分割器到主布局
            main_layout.addWidget(splitter, 1)
            
            # 创建状态栏
            self.statusBar().showMessage("准备就绪")
            
            # 连接信号
            self.log_table.itemSelectionChanged.connect(self.update_detail_view)
            
            logger.info("界面初始化完成")
        except Exception as e:
            logger.error(f"界面初始化失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def create_filter_widget(self) -> QWidget:
        """创建筛选控件"""
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 10)
        
        # 标题
        title = ModernLabel("日志审计", font_size=12, bold=True)
        title.setAlignment(Qt.AlignCenter)
        filter_layout.addWidget(title)
        
        # 水平分割线
        filter_layout.addWidget(HorizontalLine())
        
        # 筛选条件组
        filter_group = QWidget()
        filter_group_layout = QHBoxLayout(filter_group)
        filter_group_layout.setContentsMargins(0, 5, 0, 5)
        
        # 日志类型
        log_type_layout = QVBoxLayout()
        log_type_label = QLabel("日志类型")
        log_type_label.setFont(QFont(FONT_FAMILY, 9))
        self.log_type_combo = QComboBox()
        self.log_type_combo.setFont(QFont(FONT_FAMILY, 9))
        self.log_type_combo.addItem("系统操作日志", LOG_TYPE_SYSTEM)
        self.log_type_combo.addItem("SSH更新日志", LOG_TYPE_SSH)
        self.log_type_combo.addItem("全部日志", LOG_TYPE_ALL)
        self.log_type_combo.currentIndexChanged.connect(self.on_log_type_changed)
        log_type_layout.addWidget(log_type_label)
        log_type_layout.addWidget(self.log_type_combo)
        filter_group_layout.addLayout(log_type_layout)
        
        # 时间范围
        time_range_layout = QVBoxLayout()
        time_range_label = QLabel("时间范围")
        time_range_label.setFont(QFont(FONT_FAMILY, 9))
        
        # 创建时间范围选择组合框和刷新按钮的水平布局
        time_range_group = QWidget()
        time_range_group_layout = QHBoxLayout(time_range_group)
        time_range_group_layout.setContentsMargins(0, 0, 0, 0)
        time_range_group_layout.setSpacing(5)
        
        self.time_range_combo = QComboBox()
        self.time_range_combo.setFont(QFont(FONT_FAMILY, 9))
        
        # 添加时间范围选项
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        
        # 手动设置时间范围选项
        time_ranges = [
            {"name": "当前", "start_time": now - timedelta(minutes=1), "end_time": now},
            {"name": "今天", "start_time": today_start, "end_time": now},
            {"name": "昨天", "start_time": today_start - timedelta(days=1), "end_time": today_start - timedelta(seconds=1)},
            {"name": "本周", "start_time": today_start - timedelta(days=now.weekday()), "end_time": now},
            {"name": "上周", "start_time": today_start - timedelta(days=now.weekday() + 7), "end_time": today_start - timedelta(days=now.weekday() + 1) - timedelta(seconds=1)},
            {"name": "最近7天", "start_time": now - timedelta(days=7), "end_time": now},
            {"name": "全部", "start_time": None, "end_time": None}
        ]
        
        for option in time_ranges:
            self.time_range_combo.addItem(option["name"], option)
        
        self.time_range_combo.currentIndexChanged.connect(self.on_time_range_changed)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新")
        refresh_button.setFont(QFont(FONT_FAMILY, 9))
        refresh_button.setMaximumWidth(50)
        refresh_button.clicked.connect(self.refresh_time_range)
        
        time_range_group_layout.addWidget(self.time_range_combo)
        time_range_group_layout.addWidget(refresh_button)
        
        time_range_layout.addWidget(time_range_label)
        time_range_layout.addWidget(time_range_group)
        filter_group_layout.addLayout(time_range_layout)
        
        # 自定义时间范围
        custom_time_layout = QVBoxLayout()
        custom_time_label = QLabel("自定义时间")
        custom_time_label.setFont(QFont(FONT_FAMILY, 9))
        custom_time_group = QWidget()
        custom_time_group_layout = QHBoxLayout(custom_time_group)
        custom_time_group_layout.setContentsMargins(0, 0, 0, 0)
        custom_time_group_layout.setSpacing(5)
        
        # 开始时间
        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setFont(QFont(FONT_FAMILY, 9))
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 设置显示格式，包含时分秒
        # 设置最小宽度确保时间显示完整
        self.start_time_edit.setMinimumWidth(160)
        
        # 结束时间
        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setFont(QFont(FONT_FAMILY, 9))
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDateTime(QDateTime.currentDateTime())
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 设置显示格式，包含时分秒
        # 设置最小宽度确保时间显示完整
        self.end_time_edit.setMinimumWidth(160)
        
        # 调整布局间距，确保时间显示不被遮挡
        custom_time_group_layout.addWidget(self.start_time_edit)
        custom_time_group_layout.addWidget(QLabel("-"))  # 增加间隔符两侧的空格
        custom_time_group_layout.addWidget(self.end_time_edit)
        
        custom_time_layout.addWidget(custom_time_label)
        custom_time_layout.addWidget(custom_time_group)
        filter_group_layout.addLayout(custom_time_layout)
        
        # 操作类型
        op_type_layout = QVBoxLayout()
        op_type_label = QLabel("操作类型")
        op_type_label.setFont(QFont(FONT_FAMILY, 9))
        self.op_type_combo = QComboBox()
        self.op_type_combo.setFont(QFont(FONT_FAMILY, 9))
        self.op_type_combo.addItem("全部", None)
        self.op_type_combo.addItem("登录", OP_TYPE_LOGIN)
        self.op_type_combo.addItem("登出", OP_TYPE_LOGOUT)
        self.op_type_combo.addItem("查询", OP_TYPE_QUERY)
        self.op_type_combo.addItem("添加", OP_TYPE_ADD)
        self.op_type_combo.addItem("更新", OP_TYPE_UPDATE)
        self.op_type_combo.addItem("删除", OP_TYPE_DELETE)
        self.op_type_combo.addItem("生成", OP_TYPE_GENERATE)
        self.op_type_combo.addItem("SSH更新", OP_TYPE_SSH_UPDATE)
        self.op_type_combo.addItem("导出", OP_TYPE_EXPORT)
        self.op_type_combo.addItem("导入", OP_TYPE_IMPORT)
        self.op_type_combo.currentIndexChanged.connect(self.load_logs)
        op_type_layout.addWidget(op_type_label)
        op_type_layout.addWidget(self.op_type_combo)
        filter_group_layout.addLayout(op_type_layout)
        
        # 关键词搜索
        keyword_layout = QVBoxLayout()
        keyword_label = QLabel("关键词搜索")
        keyword_label.setFont(QFont(FONT_FAMILY, 9))
        self.keyword_edit = ModernLineEdit(placeholder="搜索...")
        # 设置关键词搜索框的最大宽度
        self.keyword_edit.setMaximumWidth(150)
        # 添加回车键触发搜索功能
        self.keyword_edit.returnPressed.connect(self.load_logs)
        keyword_layout.addWidget(keyword_label)
        keyword_layout.addWidget(self.keyword_edit)
        filter_group_layout.addLayout(keyword_layout)
        
        # 导出按钮
        export_layout = QVBoxLayout()
        export_layout.addStretch()
        export_button = ModernButton("导出", color=COLORS["secondary"])
        export_button.clicked.connect(self.export_logs)
        export_layout.addWidget(export_button)
        filter_group_layout.addLayout(export_layout)
        
        filter_layout.addWidget(filter_group)
        
        return filter_widget
        
    def create_log_table(self) -> QTableWidget:
        """创建日志表格"""
        table = QTableWidget()
        table.setFont(QFont(FONT_FAMILY, 9))
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
        # 设置列
        table.setColumnCount(6)
        headers = ["时间", "用户", "操作", "结果", "目标", "详情"]
        table.setHorizontalHeaderLabels(headers)
        
        # 设置各列宽度
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # 默认可调整
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 时间列自适应内容
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 用户列自适应内容
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 操作列自适应内容
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 结果列自适应内容
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # 详情列占用剩余空间
        
        return table
        
    def create_detail_widget(self) -> QWidget:
        """创建详情控件"""
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = ModernLabel("日志详情", font_size=10, bold=True)
        title.setAlignment(Qt.AlignCenter)
        detail_layout.addWidget(title)
        
        # 详情文本框
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont(FONT_FAMILY, 9))
        self.detail_text.setPlainText("请选择一条日志记录以查看详情")
        
        detail_layout.addWidget(self.detail_text)
        
        return detail_widget
        
    def create_stats_widget(self) -> QWidget:
        """创建统计控件"""
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = ModernLabel("统计分析", font_size=10, bold=True)
        title.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(title)
        
        # 统计表格
        self.stats_table = QTableWidget()
        self.stats_table.setFont(QFont(FONT_FAMILY, 9))
        self.stats_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.stats_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.stats_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.stats_table.setAlternatingRowColors(True)
        
        # 设置列
        self.stats_table.setColumnCount(2)
        headers = ["统计项", "值"]
        self.stats_table.setHorizontalHeaderLabels(headers)
        
        # 自动调整列宽
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        stats_layout.addWidget(self.stats_table)
        
        return stats_widget
    
    def on_log_type_changed(self, index: int):
        """
        日志类型变化处理
        
        Args:
            index (int): 选中的索引
        """
        log_type = self.log_type_combo.itemData(index)
        if log_type != self.current_log_type:
            self.current_log_type = log_type
            self.load_logs()
    
    def on_time_range_changed(self, index: int):
        """
        时间范围变化处理
        
        Args:
            index (int): 选中的索引
        """
        # 获取选中的时间范围选项名称
        option_name = self.time_range_combo.itemText(index)
        option = self.time_range_combo.itemData(index)
        
        # 更新自定义时间控件
        if option["start_time"] is not None:
            self.start_time_edit.setDateTime(QDateTime.fromString(option["start_time"].isoformat(), Qt.ISODate))
        if option["end_time"] is not None:
            self.end_time_edit.setDateTime(QDateTime.fromString(option["end_time"].isoformat(), Qt.ISODate))
            
        # 加载日志
        self.load_logs()
    
    def refresh_time_range(self):
        """刷新当前选择的时间范围"""
        # 获取当前选择的索引
        current_index = self.time_range_combo.currentIndex()
        # 获取当前选择的选项名称
        option_name = self.time_range_combo.itemText(current_index)
        option = self.time_range_combo.itemData(current_index)
        
        # 根据不同的选项更新时间
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        
        if option_name == "当前":
            option["start_time"] = now - timedelta(minutes=1)
            option["end_time"] = now
        elif option_name == "今天":
            option["start_time"] = today_start
            option["end_time"] = now
        elif option_name == "本周":
            option["start_time"] = today_start - timedelta(days=now.weekday())
            option["end_time"] = now
        elif option_name == "最近7天":
            option["start_time"] = now - timedelta(days=7)
            option["end_time"] = now
        
        # 更新自定义时间控件
        if option["start_time"] is not None:
            self.start_time_edit.setDateTime(QDateTime.fromString(option["start_time"].isoformat(), Qt.ISODate))
        if option["end_time"] is not None:
            self.end_time_edit.setDateTime(QDateTime.fromString(option["end_time"].isoformat(), Qt.ISODate))
            
        # 加载日志
        self.load_logs()
        
        # 显示刷新消息
        self.statusBar().showMessage(f"已刷新时间范围为：{option_name}")
    
    def load_logs(self):
        """加载日志记录"""
        try:
            # 显示加载状态
            self.statusBar().showMessage("正在加载日志...")
            
            # 获取时间范围
            start_time = self.start_time_edit.dateTime().toPyDateTime()
            end_time = self.end_time_edit.dateTime().toPyDateTime()
            
            # 获取当前选中的操作类型
            op_type_index = self.op_type_combo.currentIndex()
            operation_type = self.op_type_combo.itemData(op_type_index)
            operation_types = [operation_type] if operation_type else None
            
            # 获取关键词
            keyword = self.keyword_edit.text().strip() if self.keyword_edit.text().strip() else None
            
            # 获取基本日志数据，应用过滤条件
            try:
                # 调用审计日志API获取日志
                self.current_logs = audit_logger.get_logs(
                    log_type=self.current_log_type,
                    start_time=start_time,
                    end_time=end_time,
                    operation_types=operation_types,
                    keyword=keyword,
                    limit=1000  # 增加显示条数
                )
            except Exception as e:
                logger.error(f"调用audit_logger.get_logs时出错: {str(e)}")
                # 创建空日志列表，避免崩溃
                self.current_logs = []
            
            # 更新表格，捕获可能的异常
            try:
                self.update_log_table()
            except Exception as e:
                logger.error(f"更新日志表格时出错: {str(e)}")
            
            # 更新统计，捕获可能的异常
            try:
                self.update_stats()
            except Exception as e:
                logger.error(f"更新统计数据时出错: {str(e)}")
            
            # 显示结果状态
            self.statusBar().showMessage(f"共找到 {len(self.current_logs)} 条日志记录 (时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {end_time.strftime('%Y-%m-%d %H:%M:%S')})")
            
        except Exception as e:
            logger.error(f"加载日志时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.statusBar().showMessage(f"加载日志失败: {str(e)}")
            # 确保current_logs不为None
            self.current_logs = []
    
    def update_log_table(self):
        """更新日志表格"""
        try:
            # 清空表格
            self.log_table.setRowCount(0)
            
            # 没有日志时直接返回
            if not self.current_logs:
                return
                
            # 显示加载状态
            self.statusBar().showMessage("正在更新表格...")
            
            # 设置行数
            self.log_table.setRowCount(len(self.current_logs))
            
            # 填充表格
            for row, log in enumerate(self.current_logs):
                try:
                    # 时间
                    timestamp_item = QTableWidgetItem(log.get("timestamp", "")[:19].replace("T", " "))
                    self.log_table.setItem(row, 0, timestamp_item)
                    
                    # 用户
                    user_item = QTableWidgetItem(log.get("user", ""))
                    self.log_table.setItem(row, 1, user_item)
                    
                    # 操作
                    operation_item = QTableWidgetItem(log.get("operation", ""))
                    self.log_table.setItem(row, 2, operation_item)
                    
                    # 结果
                    result_item = QTableWidgetItem(log.get("result", ""))
                    self.log_table.setItem(row, 3, result_item)
                    
                    # 设置结果颜色
                    if log.get("result") == OP_RESULT_SUCCESS:
                        result_item.setForeground(QColor(COLORS["success"]))
                    elif log.get("result") == OP_RESULT_FAIL:
                        result_item.setForeground(QColor(COLORS["danger"]))
                    elif log.get("result") == OP_RESULT_WARNING:
                        result_item.setForeground(QColor(COLORS["warning"]))
                    
                    # 目标
                    target_item = QTableWidgetItem(log.get("target", ""))
                    self.log_table.setItem(row, 4, target_item)
                    
                    # 详情
                    details_item = QTableWidgetItem(log.get("details", "")[:50] + "..." if len(log.get("details", "")) > 50 else log.get("details", ""))
                    self.log_table.setItem(row, 5, details_item)
                except Exception as e:
                    logger.error(f"处理第{row}行日志时出错: {str(e)}")
                    continue
            
            # 自动调整列宽以适应内容
            self.log_table.resizeColumnsToContents()
            
            # 显示状态
            self.statusBar().showMessage(f"共显示 {len(self.current_logs)} 条日志记录")
            
        except Exception as e:
            logger.error(f"更新日志表格时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.statusBar().showMessage("更新表格失败")
    
    def update_detail_view(self):
        """更新详情视图"""
        try:
            # 获取选中行
            selected_rows = self.log_table.selectedItems()
            if not selected_rows:
                self.detail_text.setPlainText("请选择一条日志记录以查看详情")
                return
                
            row = selected_rows[0].row()
            if row < 0 or row >= len(self.current_logs):
                self.detail_text.setPlainText("无效的选择")
                return
                
            # 获取选中的日志记录
            log = self.current_logs[row]
            
            # 格式化详情
            details = f"时间: {log.get('timestamp', '').replace('T', ' ')}\n"
            details += f"用户: {log.get('user', '')}\n"
            details += f"操作: {log.get('operation', '')}\n"
            details += f"结果: {log.get('result', '')}\n"
            details += f"目标: {log.get('target', '')}\n"
            details += f"详情: {log.get('details', '')}\n"
            
            # 显示详情
            self.detail_text.setPlainText(details)
            
        except Exception as e:
            logger.error(f"更新详情视图时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.detail_text.setPlainText(f"加载详情时出错: {str(e)}")
    
    def update_stats(self):
        """更新统计信息"""
        try:
            # 简化统计，仅显示基本信息
            if not self.current_logs:
                # 无日志时显示空统计
                self.stats_table.setRowCount(0)
                return
            
            # 计算基本统计: 总数、成功数、失败数
            total_count = len(self.current_logs)
            success_count = sum(1 for log in self.current_logs if log.get("result") == OP_RESULT_SUCCESS)
            fail_count = sum(1 for log in self.current_logs if log.get("result") == OP_RESULT_FAIL)
            
            # 更新统计表格
            self.stats_table.setRowCount(3)
            
            # 总数
            self.stats_table.setItem(0, 0, QTableWidgetItem("总记录数"))
            self.stats_table.setItem(0, 1, QTableWidgetItem(str(total_count)))
            
            # 成功数
            self.stats_table.setItem(1, 0, QTableWidgetItem("成功操作"))
            self.stats_table.setItem(1, 1, QTableWidgetItem(str(success_count)))
            self.stats_table.item(1, 1).setForeground(QColor(COLORS["success"]))
            
            # 失败数
            self.stats_table.setItem(2, 0, QTableWidgetItem("失败操作"))
            self.stats_table.setItem(2, 1, QTableWidgetItem(str(fail_count)))
            self.stats_table.item(2, 1).setForeground(QColor(COLORS["danger"]))
            
        except Exception as e:
            logger.error(f"更新统计信息时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def export_logs(self):
        """导出日志记录"""
        try:
            # 检查是否有日志可导出
            if not self.current_logs:
                show_message(self, "导出失败", "没有可导出的日志记录", QMessageBox.Warning)
                return
            
            # 选择保存路径和格式
            options = QFileDialog.Options()
            file_path, file_type = QFileDialog.getSaveFileName(
                self, "导出日志", "", 
                "CSV文件 (*.csv);;JSON文件 (*.json)", 
                options=options
            )
            
            if not file_path:
                return
                
            # 确定导出格式
            export_format = "csv"
            if file_path.lower().endswith(".json"):
                export_format = "json"
            elif not file_path.lower().endswith(".csv"):
                file_path += ".csv"
                
            # 执行导出
            success = audit_logger.export_logs(self.current_logs, file_path, export_format)
            
            if success:
                self.statusBar().showMessage(f"导出成功: {file_path}")
                show_message(self, "导出成功", f"日志已导出到: {file_path}")
            else:
                show_message(self, "导出失败", "导出日志时出错，请检查文件路径和权限", QMessageBox.Warning)
                
        except Exception as e:
            logger.error(f"导出日志时出错: {str(e)}")
            show_message(self, "导出失败", f"导出日志时出错: {str(e)}", QMessageBox.Critical)
    
    def run(self):
        """运行日志审计查看器"""
        self.show()


def main():
    """
    主函数，用于单独运行审计日志查看器
    """
    try:
        # 单独执行时的包含异常处理的入口
        import sys
        from PyQt5.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        viewer = AuditLogViewer()
        viewer.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"启动日志审计查看器时出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 