#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自定义表格委托模块
实现表格中特殊单元格的自定义渲染
"""

import logging
from PyQt5.QtWidgets import (
    QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle, QToolTip,
    QWidget, QTextBrowser, QVBoxLayout, QFrame, QMenu, QAction
)
from PyQt5.QtCore import Qt, QModelIndex, QSize, QPoint, QTimer, QEvent, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QBrush, QPainter, QPen, QFont, QTextDocument, QCursor
from PyQt5.QtWidgets import QGraphicsOpacityEffect

from config import REQUIRED_FIELDS, PASSWORD_COLUMNS

# 配置日志
logger = logging.getLogger(__name__)


class RequiredFieldDelegate(QStyledItemDelegate):
    """
    必填字段委托类
    
    通过重写绘制方法，为必填字段提供醒目的黄色背景显示
    仅在编辑模式下显示高亮背景
    """
    
    def __init__(self, parent=None):
        """
        初始化委托
        
        Args:
            parent: 父对象
        """
        super(RequiredFieldDelegate, self).__init__(parent)
        # 使用与编辑行相同的蓝色作为必填字段背景色
        self.required_bg_color = QColor("#008C8C")  # 蓝色背景
        self.required_text_color = QColor(255, 0, 0)   # 红色警示文本颜色
        self.empty_text_format = "*必填: {}"
        
        # 跟踪编辑模式状态，默认为非编辑模式
        self.editing_mode = False
        # 当前正在编辑的行，-1表示没有正在编辑的行
        self.editing_row = -1
        
    def set_editing_mode(self, is_editing, row=-1):
        """
        设置编辑模式状态
        
        Args:
            is_editing (bool): 是否处于编辑模式
            row (int): 正在编辑的行索引，默认为-1表示没有正在编辑的行
        """
        self.editing_mode = is_editing
        self.editing_row = row
        # 通知视图更新，刷新显示
        if self.parent():
            self.parent().viewport().update()
        
    def paint(self, painter, option, index):
        """
        绘制单元格
        
        Args:
            painter: QPainter对象
            option: 单元格样式选项
            index: 单元格索引
        """
        # 保存绘制器状态
        painter.save()
        
        # 获取单元格的行和列
        row = index.row()
        column = index.column()
        
        # 判断是否是必填字段
        is_required = column in REQUIRED_FIELDS
        
        # 判断是否需要高亮显示（仅在编辑模式且是当前编辑行或未指定编辑行时高亮）
        is_editing_row = self.editing_mode and (self.editing_row == -1 or self.editing_row == row)
        
        if is_editing_row:
            # 为编辑行的所有单元格设置蓝色背景
            painter.fillRect(option.rect, self.required_bg_color)
            
            # 设置文本选项
            text_option = QStyleOptionViewItem(option)
            text_option.state &= ~QStyle.State_Selected
            
            # 获取单元格文本内容
            text = index.data(Qt.DisplayRole)
            
            if is_required and (not text or text.startswith("*必填:")):
                # 获取字段名称
                field_name = PASSWORD_COLUMNS[column] if column < len(PASSWORD_COLUMNS) else ""
                display_text = self.empty_text_format.format(field_name)
                
                # 设置红色文本
                painter.setPen(QPen(self.required_text_color))
                
                # 设置加粗字体
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                
                # 绘制文本
                text_rect = option.rect.adjusted(4, 0, -4, 0)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)
                
            elif is_required and text:
                # 必填字段有内容时，使用红色文本
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                
                painter.setPen(QPen(self.required_text_color))
                text_rect = option.rect.adjusted(4, 0, -4, 0)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
                
            else:
                # 非必填字段，使用白色文本
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                
                painter.setPen(QPen(Qt.white))
                text_rect = option.rect.adjusted(4, 0, -4, 0)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text if text else "")
                
            # 如果是选中状态，绘制半透明的选中框
            if option.state & QStyle.State_Selected:
                selection_color = QColor(100, 150, 230, 50)  # 半透明蓝色
                painter.fillRect(option.rect, selection_color)
        else:
            # 非编辑模式，使用默认渲染
            QStyledItemDelegate.paint(self, painter, option, index)
        
        # 恢复绘制器状态
        painter.restore()


class SelectableTooltip(QWidget):
    """
    可选择文本的自定义工具提示
    
    创建一个可以选择和复制文本的浮动窗口，作为高级工具提示使用
    """
    
    def __init__(self, parent=None):
        """
        初始化可选择工具提示
        
        Args:
            parent: 父对象
        """
        super(SelectableTooltip, self).__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        
        # 设置无边框并避免任务栏显示
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        # 设置半透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 不在任务栏显示
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        
        # 创建文本浏览器，支持选择文本
        self.text_browser = QTextBrowser(self)
        self.text_browser.setFrameShape(QFrame.NoFrame)  # 无边框
        self.text_browser.setOpenExternalLinks(False)   # 不打开外部链接
        self.text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 需要时显示滚动条
        self.text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 设置最大尺寸限制，与项目UI保持一致
        # 最大宽度为屏幕宽度的1/3，最大高度为屏幕高度的1/2
        screen_size = QApplication.desktop().availableGeometry().size()
        max_width = min(500, screen_size.width() // 3)  # 最大宽度500px或屏幕宽度的1/3
        max_height = min(400, screen_size.height() // 2)  # 最大高度400px或屏幕高度的1/2
        
        self.text_browser.setMaximumSize(max_width, max_height)
        
        # 设置样式 - 使用与项目一致的样式
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #f5f5f5; 
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                padding: 5px;
                font-family: "Microsoft YaHei", "SimSun", sans-serif;
                font-size: 9pt;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f0f0f0;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # 添加到布局
        layout.addWidget(self.text_browser)
        
        # 初始化隐藏定时器（当鼠标离开后延迟隐藏）
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._start_fade_out)
        
        # 是否选择中标志
        self.is_selecting = False
        # 是否显示菜单标志
        self.is_menu_visible = False
        # 是否正在淡出
        self.is_fading_out = False
        
        # 添加右键菜单
        self.text_browser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_browser.customContextMenuRequested.connect(self._show_context_menu)
        
        # 安装事件过滤器监控鼠标事件
        self.text_browser.viewport().installEventFilter(self)
        self.installEventFilter(self)  # 给窗口本身也添加事件过滤器
        
        # 应用全局事件过滤器来捕获鼠标事件
        QApplication.instance().installEventFilter(self)
        
        # 创建不透明度效果和淡出动画
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)  # 初始完全不透明
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(250)  # 动画持续250毫秒
        self.fade_animation.setStartValue(1.0)  # 起始值：完全不透明
        self.fade_animation.setEndValue(0.0)   # 结束值：完全透明
        self.fade_animation.setEasingCurve(QEasingCurve.OutQuart)  # 使用平滑的缓动曲线
        self.fade_animation.finished.connect(self._on_fade_finished)
    
    def _start_fade_out(self):
        """
        启动淡出动画
        """
        if not self.isVisible() or self.is_fading_out:
            return
        
        # 标记正在淡出
        self.is_fading_out = True
        # 启动淡出动画
        self.fade_animation.start()
    
    def _on_fade_finished(self):
        """
        淡出动画完成后的处理
        """
        if self.is_fading_out:
            # 重置标志
            self.is_fading_out = False
            # 重置不透明度为1，以便下次显示
            self.opacity_effect.setOpacity(1.0)
            # 真正隐藏窗口
            super(SelectableTooltip, self).hide()
    
    def hide(self):
        """
        重写隐藏方法，使用淡出效果
        """
        # 如果已经在淡出中，不再重复操作
        if self.is_fading_out:
            return
        
        # 如果窗口可见，启动淡出动画
        if self.isVisible():
            self._start_fade_out()
        else:
            # 窗口已经不可见，直接调用父类的hide
            super(SelectableTooltip, self).hide()
    
    def _show_context_menu(self, pos):
        """
        显示右键菜单
        
        Args:
            pos: 菜单显示位置
        """
        # 设置菜单显示标志
        self.is_menu_visible = True
        
        # 创建自定义菜单
        menu = QMenu(self)
        
        # 连接菜单关闭信号
        menu.aboutToHide.connect(self._on_menu_hide)
        
        # 使用与项目一致的样式
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                padding: 3px;
                font-family: "Microsoft YaHei", "SimSun", sans-serif;
                font-size: 9pt;
            }
            QMenu::item {
                padding: 5px 25px 5px 30px;
                border: 1px solid transparent;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
                color: #333333;
            }
            QMenu::separator {
                height: 1px;
                background-color: #d0d0d0;
                margin: 3px 10px;
            }
        """)
        
        # 添加复制操作
        cursor = self.text_browser.textCursor()
        has_selection = cursor.hasSelection()
        
        copy_action = QAction("复制", self)
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(self._copy_selection)
        menu.addAction(copy_action)
        
        # 添加全选操作
        select_all_action = QAction("全选", self)
        select_all_action.triggered.connect(self.text_browser.selectAll)
        menu.addAction(select_all_action)
        
        # 显示菜单
        menu.exec_(self.text_browser.mapToGlobal(pos))
    
    def _on_menu_hide(self):
        """
        菜单关闭时触发
        """
        # 菜单关闭后重置标志
        self.is_menu_visible = False
        
        # 检查鼠标是否在窗口内
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            # 启动隐藏计时器，延迟关闭
            self.hide_timer.start(300)
    
    def _copy_selection(self):
        """
        复制选中的文本
        """
        self.text_browser.copy()
    
    def setText(self, text):
        """
        设置工具提示文本
        
        Args:
            text (str): HTML格式的文本
        """
        self.text_browser.setHtml(text)
        
        # 调整大小以适应内容，但不超过最大限制
        self.text_browser.document().adjustSize()
        document_size = self.text_browser.document().size().toSize()
        
        width = min(document_size.width() + 20, self.text_browser.maximumWidth())
        height = min(document_size.height() + 15, self.text_browser.maximumHeight())
        
        self.text_browser.setMinimumSize(min(width, 200), min(height, 100))
        self.adjustSize()
    
    def showEvent(self, event):
        """
        显示事件处理
        
        Args:
            event: 显示事件
        """
        # 确保窗口显示时是不透明的
        self.opacity_effect.setOpacity(1.0)
        self.is_fading_out = False
        
        super(SelectableTooltip, self).showEvent(event)
        # 取消所有选择
        cursor = self.text_browser.textCursor()
        cursor.clearSelection()
        self.text_browser.setTextCursor(cursor)
        
        # 取消隐藏定时器
        self.hide_timer.stop()
    
    def eventFilter(self, obj, event):
        """
        事件过滤器
        
        用于检测文本选择状态和鼠标移动
        
        Args:
            obj: 被监视的对象
            event: 事件
            
        Returns:
            bool: 是否处理了事件
        """
        # 如果菜单可见，阻止关闭
        if self.is_menu_visible and isinstance(event, QEvent) and event.type() in [QEvent.MouseMove, QEvent.Leave]:
            self.hide_timer.stop()  # 确保定时器停止
            return False
            
        # 检测鼠标按下事件，标记为选择中
        if event.type() == QEvent.MouseButtonPress:
            if obj == self.text_browser.viewport() or obj == self:
                self.is_selecting = True
                self.hide_timer.stop()  # 停止隐藏定时器
            return False
        
        # 检测鼠标释放事件，取消选择中标记
        elif event.type() == QEvent.MouseButtonRelease:
            # 如果是在tooltip内部释放按键，保持选择标记一会儿，以便能复制
            if obj == self.text_browser.viewport() or obj == self:
                self.is_selecting = False
                self.hide_timer.stop()
            # 处理在窗口外释放的情况，但要避免在菜单显示时关闭窗口
            elif not self.is_menu_visible and not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                self.is_selecting = False
                self.hide_timer.start(500)  # 500毫秒后隐藏
            return False
        
        # 处理全局事件，跟踪鼠标移动
        if obj == QApplication.instance():
            # 如果鼠标不在当前窗口内，也不在菜单内
            if (event.type() == QEvent.MouseMove and 
                not self.is_selecting and 
                not self.is_menu_visible and 
                self.isVisible() and 
                not self.rect().contains(self.mapFromGlobal(QCursor.pos()))):
                
                if not self.hide_timer.isActive():
                    self.hide_timer.start(600)  # 稍微延长等待时间，提升用户体验
                    
            # 如果鼠标回到窗口内，取消定时器
            elif event.type() == QEvent.MouseMove and self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                self.hide_timer.stop()
                
            return False
        
        return super(SelectableTooltip, self).eventFilter(obj, event)
    
    def enterEvent(self, event):
        """
        鼠标进入事件处理
        
        Args:
            event: 进入事件
        """
        # 鼠标进入窗口，停止隐藏定时器
        self.hide_timer.stop()
        super(SelectableTooltip, self).enterEvent(event)
    
    def leaveEvent(self, event):
        """
        鼠标离开事件处理
        
        Args:
            event: 离开事件
        """
        # 如果不是在选择中且菜单没有显示，才启动隐藏定时器
        if not self.is_selecting and not self.is_menu_visible:
            self.hide_timer.start(500)  # 500毫秒后隐藏
        super(SelectableTooltip, self).leaveEvent(event)
        
    def hideEvent(self, event):
        """
        窗口隐藏事件处理
        
        Args:
            event: 隐藏事件
        """
        # 在窗口隐藏时清除标志
        self.is_selecting = False
        self.is_menu_visible = False
        super(SelectableTooltip, self).hideEvent(event)


