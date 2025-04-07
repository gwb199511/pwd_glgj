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
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer, pyqtSignal, QObject, QPoint
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
    交互式步骤引导浮层
    
    提供半透明浮层，高亮显示当前步骤的目标区域，并通过提示框引导用户操作
    """
    
    # 引导完成信号
    finished = pyqtSignal()
    
    # 图片缓存
    _image_cache = {}
    
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
        
        # 当前高亮的区域，确保初始化为一个空的QRect
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
        
        # 预加载菜单图片
        self._preload_menu_images()
        
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
    
    def _preload_menu_images(self):
        """预加载菜单图片以加快显示速度"""
        try:
            # 要加载的文件名
            image_files = ["account_menu.png", "password_menu.png"]
            
            # 图片基础路径
            base_paths = [
                os.path.abspath(os.path.join(os.getcwd(), "images")),
                os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), "images")),
                r"C:\Users\gwb\Desktop\pwd_glgj\images"
            ]
            
            logger.info("开始预加载菜单图片...")
            
            # 尝试每个文件和路径的组合
            for filename in image_files:
                # 找到图片并加载到缓存
                for base_path in base_paths:
                    path = os.path.join(base_path, filename)
                    if os.path.exists(path):
                        logger.info(f"预加载图片: {path}")
                        pixmap = QPixmap(path)
                        if not pixmap.isNull():
                            # 存入缓存
                            self._image_cache[filename] = pixmap
                            logger.info(f"成功预加载图片: {filename}")
                            break
            
            logger.info(f"预加载完成，共加载 {len(self._image_cache)} 张图片")
        except Exception as e:
            logger.error(f"预加载图片时出错: {str(e)}")
    
    def _show_menu_image(self, step):
        """
        显示菜单图片而非触发真实菜单
        
        Args:
            step (dict): 步骤信息，包含列索引等
        """
        # 清理已有的菜单图片（如果存在）
        self._clear_menu_image()
        
        # 获取列类型
        column_index = step.get("column_index", 4)  # 默认密码列
        
        # 选择对应图片文件名
        base_name = "account_menu.png" if column_index == 3 else "password_menu.png"
        
        # 从缓存获取图片
        pixmap = self._image_cache.get(base_name)
        
        # 如果缓存中没有，尝试即时加载
        if pixmap is None:
            logger.info(f"缓存中未找到图片 {base_name}，尝试加载...")
            # 尝试不同格式的路径
            image_paths = []
            
            # 添加可能的路径
            image_paths.append(os.path.abspath(os.path.join(os.getcwd(), "images", base_name)))
            image_paths.append(os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), "images", base_name)))
            image_paths.append(r"C:\Users\gwb\Desktop\pwd_glgj\images\{}".format(base_name))
            
            # 记录尝试加载的路径
            logger.info(f"尝试加载菜单图片，列索引: {column_index}, 文件名: {base_name}")
            
            # 尝试加载图片
            loaded_path = None
            
            for image_path in image_paths:
                try:
                    # 检查文件是否存在
                    if os.path.exists(image_path):
                        logger.info(f"文件存在: {image_path}")
                        temp_pixmap = QPixmap(image_path)
                        if not temp_pixmap.isNull():
                            pixmap = temp_pixmap
                            # 添加到缓存
                            self._image_cache[base_name] = pixmap
                            loaded_path = image_path
                            logger.info(f"成功加载图片并添加到缓存: {image_path}")
                            break
                except Exception as e:
                    logger.error(f"加载路径 {image_path} 时出错: {str(e)}")
        else:
            logger.info(f"从缓存中获取图片: {base_name}")
        
        # 如果仍然无法加载图片，使用文本标签作为备选
        if pixmap is None or pixmap.isNull():
            logger.warning("无法加载图片，使用文本标签作为备选")
            
            # 创建文本标签
            menu_image = QLabel(self)
            menu_image.setObjectName("menu_image")
            
            # 设置样式
            menu_image.setStyleSheet("""
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
            """)
            
            # 设置内容
            if column_index == 3:  # 账号列
                menu_text = "账号列右键菜单：\n\n· 复制\n————————————\n· 添加行\n· 编辑行\n· 删除行"
            else:  # 密码列
                menu_text = "密码列右键菜单：\n\n· 复制\n· 生成16位随机密码\n  并更新到服务器\n————————————\n· 添加行\n· 编辑行\n· 删除行"
            
            menu_image.setText(menu_text)
            menu_image.setFixedSize(180, 200)  # 设置固定大小
            
            # 根据步骤中设置的位置或默认位置计算显示位置
            target = None
            if "widget_id" in step and step["widget_id"] in self.target_widgets:
                target = self.target_widgets[step["widget_id"]]
            
            if target and hasattr(target, "viewport"):
                # 表格控件
                visible_rect = target.viewport().rect()
                
                # 根据列索引区分位置
                if column_index == 3:  # 账号列
                    # 靠近表格左边
                    menu_x = visible_rect.left() + 50
                else:  # 密码列
                    # 靠近表格中间偏右位置，不要靠近表格边缘
                    menu_x = visible_rect.center().x() + 50  # 从中心向右偏移50像素
                
                menu_y = visible_rect.top() + 150  # 固定位置
                
                # 获取全局位置并调整
                global_pos = target.mapToGlobal(QPoint(menu_x, menu_y))
                parent_pos = self.mapFromGlobal(global_pos)
                
                menu_x = parent_pos.x()
                menu_y = parent_pos.y()
            else:
                # 默认中心位置
                menu_x = (self.width() - menu_image.width()) // 2
                menu_y = (self.height() - menu_image.height()) // 2
            
            # 显示文本菜单
            menu_image.move(menu_x, menu_y)
            menu_image.raise_()  # 确保菜单在顶层
            menu_image.show()
            
            # 记录到当前步骤中
            step["menu_image_widget"] = menu_image
            
            # 设置高亮区域
            self.highlight_rect = QRect(menu_x, menu_y, menu_image.width(), menu_image.height())
            self.update()
            
            # 确保提示框在菜单下方
            step["position"] = "menu_bottom"  
            
            # 延迟更新提示框位置，确保菜单先显示
            QTimer.singleShot(50, lambda: self._position_tooltip(step))
            QTimer.singleShot(60, lambda: self.tooltip_widget.raise_())  # 确保提示框在顶层
            
            logger.info(f"已创建文本菜单替代图片，位置: ({menu_x}, {menu_y})")
            return
            
        try:
            # 创建QLabel显示图片
            menu_image = QLabel(self)
            menu_image.setObjectName("menu_image")
            menu_image.setPixmap(pixmap)
            
            # 根据步骤中设置的位置或默认位置计算显示位置
            target = None
            if "widget_id" in step and step["widget_id"] in self.target_widgets:
                target = self.target_widgets[step["widget_id"]]
            
            if target and hasattr(target, "viewport"):
                # 表格控件
                visible_rect = target.viewport().rect()
                
                # 根据列索引区分位置
                if column_index == 3:  # 账号列
                    # 靠近表格左边
                    menu_x = visible_rect.left() + 50
                else:  # 密码列
                    # 靠近表格中间偏右位置，不要靠近表格边缘
                    menu_x = visible_rect.center().x() + 50  # 从中心向右偏移50像素
                
                menu_y = visible_rect.top() + 150  # 固定位置
                
                # 获取全局位置并调整
                global_pos = target.mapToGlobal(QPoint(menu_x, menu_y))
                parent_pos = self.mapFromGlobal(global_pos)
                
                menu_x = parent_pos.x()
                menu_y = parent_pos.y()
            else:
                # 默认中心位置
                menu_x = (self.width() - pixmap.width()) // 2
                menu_y = (self.height() - pixmap.height()) // 2
            
            # 显示图片
            menu_image.move(menu_x, menu_y)
            menu_image.raise_()  # 确保菜单在顶层
            menu_image.show()
            
            # 记录到当前步骤中
            step["menu_image_widget"] = menu_image
            
            # 设置高亮区域
            self.highlight_rect = QRect(menu_x, menu_y, pixmap.width(), pixmap.height())
            self.update()
            
            # 确保提示框在菜单下方
            step["position"] = "menu_bottom"  
            
            # 延迟更新提示框位置，确保菜单先显示
            QTimer.singleShot(50, lambda: self._position_tooltip(step))
            QTimer.singleShot(60, lambda: self.tooltip_widget.raise_())  # 确保提示框在顶层
            
            logger.info(f"成功显示菜单图片，位置: ({menu_x}, {menu_y})")
            
        except Exception as e:
            logger.error(f"显示菜单图片时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _clear_menu_image(self):
        """清理当前显示的菜单图片"""
        try:
            # 查找所有menu_image控件并删除
            for widget in self.findChildren(QLabel, "menu_image"):
                widget.deleteLater()
            
            # 如果当前步骤中有菜单图片引用，也清除
            if self.current_step < len(self.steps):
                current_step = self.steps[self.current_step]
                if "menu_image_widget" in current_step:
                    if current_step["menu_image_widget"] is not None:
                        try:
                            current_step["menu_image_widget"].deleteLater()
                        except:
                            pass
                    current_step["menu_image_widget"] = None
                    
            logger.info("已清理菜单图片")
        except Exception as e:
            logger.error(f"清理菜单图片时出错: {str(e)}")
    
    def _calculate_highlight_rect(self, step):
        """
        计算当前步骤的高亮区域
        
        Args:
            step (dict): 步骤信息
            
        Returns:
            QRect: 高亮区域矩形
        """
        # 获取目标控件
        target = None
        if "target" in step:
            # 直接使用步骤中保存的目标控件
            target = step["target"]
        elif "widget_id" in step and step["widget_id"] in self.target_widgets:
            # 使用控件ID从目标控件字典中获取控件
            target = self.target_widgets[step["widget_id"]]
        
        # 如果有目标控件，计算其位置和尺寸
        if target and hasattr(target, "rect"):
            # 获取控件全局位置并转换为父窗口坐标
            global_pos = target.mapToGlobal(target.rect().topLeft())
            parent_pos = self.parent().mapFromGlobal(global_pos)
            self.highlight_rect = QRect(parent_pos, target.size())
        else:
            # 默认不高亮任何区域，但确保是一个有效的空QRect
            self.highlight_rect = QRect()
        
        # 设置提示框位置
        self.tooltip_position = step.get("position", "bottom")
        
        # 检查是否需要显示菜单图片
        if step.get("show_menu_image", False) and not step.get("menu_image_shown", False):
            # 标记菜单图片已显示
            step["menu_image_shown"] = True
            # 延迟显示图片菜单
            QTimer.singleShot(300, lambda: self._show_menu_image(step))
            
        # 返回计算后的高亮区域
        return self.highlight_rect

    def _show_current_step(self):
        """显示当前步骤的高亮区域和提示"""
        if self.current_step >= len(self.steps):
            self._finish_guide()
            return
        
        # 获取当前步骤（创建一个深拷贝，避免共享状态）
        step = self.steps[self.current_step].copy()
        
        # 重置高亮区域
        self.highlight_rect = QRect()
        
        # 设置标题和描述
        self.title_label.setText(step.get("title", ""))
        self.description_label.setText(step.get("description", ""))
        
        # 计算高亮区域并更新
        highlight_rect = self._calculate_highlight_rect(step)
        if highlight_rect is not None:
            self.highlight_rect = highlight_rect
        else:
            self.highlight_rect = QRect()  # 确保不为None
        
        # 更新浮层
        self.update()
        
        # 检查是否显示菜单图片
        if not step.get("show_menu_image", False):
            # 如果不显示菜单图片，立即定位并显示提示框
            self._position_tooltip(step)
            self.tooltip_widget.show()
        # 否则，提示框位置将在_show_menu_image中通过定时器设置
        
        # 更新步骤指示器和按钮状态
        self._update_step_indicators()
        self._update_buttons()
    
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
        """
        定位提示框
        
        Args:
            step (dict): 步骤信息
        """
        # 如果step为None，使用默认居中位置
        if step is None:
            self.tooltip_widget.move(
                (self.width() - self.tooltip_widget.width()) // 2,
                (self.height() - self.tooltip_widget.height()) // 2
            )
            return
        
        # 确保提示框尺寸合适
        self.tooltip_widget.adjustSize()
        
        # 获取高亮区域
        rect = self.highlight_rect
        
        # 如果没有高亮区域或rect无效，居中显示
        if rect is None or rect.isEmpty():
            self.tooltip_widget.move(
                (self.width() - self.tooltip_widget.width()) // 2,
                (self.height() - self.tooltip_widget.height()) // 2
            )
            return
            
        # 检查是否是菜单相关步骤
        is_menu_step = step.get("show_menu_image", False)
        position = step.get("position", "bottom")
        
        # 如果是菜单相关步骤，特殊处理位置
        if is_menu_step and position == "menu_bottom":
            # 对于菜单步骤，将提示框放在菜单下方
            
            # 获取列类型，根据列类型调整水平对齐方式
            column_index = step.get("column_index", 4)  # 默认密码列
            
            if column_index == 3:  # 账号列（左侧显示）
                # 与菜单左对齐
                tooltip_x = rect.x()
            else:  # 密码列（右侧显示）
                # 与菜单右对齐
                tooltip_x = rect.x() + rect.width() - self.tooltip_widget.width()
            
            # 在菜单下方留出15像素空间，确保上下相邻但间距合适
            tooltip_y = rect.y() + rect.height() + 15
            
            # 验证位置合理性，防止越界
            if tooltip_y < 0 or tooltip_y > self.height() - 50:
                # 位置不合理，重置为中间位置
                tooltip_y = self.height() // 3
                
            if tooltip_x < 0 or tooltip_x > self.width() - self.tooltip_widget.width():
                # 水平位置不合理，重置为中间
                tooltip_x = (self.width() - self.tooltip_widget.width()) // 2
            
            # 记录日志
            logger.info(f"将提示框放在菜单下方，位置: ({tooltip_x}, {tooltip_y})")
            
            # 设置提示框位置
            self.tooltip_widget.move(tooltip_x, tooltip_y)
            self.tooltip_widget.show()  # 确保提示框显示
        elif position == "bottom":
            self.tooltip_widget.move(
                rect.x() + (rect.width() - self.tooltip_widget.width()) // 2,
                rect.y() + rect.height() + 10
            )
        elif position == "top":
            self.tooltip_widget.move(
                rect.x() + (rect.width() - self.tooltip_widget.width()) // 2,
                rect.y() - self.tooltip_widget.height() - 10
            )
        elif position == "left":
            self.tooltip_widget.move(
                rect.x() - self.tooltip_widget.width() - 10,
                rect.y() + (rect.height() - self.tooltip_widget.height()) // 2
            )
        elif position == "right":
            # 标准右侧位置
            self.tooltip_widget.move(
                rect.x() + rect.width() + 10,
                rect.y() + (rect.height() - self.tooltip_widget.height()) // 2
            )
        
        # 调整位置，确保提示框在视图范围内
        self._adjust_tooltip_position()
    
    def _next_step(self):
        """前进到下一步"""
        if self.current_step < len(self.steps) - 1:
            # 清理当前步骤的菜单图片
            self._clear_menu_image()
            
            # 步骤递增
            self.current_step += 1
            logger.info(f"已递增步骤索引到: {self.current_step}")
            
            # 显示新步骤
            self._show_current_step()
        else:
            self._finish_guide()
    
    def _prev_step(self):
        """返回上一步"""
        if self.current_step > 0:
            # 清理当前步骤的菜单图片
            self._clear_menu_image()
            
            # 步骤递减
            self.current_step -= 1
            logger.info(f"已递减步骤索引到: {self.current_step}")
            
            # 显示新步骤
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
        if self.highlight_rect is not None and self.highlight_rect.isValid():
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
            
            # 普通高亮区域样式 - 修复缩进错误
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

    def _adjust_tooltip_position(self):
        """
        调整提示框位置，确保它在视图范围内
        """
        # 获取当前位置
        pos = self.tooltip_widget.pos()
        size = self.tooltip_widget.size()
        
        # 调整X坐标确保不超出屏幕左右边界
        if pos.x() < 10:
            pos.setX(10)
        elif pos.x() + size.width() > self.width() - 10:
            pos.setX(self.width() - size.width() - 10)
        
        # 调整Y坐标确保不超出屏幕上下边界
        if pos.y() < 10:
            pos.setY(10)
        elif pos.y() + size.height() > self.height() - 10:
            pos.setY(self.height() - size.height() - 10)
        
        # 应用调整后的位置
        self.tooltip_widget.move(pos)


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
        "description": "在账号列上右击可显示操作菜单，支持复制账号内容以及添加、编辑和删除记录功能。\n\n注意：实际使用时可在任意（除了密码列）的单元格右击。",
        "position": "menu_bottom",
        "show_menu_image": True,  # 使用图片显示菜单
        "widget_id": "password_table", 
        "column_index": 3  # 指定账号列的索引
    },
    {
        "title": "右键操作（密码列）",
        "description": "在密码列上右击可显示操作菜单，包括复制密码和生成随机密码等功能。\n也可进行添加、编辑和删除记录操作。\n\n支持多选操作，批量更新服务器密码。",
        "position": "menu_bottom",
        "show_menu_image": True,  # 使用图片显示菜单
        "widget_id": "password_table",
        "column_index": 4  # 指定密码列的索引
    },
    {
        "title": "功能菜单",
        "description": "在菜单栏可以访问更多高级功能，如密码生成器、审计日志查看等。",
        "position": "bottom",
        "widget_id": "toolbar"
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
        
        # 标记引导已完成（使用延迟保存）
        user_settings.user_settings.mark_guide_completed(guide_key, immediate=False)
        logger.info(f"用户已完成步骤引导: {guide_key}")
    
    overlay.finished.connect(on_walkthrough_finished)
    
    # 传递控件字典，用于特殊处理（如显示上下文菜单）
    overlay.set_target_widgets(target_widgets)
    overlay.set_steps(walkthrough_steps)
    
    return True 