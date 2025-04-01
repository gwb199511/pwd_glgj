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
    QSizePolicy, QApplication, QMenu
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
            
            # 获取选中单元格的中心点
            cell_rect = table.visualItemRect(table.item(row, 0))
            point = cell_rect.center()
            
            # 为了更可靠地显示菜单，尝试三种方法
            
            # 方法1: 使用QTimer延迟调用更直接的方法显示菜单
            QTimer.singleShot(200, lambda: self._direct_show_menu(table, point))
            
            # 方法2: 使用QTimer，尝试发送鼠标右键事件
            QTimer.singleShot(400, lambda: self._trigger_context_menu(table, point))
            
            # 方法3: 将控件设置为右键点击位置，然后发送自定义上下文菜单信号
            QTimer.singleShot(600, lambda: self._emit_context_menu_signal(table, point))
            
            logger.info(f"已请求显示上下文菜单")
            
        except Exception as e:
            logger.error(f"显示上下文菜单时出错: {str(e)}")
    
    def _direct_show_menu(self, widget, point):
        """
        直接调用显示菜单方法
        
        Args:
            widget (QWidget): 控件
            point (QPoint): 本地坐标中的点
        """
        try:
            # 尝试找到正确的表格管理器对象
            table_manager = None
            
            # 如果widget是QTableWidget，查找其相关的TableEventsMixin
            if hasattr(widget, "property"):
                # 尝试获取table_manager属性
                table_manager = widget.property("table_manager")
            
            # 检查父窗口是否有表格管理器
            if not table_manager and hasattr(self, "parent") and self.parent():
                parent = self.parent()
                if hasattr(parent, "table_manager"):
                    table_manager = parent.table_manager
                    
            # 如果找到了表格管理器，直接调用其显示上下文菜单的方法
            if table_manager and hasattr(table_manager, "_show_context_menu"):
                table_manager._show_context_menu(point)
                logger.info("直接调用表格管理器的_show_context_menu方法")
                return
                
            # 找不到表格管理器，尝试其他方式
            # 尝试找到event_filter
            if hasattr(widget, "event_filter") and widget.event_filter:
                # 尝试直接调用表格的上下文菜单处理方法
                if hasattr(widget.event_filter, "_show_context_menu"):
                    widget.event_filter._show_context_menu(point)
                    logger.info("直接调用event_filter的_show_context_menu方法")
                    return
            
            # 如果以上方法都失败，尝试创建一个简单的右键菜单
            from PyQt5.QtWidgets import QMenu, QAction
            menu = QMenu(widget)
            
            # 添加一些基本操作
            add_action = QAction("添加", widget)
            edit_action = QAction("编辑", widget)
            delete_action = QAction("删除", widget)
            
            menu.addAction(add_action)
            menu.addAction(edit_action)
            menu.addAction(delete_action)
            
            # 显示菜单
            global_pos = widget.viewport().mapToGlobal(point)
            menu.exec_(global_pos)
            logger.info("手动创建并显示上下文菜单")
            
        except Exception as e:
            logger.error(f"直接显示菜单时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _trigger_context_menu(self, widget, point):
        """
        触发控件的上下文菜单
        
        Args:
            widget (QWidget): 要触发上下文菜单的控件
            point (QPoint): 菜单显示位置的本地坐标
        """
        try:
            # 使用模拟右键点击的方式触发菜单
            from PyQt5.QtGui import QMouseEvent
            from PyQt5.QtCore import QEvent, QPoint
            
            # 创建鼠标右键按下事件
            press_event = QMouseEvent(
                QEvent.MouseButtonPress,
                point,
                Qt.RightButton,
                Qt.RightButton,
                Qt.NoModifier
            )
            
            # 创建鼠标右键释放事件
            release_event = QMouseEvent(
                QEvent.MouseButtonRelease,
                point,
                Qt.RightButton,
                Qt.RightButton,
                Qt.NoModifier
            )
            
            # 将事件发送到表格视口
            viewport = widget.viewport()
            QApplication.sendEvent(viewport, press_event)
            QApplication.sendEvent(viewport, release_event)
            
            logger.info(f"已触发鼠标右键事件")
        except Exception as e:
            logger.error(f"触发鼠标右键事件时出错: {str(e)}")
    
    def _emit_context_menu_signal(self, widget, point):
        """
        发射自定义上下文菜单信号
        
        Args:
            widget (QWidget): 控件
            point (QPoint): 本地坐标中的点
        """
        try:
            # 如果控件有customContextMenuRequested信号，直接发射
            if hasattr(widget, "customContextMenuRequested"):
                widget.customContextMenuRequested.emit(point)
                logger.info("已发射自定义上下文菜单信号")
        except Exception as e:
            logger.error(f"发射上下文菜单信号时出错: {str(e)}")
    
    def _show_current_step(self):
        """显示当前步骤"""
        if not self.steps or self.current_step >= len(self.steps):
            self._finish_guide()
            return
        
        step = self.steps[self.current_step]
        
        # 设置标题和描述
        self.title_label.setText(step.get("title", ""))
        self.description_label.setText(step.get("description", ""))
        
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
        
        # 更新步骤指示器
        self._update_step_indicators()
        
        # 更新按钮状态
        self._update_buttons()
        
        # 放置提示框
        self._position_tooltip()
        
        # 显示提示框
        self.tooltip_widget.show()
        
        # 检查是否需要显示上下文菜单
        if step.get("show_context_menu", False):
            widget_id = step.get("widget_id")
            if widget_id and widget_id in self.target_widgets:
                # 使用延时，确保引导界面已经完全显示
                QTimer.singleShot(300, lambda: self._show_context_menu(self.target_widgets[widget_id], step))
            elif "target_widget" in step:
                # 使用直接保存的控件引用
                QTimer.singleShot(300, lambda: self._show_context_menu(step["target_widget"], step))
        
        # 强制重绘
        self.update()
    
    def _update_step_indicators(self):
        """更新步骤指示器状态"""
        for i, indicator in enumerate(self.step_indicators):
            if i == self.current_step:
                indicator.setStyleSheet(f"""
                    background-color: {COLORS['primary']};
                    border-radius: 5px;
                """)
            else:
                indicator.setStyleSheet(f"""
                    background-color: {COLORS['border']};
                    border-radius: 5px;
                """)
    
    def _update_buttons(self):
        """更新按钮状态"""
        # 上一步按钮
        self.prev_button.setEnabled(self.current_step > 0)
        
        # 下一步/完成按钮
        if self.current_step == len(self.steps) - 1:
            self.next_button.setText("完成")
        else:
            self.next_button.setText("下一步")
    
    def _position_tooltip(self):
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
            x = self.highlight_rect.left() - tooltip_width - 10
            y = self.highlight_rect.y() + (self.highlight_rect.height() - tooltip_height) // 2
        elif self.tooltip_position == "right":
            x = self.highlight_rect.right() + 10
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
        self._position_tooltip()
    
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
            
            # 绘制高亮区域边框
            painter.setPen(QPen(QColor(COLORS["primary"]), 3))  # 加粗边框
            painter.drawRect(self.highlight_rect)
        else:
            # 如果没有高亮区域，整个屏幕都是半透明遮罩
            painter.fillPath(fullScreenPath, QColor(0, 0, 0, 160))  # 黑色半透明


# 主界面操作步骤引导信息
MAIN_FEATURES_WALKTHROUGH = [
    {
        "title": "人员列表",
        "description": "点击此处可以切换不同人员的密码记录。系统按人员对密码进行分类管理。",
        "position": "right"
    },
    {
        "title": "密码记录表格",
        "description": "这里展示所有密码记录，点击列标题可以排序，双击行可以编辑记录。",
        "position": "top"
    },
    {
        "title": "搜索功能",
        "description": "在这里输入关键词可以快速查找密码记录，支持模糊搜索。",
        "position": "bottom"
    },
    {
        "title": "右键菜单操作",
        "description": "在表格中右击某条记录可显示操作菜单，包括添加、编辑和删除记录功能。右击密码列可生成随机密码或更新到服务器。",
        "position": "left",
        "show_context_menu": True,  # 标记需要显示右键菜单
        "widget_id": "password_table"  # 指定要在哪个控件上显示右键菜单
    },
    {
        "title": "功能菜单",
        "description": "在菜单栏可以访问更多高级功能，如密码导出、审计日志查看等。",
        "position": "bottom"
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