class TooltipDelegate(RequiredFieldDelegate):
    """
    工具提示委托类
    
    为单元格内容添加工具提示，当内容被截断或包含换行符时，
    悬停鼠标会显示完整内容。特别适用于"其他账号"列中包含多行文本的情况。
    同时继承RequiredFieldDelegate的所有功能，包括编辑模式下的高亮样式。
    """
    
    def __init__(self, parent=None, column_index=7):  # 默认为"其他账号"列（索引7）
        """
        初始化工具提示委托
        
        Args:
            parent: 父对象
            column_index: 应用工具提示的列索引，默认为"其他账号"列（索引7）
        """
        # 调用RequiredFieldDelegate的初始化方法
        super(TooltipDelegate, self).__init__(parent)
        self.column_index = column_index
        logger.info(f"初始化工具提示委托，为列 {column_index} 添加工具提示功能，并继承编辑模式高亮样式")
        
        # 创建可选择文本的工具提示实例
        self.tooltip = None
    
    def helpEvent(self, event, view, option, index):
        """
        处理帮助事件，显示工具提示
        
        当鼠标悬停在单元格上时，检查是否需要显示工具提示
        
        Args:
            event: 事件对象
            view: 视图对象
            option: 样式选项
            index: 模型索引
            
        Returns:
            bool: 事件是否已处理
        """
        # 检查是否是目标列(其他账号列或其他指定列)
        if index.column() != self.column_index:
            # 不是目标列，使用默认行为
            return super(TooltipDelegate, self).helpEvent(event, view, option, index)
        
        # 获取单元格内容
        text = index.data(Qt.DisplayRole)
        if not text:
            # 没有内容，不显示工具提示
            return super(TooltipDelegate, self).helpEvent(event, view, option, index)
        
        # 检查内容是否包含换行符或者宽度超过单元格
        content_too_long = False
        
        # 判断文本是否包含换行符
        if "\n" in text or "\r" in text:
            content_too_long = True
        else:
            # 判断文本是否宽度超过单元格
            painter = QPainter()
            painter.begin(view)
            font_metrics = painter.fontMetrics()
            painter.end()
            
            # 计算文本宽度
            text_width = font_metrics.horizontalAdvance(text)
            # 考虑单元格内边距
            cell_width = option.rect.width() - 10
            
            if text_width > cell_width:
                content_too_long = True
        
        if content_too_long:
            # 格式化内容为HTML，保留换行符
            tooltip_text = text.replace("\n", "<br>")
            tooltip_html = f"<div style='white-space:pre-wrap;'>{tooltip_text}</div>"
            
            # 使用自定义工具提示替代标准QToolTip
            if not self.tooltip:
                self.tooltip = SelectableTooltip()
            
            # 设置工具提示内容
            self.tooltip.setText(tooltip_html)
            
            # 计算显示位置（鼠标右下角）
            global_pos = event.globalPos()
            tooltip_pos = global_pos + QPoint(5, 5)
            
            # 显示工具提示
            self.tooltip.move(tooltip_pos)
            self.tooltip.show()
            return True
        elif self.tooltip and self.tooltip.isVisible():
            # 如果内容不长，但工具提示正在显示，则隐藏
            self.tooltip.hide()
        
        # 如果内容没有被截断，使用默认行为（不显示工具提示）
        return super(TooltipDelegate, self).helpEvent(event, view, option, index) 