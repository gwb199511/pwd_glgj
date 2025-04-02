#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理系统引导模块
提供用户交互式步骤引导功能
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional, Callable

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QCheckBox, QPushButton, QGraphicsDropShadowEffect,
    QSizePolicy, QApplication, QMenu, QAction
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QFont, QIcon, QColor, QPalette, QBrush, QPainter, QPen, QPainterPath

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


class WalkthroughOverlay(QWidget):
    """
    步骤引导浮层
    
    创建透明浮层覆盖在应用程序上，引导用户完成特定操作
    """
    
    finished = pyqtSignal()  # 引导完成信号
    
    def __init__(self, parent=None):
        """
        初始化引导浮层
        
        Args:
            parent: 父窗口，通常是主窗口
        """
        super().__init__(parent)
        
        # 确保浮层覆盖整个父窗口
        if parent:
            self.setGeometry(parent.rect())
            parent.resizeEvent = self._handle_parent_resize
        
        # 设置透明背景
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 遮罩层颜色 - 半透明黑色
        self.mask_color = QColor(0, 0, 0, 160)
        
        # 当前高亮的区域
        self.highlight_rect = QRect()
        
        # 当前步骤
        self.current_step = 0
        self.steps = []
        
        # 提示框位置和内容
        self.tooltip_position = "bottom"  # 可选: top, bottom, left, right
        self.tooltip_widget = None
        
        # 目标控件字典
        self.target_widgets = {}
        
        # 创建按钮控制布局
        self._setup_ui()
        
    def _setup_ui(self):
        """设置用户界面元素"""
        # 创建提示框
        self.tooltip_widget = QWidget(self)
        self.tooltip_widget.setObjectName("walkthrough_tooltip")
        self.tooltip_widget.setStyleSheet("""
            QWidget#walkthrough_tooltip {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #ddd;
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self.tooltip_widget)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.tooltip_widget.setGraphicsEffect(shadow)
        
        # 提示框布局
        tooltip_layout = QVBoxLayout(self.tooltip_widget)
        tooltip_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        self.title_label = ModernLabel("", font_size=12, bold=True)
        tooltip_layout.addWidget(self.title_label)
        
        # 描述
        self.description_label = ModernLabel("")
        self.description_label.setWordWrap(True)
        tooltip_layout.addWidget(self.description_label)
        
        # 步骤指示器
        steps_layout = QHBoxLayout()
        steps_layout.setContentsMargins(0, 10, 0, 0)
        steps_layout.setSpacing(5)
        steps_layout.addStretch()
        self.step_indicators = []
        tooltip_layout.addLayout(steps_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        # 跳过按钮
        self.skip_button = ModernButton("跳过", color=COLORS["secondary"], flat=True)
        self.skip_button.clicked.connect(self._skip_guide)
        button_layout.addWidget(self.skip_button)
        
        button_layout.addStretch()
        
        # 上一步按钮
        self.prev_button = ModernButton("上一步", color=COLORS["secondary"])
        self.prev_button.clicked.connect(self._prev_step)
        button_layout.addWidget(self.prev_button)
        
        # 下一步/完成按钮
        self.next_button = ModernButton("下一步", color=COLORS["primary"])
        self.next_button.clicked.connect(self._next_step)
        button_layout.addWidget(self.next_button)
        
        tooltip_layout.addLayout(button_layout)
        
        # 初始隐藏提示框
        self.tooltip_widget.hide()
        
    def set_steps(self, steps: List[Dict[str, Any]]):
        """
        设置引导步骤
        
        Args:
            steps (List[Dict[str, Any]]): 步骤列表，每个步骤包含：
                - title: 步骤标题
                - description: 步骤描述
                - target: 目标元素选择器或矩形区域 (x, y, width, height)
                - position: 提示框位置 (可选，默认为 "bottom")
        """
        self.steps = steps
        self.current_step = 0
        
        # 创建步骤指示器
        self._create_step_indicators(len(steps))
        
        # 如果有步骤，开始引导
        if steps:
            self.show()
            QTimer.singleShot(100, self._show_current_step)
    
    def _create_step_indicators(self, count: int):
        """
        创建步骤指示器小圆点
        
        Args:
            count (int): 步骤数量
        """
        # 清除现有指示器
        layout = self.tooltip_widget.layout().itemAt(2).layout()
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.step_indicators = []
        
        # 创建新指示器
        for i in range(count):
            indicator = QLabel()
            indicator.setFixedSize(10, 10)
            indicator.setStyleSheet(f"""
                background-color: {COLORS['border']};
                border-radius: 5px;
            """)
            layout.insertWidget(layout.count() - 1, indicator)
            self.step_indicators.append(indicator)
    
    def set_target_widgets(self, widgets: Dict[str, QWidget]):
        """
        设置目标控件字典，用于特殊处理（如显示右键菜单）
        
        Args:
            widgets (Dict[str, QWidget]): 控件字典，键为控件ID，值为控件实例
        """
        self.target_widgets = widgets or {}
    
    def _show_context_menu(self, widget, step):
        """
        显示指定控件的上下文菜单
        
        Args:
            widget (QWidget): 要显示上下文菜单的控件
            step (dict): 当前步骤信息
        """
        if not widget:
            logger.warning("无法显示上下文菜单：未提供控件")
            return
            
        try:
            # 在显示菜单前，先清除高亮区域
            if step.get("highlight_menu", False):
                self.highlight_rect = QRect()
                self.update()  # 强制重绘
                
            # 尝试获取表格控件
            table = None
            if hasattr(widget, "currentItem") and hasattr(widget, "itemAt"):
                # 这是一个QTableWidget
                table = widget
            elif hasattr(widget, "table"):
                # 这可能是一个包含table属性的对象
                table = widget.table
            else:
                logger.warning(f"未找到表格控件，无法显示上下文菜单")
                return
                
            # 确保表格有数据
            if table.rowCount() == 0:
                logger.warning("表格没有数据，无法显示上下文菜单")
                return
                
            # 选择一行（优先选择中间的行）
            row = min(table.rowCount() // 2, table.rowCount() - 1)
            table.selectRow(row)
            
            # 获取指定列的单元格中心点
            column_index = step.get("column_index", 4)  # 默认是密码列(索引4)，可以通过参数指定其他列
            if table.columnCount() > column_index:
                cell_rect = table.visualItemRect(table.item(row, column_index))
                point = cell_rect.center()
            else:
                # 如果没有指定列，则使用第一列
                cell_rect = table.visualItemRect(table.item(row, 0))
                point = cell_rect.center()
            
            # 使用发射自定义上下文菜单信号的方式显示菜单
            self._emit_context_menu_signal(table, point, step)
            
            column_name = "账号列" if column_index == 3 else "密码列" if column_index == 4 else f"列{column_index+1}"
            logger.info(f"已请求通过发射信号显示上下文菜单在{column_name}")
            
        except Exception as e:
            logger.error(f"显示上下文菜单时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def _emit_context_menu_signal(self, widget, point, step):
        """
        发射自定义上下文菜单请求信号
        
        Args:
            widget (QWidget): 控件
            point (QPoint): 本地坐标中的点
            step (dict): 当前步骤信息
        """
        try:
            logger.info("已发射自定义上下文菜单信号")
            
            # 记录列信息
            column_index = step.get("column_index", 4)
            column_name = "账号列" if column_index == 3 else "密码列" if column_index == 4 else f"列{column_index}"
            logger.info(f"已请求通过发射信号显示上下文菜单在{column_name}")
            
            # 停止并销毁之前的菜单观察器
            if hasattr(self, 'menu_watcher') and self.menu_watcher:
                if hasattr(self.menu_watcher, 'timer') and self.menu_watcher.timer.isActive():
                    self.menu_watcher.timer.stop()
                self.menu_watcher.deleteLater()
                self.menu_watcher = None
            
            # 为了捕获菜单显示并设置高亮区域，我们需要拦截菜单
            # 添加全局事件过滤器来监控菜单的出现
            if step.get("highlight_menu", False):
                # 创建菜单观察器
                class MenuWatcher(QObject):
                    def __init__(self, parent, overlay, step):
                        super().__init__(parent)
                        self.overlay = overlay
                        self.step = step
                        self.timer = QTimer(self)
                        self.timer.timeout.connect(self.check_menu)
                        self.timer.start(50)  # 每50毫秒检查一次
                        self.menu_found = False  # 标记是否已找到菜单
                        self.logged_status = False  # 标记是否已输出状态日志
                        
                    def check_menu(self):
                        """检查是否有活动的菜单并高亮显示"""
                        # 查找所有顶级窗口中的QMenu
                        menu_found = False
                        for widget in QApplication.topLevelWidgets():
                            if isinstance(widget, QMenu) and widget.isVisible():
                                menu_found = True
                                # 找到菜单，更新高亮区域
                                self.update_highlight_rect(widget)
                                
                                # 检查并移除指定菜单项
                                if not self.logged_status:
                                    self.remove_unwanted_menu_items(widget)
                                    self.logged_status = True
                                
                                # 已找到菜单
                                if not self.menu_found:
                                    self.menu_found = True
                                return
                        
                        # 如果之前找到过菜单，但现在没有了，可能是菜单已关闭
                        if self.menu_found and not menu_found:
                            self.timer.stop()  # 停止定时器
                
                    def remove_unwanted_menu_items(self, menu):
                        """移除不需要的菜单项"""
                        # 只在账号列上右击时移除"生成16位随机密码"选项
                        column_index = self.step.get("column_index", 4)
                        logger.info(f"当前列索引: {column_index}, 是否应该移除菜单项: {'是' if column_index == 3 else '否'}")
                        
                        if column_index == 3:  # 只在账号列右击时移除
                            for action in menu.actions():
                                # 移除"生成16位随机密码\n并更新到服务器"选项
                                if action.text() and "生成16位随机密码" in action.text() and "更新到服务器" in action.text():
                                    menu.removeAction(action)
                                    logger.info("已从账号列右键菜单中移除'生成16位随机密码 并更新到服务器'选项")
                
                    def update_highlight_rect(self, menu):
                        """更新高亮区域为菜单区域"""
                        # 获取菜单的全局位置和大小
                        menu_rect = menu.rect()
                        menu_global_pos = menu.mapToGlobal(menu_rect.topLeft())
                        parent_pos = self.overlay.parent().mapFromGlobal(menu_global_pos)
                        
                        # 确保菜单在屏幕范围内
                        menu_width = max(menu_rect.width(), 150)
                        menu_height = menu_rect.height()
                        
                        # 计算新的高亮区域
                        padding = 5
                        new_highlight_rect = QRect(
                            parent_pos.x() - padding, 
                            parent_pos.y() - padding,
                            menu_width + padding * 2,
                            menu_height + padding * 2
                        )
                        
                        # 只有当高亮区域发生变化时才更新
                        if not hasattr(self, 'last_highlight_rect') or self.last_highlight_rect != new_highlight_rect:
                            self.last_highlight_rect = new_highlight_rect
                            # 更新高亮区域
                            self.overlay.highlight_rect = new_highlight_rect
                            self.overlay.update()  # 强制重绘
                
                # 创建并安装菜单观察器
                self.menu_watcher = MenuWatcher(self, self, step)
            
            # 发射自定义右键菜单信号
            widget.customContextMenuRequested.emit(point)
        except Exception as e:
            logger.error(f"发射上下文菜单信号时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 退回到直接显示菜单
            self._direct_show_menu(widget, point, step.get("column_index", 4))
    
    def _direct_show_menu(self, widget, point, custom_column_index=None):
        """直接调用表格的_show_context_menu方法显示右键菜单"""
        try:
            # 尝试查找表格管理器
            table_manager = None
            
            # 1. 检查widget是否有table_manager属性
            if hasattr(widget, "property") and callable(widget.property):
                table_manager = widget.property("table_manager")
            
            # 2. 或者检查parent是否有table_manager属性
            if table_manager is None and hasattr(widget, "parent") and callable(widget.parent):
                parent = widget.parent()
                if parent and hasattr(parent, "property") and callable(parent.property):
                    table_manager = parent.property("table_manager")
            
            # 找到table_manager，直接调用其_show_context_menu方法
            if table_manager and hasattr(table_manager, "_show_context_menu"):
                self.debug_log("找到table_manager，直接调用_show_context_menu方法")
                table_manager._show_context_menu(point)
                return
            
            # 尝试查找事件过滤器
            if hasattr(widget, "installEventFilter"):
                for child in widget.children():
                    if hasattr(child, "_show_context_menu") and callable(child._show_context_menu):
                        self.debug_log("找到事件过滤器，调用_show_context_menu方法")
                        child._show_context_menu(point)
                        return
            
            # 如果没有找到合适的方法，创建一个简单的右键菜单
            self.debug_log("未找到_show_context_menu方法，创建临时菜单")
            context_menu = QMenu(widget)
            
            # 根据当前显示的列创建不同的菜单
            if custom_column_index is not None:
                if custom_column_index == 3:  # 账号列
                    self.debug_log("为账号列创建右键菜单")
                    copy_action = context_menu.addAction("复制")
                    context_menu.addSeparator()
                elif custom_column_index == 4:  # 密码列
                    self.debug_log("为密码列创建右键菜单")
                    copy_action = context_menu.addAction("复制")
                    gen_pwd_action = context_menu.addAction("生成随机密码")
                    context_menu.addSeparator()
            
            # 添加通用操作
            add_action = context_menu.addAction("添加行")
            edit_action = context_menu.addAction("编辑行")
            del_action = context_menu.addAction("删除行")
            
            # 显示菜单
            global_pos = widget.mapToGlobal(point)
            context_menu.exec_(global_pos)
            
        except Exception as e:
            self.debug_log(f"显示右键菜单时发生错误: {str(e)}")
    
    def _calculate_highlight_rect(self, step):
        """
        计算高亮区域的矩形
        
        Args:
            step (dict): 当前步骤信息
        """
        # 获取目标区域
        target = step.get("target")
        if isinstance(target, (list, tuple)) and len(target) == 4:
            # 如果是矩形坐标
            self.highlight_rect = QRect(*target)
        elif isinstance(target, QWidget):
            # 如果是控件
            global_pos = target.mapToGlobal(target.rect().topLeft())
            parent_pos = self.parent().mapFromGlobal(global_pos)
            self.highlight_rect = QRect(parent_pos, target.size())
        else:
            # 默认不高亮任何区域
            self.highlight_rect = QRect()
        
        # 设置提示框位置
        self.tooltip_position = step.get("position", "bottom")
        
        # 检查是否需要显示上下文菜单
        if step.get("show_context_menu", False):
            widget_id = step.get("widget_id")
            if widget_id and widget_id in self.target_widgets:
                # 使用延时，确保引导界面已经完全显示
                QTimer.singleShot(300, lambda: self._show_context_menu(self.target_widgets[widget_id], step))
            elif "target_widget" in step:
                # 使用直接保存的控件引用
                QTimer.singleShot(300, lambda: self._show_context_menu(step["target_widget"], step))

    def _show_current_step(self):
        """显示当前步骤"""
        if not self.steps or self.current_step >= len(self.steps):
            self._finish_guide()
            return
        
        step = self.steps[self.current_step]
        
        # 设置标题和描述
        self.title_label.setText(step.get("title", ""))
        self.description_label.setText(step.get("description", ""))
        
        # 更新步骤指示器
        self._update_step_indicators()
        
        # 计算高亮区域
        self._calculate_highlight_rect(step)
        
        # 更新按钮状态
        self._update_buttons()
        
        # 显示提示框
        self._position_tooltip(step)
        self.tooltip_widget.show()
        
        # 更新界面
        self.update()
    
    def _update_step_indicators(self):
        """更新步骤指示器，高亮显示当前步骤"""
        if not self.step_indicators:
            return
        
        for i, indicator in enumerate(self.step_indicators):
            if i == self.current_step:
                # 当前步骤高亮显示
                indicator.setStyleSheet(f"""
                    background-color: {COLORS['primary']};
                    border-radius: 5px;
                """)
            else:
                # 其他步骤使用默认样式
                indicator.setStyleSheet(f"""
                    background-color: {COLORS['border']};
                    border-radius: 5px;
                """)
            
        # 记录日志用于调试
        logger.info(f"更新步骤指示器: 当前步骤 {self.current_step + 1}/{len(self.steps)}")
    
    def _update_buttons(self):
        """更新按钮状态"""
        # 上一步按钮
        self.prev_button.setEnabled(self.current_step > 0)
        
        # 下一步/完成按钮
        if self.current_step == len(self.steps) - 1:
            self.next_button.setText("完成")
        else:
            self.next_button.setText("下一步")
            
    def _position_tooltip(self, step):
        """根据目标区域和设置的位置放置提示框"""
        if not self.highlight_rect.isValid():
            # 如果没有有效的高亮区域，居中显示
            self.tooltip_widget.setGeometry(
                (self.width() - 400) // 2,
                (self.height() - 200) // 2,
                400,
                200
            )
            return
        
        # 提示框默认大小
        tooltip_width = 300
        tooltip_height = self.tooltip_widget.sizeHint().height()
        
        # 根据位置计算提示框坐标
        if self.tooltip_position == "bottom":
            x = self.highlight_rect.x() + (self.highlight_rect.width() - tooltip_width) // 2
            y = self.highlight_rect.bottom() + 10
        elif self.tooltip_position == "top":
            x = self.highlight_rect.x() + (self.highlight_rect.width() - tooltip_width) // 2
            y = self.highlight_rect.top() - tooltip_height - 10
        elif self.tooltip_position == "left":
            # 增加左侧位置的偏移距离
            offset = 20
            x = self.highlight_rect.left() - tooltip_width - offset
            y = self.highlight_rect.y() + (self.highlight_rect.height() - tooltip_height) // 2
        elif self.tooltip_position == "right":
            # 增加右侧位置的偏移距离
            offset = 20
            x = self.highlight_rect.right() + offset
            y = self.highlight_rect.y() + (self.highlight_rect.height() - tooltip_height) // 2
        else:  # 默认底部
            x = self.highlight_rect.x() + (self.highlight_rect.width() - tooltip_width) // 2
            y = self.highlight_rect.bottom() + 10
        
        # 确保提示框在可见区域内
        if x < 10:
            x = 10
        elif x + tooltip_width > self.width() - 10:
            x = self.width() - tooltip_width - 10
            
        if y < 10:
            y = 10
        elif y + tooltip_height > self.height() - 10:
            y = self.height() - tooltip_height - 10
        
        # 设置提示框位置和大小
        self.tooltip_widget.setGeometry(x, y, tooltip_width, tooltip_height)
    
    def _next_step(self):
        """前进到下一步"""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._show_current_step()
        else:
            self._finish_guide()
    
    def _prev_step(self):
        """返回上一步"""
        if self.current_step > 0:
            self.current_step -= 1
            self._show_current_step()
    
    def _skip_guide(self):
        """跳过引导"""
        self._finish_guide()
    
    def _finish_guide(self):
        """完成引导"""
        self.hide()
        self.finished.emit()
    
    def _handle_parent_resize(self, event):
        """处理父窗口大小变化"""
        if hasattr(self.parent(), 'resizeEvent'):
            # 调用原始的resize事件处理器
            self.parent().resizeEvent = self.parent()._original_resize_event
            self.parent().resizeEvent(event)
            # 恢复为我们的处理器
            self.parent()._original_resize_event = self.parent().resizeEvent
            self.parent().resizeEvent = self._handle_parent_resize
        
        # 调整浮层大小以匹配父窗口
        self.setGeometry(self.parent().rect())
        
        # 重新定位提示框
        self._position_tooltip(self.steps[-1] if self.steps else None)
    
    def paintEvent(self, event):
        """绘制事件处理器，绘制半透明遮罩和高亮区域"""
        if not self.isVisible():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取矩形坐标和尺寸
        x, y = 0, 0
        w, h = self.width(), self.height()
        
        # 使用QPainterPath创建一个包含整个窗口的路径
        fullScreenPath = QPainterPath()
        fullScreenPath.addRect(float(x), float(y), float(w), float(h))
        
        # 如果有高亮区域，从全屏路径中减去高亮区域
        if self.highlight_rect.isValid():
            # 获取高亮区域坐标和尺寸
            hx = float(self.highlight_rect.x())
            hy = float(self.highlight_rect.y())
            hw = float(self.highlight_rect.width())
            hh = float(self.highlight_rect.height())
            
            # 创建高亮区域路径
            highlightPath = QPainterPath()
            highlightPath.addRect(hx, hy, hw, hh)
            
            # 从全屏路径中减去高亮区域，得到遮罩区域
            maskPath = fullScreenPath - highlightPath
            
            # 绘制半透明遮罩（只在遮罩区域内）
            painter.fillPath(maskPath, QColor(0, 0, 0, 160))  # 黑色半透明
            
            # 当前步骤
            current_step = self.steps[self.current_step] if self.steps and self.current_step < len(self.steps) else None
            
            # 如果是右键菜单引导步骤，使用特殊样式
            if current_step and current_step.get("highlight_menu", False):
                # 为菜单区域绘制特殊的高亮效果
                # 1. 绘制半透明背景
                menu_bg_color = QColor(COLORS["primary"])
                menu_bg_color.setAlpha(15)  # 很淡的背景
                painter.fillPath(highlightPath, menu_bg_color)
                
                # 2. 绘制发光边框
                painter.setPen(QPen(QColor(COLORS["primary"]), 2))  # 主色调边框
                painter.drawRect(self.highlight_rect)
                
                # 3. 添加外发光效果
                glow_color = QColor(COLORS["primary"])
                glow_color.setAlpha(80)
                for i in range(3):
                    pen_width = 1 + i*2
                    painter.setPen(QPen(glow_color, pen_width))
                    painter.drawRect(
                        self.highlight_rect.adjusted(-pen_width, -pen_width, pen_width, pen_width)
                    )
            else:
                # 普通高亮区域样式
                painter.setPen(QPen(QColor(COLORS["primary"]), 3))  # 加粗边框
                painter.drawRect(self.highlight_rect)
        else:
            # 如果没有高亮区域，整个屏幕都是半透明遮罩
            painter.fillPath(fullScreenPath, QColor(0, 0, 0, 160))  # 黑色半透明

    def debug_log(self, message):
        """
        输出调试日志
        
        Args:
            message (str): 日志消息
        """
        logger.info(f"引导调试: {message}")


# 主界面操作步骤引导信息
MAIN_FEATURES_WALKTHROUGH = [
    {
        "title": "人员列表",
        "description": "点击此处可以切换不同人员的密码记录。系统按人员对密码进行分类管理。",
        "position": "right"
    },
    {
        "title": "密码记录表格",
        "description": "这里展示所有密码记录，点击列标题可以排序，右击指定区域可以显示必要的操作菜单",
        "position": "top"
    },
    {
        "title": "搜索功能",
        "description": "在这里输入关键词可以快速查找密码记录，支持模糊搜索。",
        "position": "bottom"
    },
    {
        "title": "右键操作（除密码列）",
        "description": "在除了密码列以外的列上右击可显示操作菜单，支持复制账号内容以及添加、编辑和删除记录功能。",
        "position": "bottom",
        "show_context_menu": True,  # 标记需要显示右键菜单
        "widget_id": "password_table",  # 指定要在哪个控件上显示右键菜单
        "highlight_menu": True,  # 标记需要高亮显示菜单
        "column_index": 3  # 指定账号列的索引
    },
    {
        "title": "右键菜操作（密码列）",
        "description": "在密码列上右击可显示操作菜单，包括复制密码和生成随机密码等功能。也可进行添加、编辑和删除记录操作。复制、生成随机密码、删除支持多选操作。",
        "position": "bottom",
        "show_context_menu": True,  # 标记需要显示右键菜单
        "widget_id": "password_table",  # 指定要在哪个控件上显示右键菜单
        "highlight_menu": True  # 标记需要高亮显示菜单
    },
    {
        "title": "功能菜单",
        "description": "在菜单栏可以访问更多高级功能，如密码生成器、审计日志查看等。",
        "position": "bottom",
        "widget_id": "menu_bar"  # 指定菜单栏的ID
    }
]


def start_walkthrough(guide_key: str, parent, target_widgets: Dict[str, QWidget] = None) -> bool:
    """
    启动交互式步骤引导
    
    Args:
        guide_key (str): 引导键名
        parent: 父窗口
        target_widgets (Dict[str, QWidget], optional): 目标控件字典，键为控件ID，值为控件实例
        
    Returns:
        bool: 如果启动引导返回True，否则返回False
    """
    if not parent:
        logger.error("启动步骤引导失败: 未提供父窗口")
        return False
    
    # 强制显示引导，不检查完成状态
    force_walkthrough = True
    
    # 仅在调试时才检查完成状态
    if not force_walkthrough:
        # 检查是否需要显示引导
        if user_settings.user_settings.is_guide_completed(guide_key) and not getattr(parent, 'force_walkthrough', False):
            logger.info(f"用户已完成引导: {guide_key}，跳过显示")
            return False
    
    # 选择引导内容
    walkthrough_steps = []
    
    if guide_key == "main_features":
        # 主界面功能引导
        base_steps = MAIN_FEATURES_WALKTHROUGH
        
        # 如果提供了目标控件，使用控件位置
        if target_widgets:
            for i, step in enumerate(base_steps):
                step_copy = step.copy()
                
                # 尝试获取对应控件
                widget_id = step.get("widget_id")
                if widget_id and widget_id in target_widgets:
                    widget = target_widgets[widget_id]
                    # 将控件作为目标
                    step_copy["target"] = widget
                    # 保存widget_id以便后续使用
                    step_copy["widget_id"] = widget_id
                elif i < len(target_widgets.values()):
                    # 如果没有指定widget_id但有足够的控件，按顺序使用
                    widget = list(target_widgets.values())[i]
                    step_copy["target"] = widget
                    # 保存控件引用到额外的键
                    step_copy["target_widget"] = widget
                
                walkthrough_steps.append(step_copy)
        else:
            # 没有目标控件，使用默认步骤
            walkthrough_steps = base_steps
    else:
        logger.warning(f"未找到步骤引导内容: {guide_key}")
        return False
        
    # 创建浮层并设置步骤
    overlay = WalkthroughOverlay(parent)
    
    # 保存原始的resize事件处理器
    if not hasattr(parent, '_original_resize_event'):
        parent._original_resize_event = parent.resizeEvent
    
    # 设置引导完成的回调
    def on_walkthrough_finished():
        # 恢复原始的resize事件处理器
        if hasattr(parent, '_original_resize_event'):
            parent.resizeEvent = parent._original_resize_event
        
        # 标记引导已完成
        user_settings.user_settings.mark_guide_completed(guide_key)
        logger.info(f"用户已完成步骤引导: {guide_key}")
    
    overlay.finished.connect(on_walkthrough_finished)
    
    # 传递控件字典，用于特殊处理（如显示上下文菜单）
    overlay.set_target_widgets(target_widgets)
    overlay.set_steps(walkthrough_steps)
    
    return True 