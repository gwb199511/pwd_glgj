#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
图标管理器
用于集中管理应用程序的所有图标资源
"""

import os
import logging
from typing import Dict, Optional
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize

# 配置日志
logger = logging.getLogger(__name__)

class IconManager:
    """
    图标管理器类
    管理应用程序中使用的所有图标资源
    """
    
    # 单例实例
    _instance = None
    
    # 图标缓存
    _icon_cache: Dict[str, QIcon] = {}
    
    # 图标路径
    _icon_paths = [
        # 项目根目录下的icons文件夹
        os.path.abspath(os.path.join(os.getcwd(), "icons")),
        # 上级目录下的icons文件夹
        os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), "icons")),
    ]
    
    # 图标映射表 - 菜单项名称到图标文件名的映射
    _menu_icon_map = {
        # 文件菜单
        "文件": "menu_file.png",
        # 可能带有空格或特殊字符的变体
        " 文件": "menu_file.png",
        "□文件": "menu_file.png",  # 没有空格的特殊字符前缀版本
        "□ 文件": "menu_file.png",  # 带空格的特殊字符前缀版本
        "■文件": "menu_file.png", 
        "■ 文件": "menu_file.png",
        
        # 文件菜单子项
        "导入/导出": "import_export.png",
        "退出": "exit.png",
        
        # 导入/导出子菜单项
        "从Excel导入": "excel_import.png",
        "导出到Excel": "excel_export.png",
        
        # 这些项不属于任何菜单，不需要图标
        "人员列表": None,
        "检索明细": None,
        "高文彬": None,
        "石航": None,
        "高文彬 ": None,  # 带空格版本
        "石航 ": None,    # 带空格版本
        "徐国明": None,
        "石帆": None,
        
        # 工具菜单
        "工具": "menu_tools.png",
        " 工具": "menu_tools.png",
        "□工具": "menu_tools.png",  # 没有空格的特殊字符前缀版本
        "□ 工具": "menu_tools.png",  # 带空格的特殊字符前缀版本
        "■工具": "menu_tools.png",
        "■ 工具": "menu_tools.png",
        "数据库配置": "database_config.png",
        "密码生成器": "password_generator.png",
        "审计日志": "audit_log.png",  # 修正为审计日志
        "统计日志": "audit_log.png",  # 保留旧名称以防万一
        "显示字典引导": "dictionary_guide.png",
        "检查更新": "check_update.png",
        
        # 帮助菜单
        "帮助": "menu_help.png",
        " 帮助": "menu_help.png",
        "□帮助": "menu_help.png",  # 没有空格的特殊字符前缀版本
        "□ 帮助": "menu_help.png",  # 带空格的特殊字符前缀版本
        "■帮助": "menu_help.png",
        "■ 帮助": "menu_help.png",
        "关于": "about.png",
        
        # 表格右键菜单
        "复制": "copy.png",
        "添加行": "add_row.png",
        "编辑行": "edit_row.png",
        "删除行": "delete_row.png",
        "查看历史密码修改记录": "history.png",
        "生成16位随机密码\n并更新到服务器": "generate_password.png",
        
        # 添加行子菜单项
        "在上方添加行": "add_row_above.png",
        "在下方添加行": "add_row_below.png",
        "在末尾添加行": "add_row_end.png",
        
        # 通用菜单项
        "复制内容": "copy.png",
        "复制密码": "copy_password.png",
        "复制IP地址": "copy_ip.png",
        "生成16位随机密码": "generate_password.png",
        "生成16位随机密码并更新到服务器(SSH)": "generate_password.png",
        "检查密码强度": "check_strength.png",
        "SSH连接": "ssh_connect.png",
        "Ping测试": "ping.png",
        "网络工具": "network_tools.png",
        "路由跟踪": "tracert.png",
        "Whois查询": "whois.png",
        "删除选中的行": "delete_row.png",
    }
    
    def __new__(cls, *args, **kwargs):
        """
        单例模式实现
        """
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        初始化图标管理器
        """
        # 防止重复初始化
        if getattr(self, "_initialized", False):
            return
        
        # 创建默认图标目录
        self._ensure_icon_directory()
        
        # 创建默认图标
        self._create_default_icons()
        
        # 标记为已初始化
        self._initialized = True
        
    def _ensure_icon_directory(self):
        """
        确保图标目录存在
        """
        for path in self._icon_paths:
            if not os.path.exists(path):
                try:
                    os.makedirs(path)
                    logger.info(f"创建图标目录: {path}")
                except Exception as e:
                    logger.error(f"创建图标目录失败: {str(e)}")
    
    def _create_default_icons(self):
        """
        为不存在的图标创建默认图标
        使用简单的文本渲染生成图标
        """
        # 检查是否有可用的图标目录
        icon_dir = next((p for p in self._icon_paths if os.path.exists(p)), None)
        if not icon_dir:
            logger.error("无法找到有效的图标目录")
            return
            
        # 创建图标引擎
        from PyQt5.QtWidgets import QApplication
        if not QApplication.instance():
            # 创建一个临时的QApplication实例，用于创建图标
            # 如果在GUI应用程序中调用，这一步会被跳过
            app = QApplication([])
            
        from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QBrush
        
        # 为每个菜单项创建默认图标
        for name, filename in self._menu_icon_map.items():
            # 跳过None值，这些是被标记为不需要图标的菜单项
            if filename is None:
                logger.debug(f"跳过不需要图标的菜单项: {name}")
                continue
                
            file_path = os.path.join(icon_dir, filename)
            
            # 检查图标是否已存在
            if os.path.exists(file_path):
                continue
                
            try:
                # 创建一个16x16的图标
                pixmap = QPixmap(16, 16)
                pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景
                
                # 设置绘图器
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # 根据名称生成不同的图标
                if "文件" in name:
                    # 文件图标 - 绘制一个文件形状
                    painter.setPen(QPen(QColor(80, 100, 140), 1))
                    painter.setBrush(QBrush(QColor(220, 230, 240)))
                    painter.drawRect(3, 3, 10, 12)
                    painter.drawLine(6, 3, 6, 6)
                    painter.drawLine(6, 6, 10, 6)
                    
                elif "退出" in name:
                    # 退出图标 - 绘制一个门和箭头
                    painter.setPen(QPen(QColor(160, 80, 80), 1))
                    painter.setBrush(QBrush(QColor(250, 220, 220)))
                    painter.drawRect(3, 3, 8, 10)
                    painter.drawLine(11, 8, 14, 8)
                    painter.drawLine(14, 8, 12, 6)
                    painter.drawLine(14, 8, 12, 10)
                
                elif "导入" in name or "import" in name.lower():
                    # 导入图标 - 绘制一个向下箭头
                    painter.setPen(QPen(QColor(80, 140, 80), 1))
                    painter.setBrush(QBrush(QColor(220, 250, 220)))
                    painter.drawRect(3, 3, 10, 10)
                    painter.drawLine(8, 4, 8, 10)
                    painter.drawLine(5, 7, 8, 10)
                    painter.drawLine(11, 7, 8, 10)
                    
                elif "导出" in name or "export" in name.lower():
                    # 导出图标 - 绘制一个向上箭头
                    painter.setPen(QPen(QColor(80, 120, 160), 1))
                    painter.setBrush(QBrush(QColor(220, 240, 250)))
                    painter.drawRect(3, 3, 10, 10)
                    painter.drawLine(8, 10, 8, 4)
                    painter.drawLine(5, 7, 8, 4)
                    painter.drawLine(11, 7, 8, 4)
                
                elif "Excel" in name:
                    # Excel图标 - 绘制一个类似Excel的图标
                    painter.setPen(QPen(QColor(40, 120, 80), 1))
                    painter.setBrush(QBrush(QColor(230, 250, 240)))
                    painter.drawRect(3, 3, 10, 10)
                    painter.drawLine(5, 6, 11, 6)
                    painter.drawLine(5, 8, 11, 8)
                    painter.drawLine(7, 4, 7, 12)
                    painter.drawLine(9, 4, 9, 12)
                    
                elif "工具" in name:
                    # 工具图标 - 绘制一个工具形状
                    painter.setPen(QPen(QColor(100, 100, 100), 1))
                    painter.setBrush(QBrush(QColor(220, 220, 220)))
                    painter.drawEllipse(3, 3, 6, 6)
                    painter.drawRect(7, 7, 6, 6)
                    
                elif "帮助" in name:
                    # 帮助图标 - 绘制一个问号
                    painter.setPen(QPen(QColor(100, 120, 180), 2))
                    painter.setBrush(QBrush(QColor(220, 230, 250)))
                    painter.drawEllipse(3, 3, 10, 10)
                    painter.setPen(QPen(QColor(60, 80, 140), 2))
                    painter.drawText(6, 11, "?")
                    
                elif "人员" in name or "user" in name.lower():
                    # 用户图标 - 绘制一个用户形状
                    painter.setPen(QPen(QColor(80, 120, 160), 1))
                    painter.setBrush(QBrush(QColor(210, 230, 245)))
                    painter.drawEllipse(5, 3, 6, 6)  # 头部
                    painter.drawRect(3, 9, 10, 5)    # 身体
                    
                elif "数据库" in name or "database" in name.lower():
                    # 数据库图标
                    painter.setPen(QPen(QColor(80, 120, 160), 1))
                    painter.setBrush(QBrush(QColor(220, 240, 250)))
                    painter.drawEllipse(3, 2, 10, 4)
                    painter.drawEllipse(3, 6, 10, 4)
                    painter.drawEllipse(3, 10, 10, 4)
                    
                elif "密码" in name or "password" in name.lower():
                    # 密码图标 - 绘制一个锁形状
                    painter.setPen(QPen(QColor(80, 100, 160), 1))
                    painter.setBrush(QBrush(QColor(230, 240, 250)))
                    painter.drawRoundedRect(4, 8, 8, 6, 1, 1)
                    painter.drawRect(6, 4, 4, 4)
                    
                elif "审计" in name or "日志" in name or "统计" in name:
                    # 审计日志图标 - 绘制一个图表
                    painter.setPen(QPen(QColor(80, 140, 120), 1))
                    painter.setBrush(QBrush(QColor(220, 250, 240)))
                    painter.drawLine(3, 13, 3, 3)
                    painter.drawLine(3, 13, 13, 13)
                    painter.drawLine(5, 10, 7, 6)
                    painter.drawLine(7, 6, 9, 9)
                    painter.drawLine(9, 9, 12, 5)
                    
                elif "引导" in name or "guide" in name.lower():
                    # 引导图标 - 绘制一个指南针
                    painter.setPen(QPen(QColor(160, 100, 80), 1))
                    painter.setBrush(QBrush(QColor(250, 230, 220)))
                    painter.drawEllipse(3, 3, 10, 10)
                    painter.drawLine(8, 8, 5, 5)
                    painter.drawLine(8, 8, 11, 5)
                    
                elif "更新" in name or "update" in name.lower():
                    # 更新图标 - 绘制一个循环箭头
                    painter.setPen(QPen(QColor(100, 160, 100), 1))
                    painter.setBrush(QBrush(QColor(230, 250, 230)))
                    painter.drawArc(3, 3, 10, 10, 0, 270 * 16)
                    painter.drawLine(13, 8, 13, 5)
                    painter.drawLine(13, 5, 10, 5)
                    
                elif "关于" in name or "about" in name.lower():
                    # 关于图标 - 绘制一个i字母
                    painter.setPen(QPen(QColor(100, 140, 180), 1))
                    painter.setBrush(QBrush(QColor(230, 240, 250)))
                    painter.drawEllipse(3, 3, 10, 10)
                    painter.setPen(QPen(QColor(60, 100, 140), 2))
                    painter.drawText(7, 11, "i")
                    
                elif "复制" in name or "copy" in name.lower():
                    # 复制图标 - 绘制两个重叠的文档
                    painter.setPen(QPen(QColor(100, 120, 160), 1))
                    painter.setBrush(QBrush(QColor(230, 240, 250)))
                    painter.drawRect(6, 3, 7, 8)
                    painter.drawRect(3, 6, 7, 8)
                    
                elif "添加" in name or "add" in name.lower():
                    if "上方" in name:
                        # 在上方添加行图标 - 上箭头和加号
                        painter.setPen(QPen(QColor(80, 160, 80), 2))
                        painter.setBrush(QBrush(QColor(220, 250, 220)))
                        painter.drawEllipse(3, 3, 10, 10)
                        painter.drawLine(8, 6, 8, 12)
                        painter.drawLine(5, 9, 11, 9)
                        painter.drawLine(5, 5, 8, 2)
                        painter.drawLine(11, 5, 8, 2)
                    elif "下方" in name:
                        # 在下方添加行图标 - 下箭头和加号
                        painter.setPen(QPen(QColor(80, 160, 80), 2))
                        painter.setBrush(QBrush(QColor(220, 250, 220)))
                        painter.drawEllipse(3, 3, 10, 10)
                        painter.drawLine(8, 6, 8, 12)
                        painter.drawLine(5, 9, 11, 9)
                        painter.drawLine(5, 12, 8, 15)
                        painter.drawLine(11, 12, 8, 15)
                    elif "末尾" in name:
                        # 在末尾添加行图标 - 底部加号
                        painter.setPen(QPen(QColor(80, 160, 80), 2))
                        painter.setBrush(QBrush(QColor(220, 250, 220)))
                        painter.drawEllipse(3, 3, 10, 10)
                        painter.drawLine(8, 5, 8, 11)
                        painter.drawLine(5, 8, 11, 8)
                        painter.drawLine(3, 14, 13, 14)
                    else:
                        # 添加图标 - 绘制一个加号
                        painter.setPen(QPen(QColor(80, 160, 80), 2))
                        painter.setBrush(QBrush(QColor(220, 250, 220)))
                        painter.drawEllipse(3, 3, 10, 10)
                        painter.drawLine(8, 5, 8, 11)
                        painter.drawLine(5, 8, 11, 8)
                    
                elif "编辑" in name or "edit" in name.lower():
                    # 编辑图标 - 绘制一个铅笔
                    painter.setPen(QPen(QColor(160, 140, 60), 1))
                    painter.setBrush(QBrush(QColor(250, 240, 210)))
                    painter.drawLine(3, 13, 6, 10)
                    painter.drawLine(6, 10, 13, 3)
                    painter.drawLine(12, 2, 14, 4)
                    
                elif "删除" in name or "delete" in name.lower():
                    # 删除图标 - 绘制一个X
                    painter.setPen(QPen(QColor(160, 60, 60), 2))
                    painter.setBrush(QBrush(QColor(250, 210, 210)))
                    painter.drawEllipse(3, 3, 10, 10)
                    painter.drawLine(5, 5, 11, 11)
                    painter.drawLine(11, 5, 5, 11)
                    
                elif "历史" in name or "history" in name.lower():
                    # 历史记录图标 - 绘制一个时钟
                    painter.setPen(QPen(QColor(120, 100, 160), 1))
                    painter.setBrush(QBrush(QColor(240, 230, 250)))
                    painter.drawEllipse(3, 3, 10, 10)
                    painter.drawLine(8, 8, 8, 5)
                    painter.drawLine(8, 8, 11, 8)
                
                elif "ssh" in name.lower() or "连接" in name:
                    # SSH连接图标 - 终端图标
                    painter.setPen(QPen(QColor(100, 140, 100), 1))
                    painter.setBrush(QBrush(QColor(230, 250, 230)))
                    painter.drawRect(3, 4, 10, 8)
                    painter.drawLine(5, 7, 8, 7)
                    painter.drawLine(5, 9, 11, 9)
                
                elif "ping" in name.lower() or "测试" in name:
                    # Ping测试图标 - 信号图标
                    painter.setPen(QPen(QColor(80, 120, 160), 1))
                    painter.setBrush(QBrush(QColor(220, 240, 250)))
                    painter.drawArc(2, 2, 12, 12, 135 * 16, 270 * 16)
                    painter.drawArc(4, 4, 8, 8, 135 * 16, 270 * 16)
                    painter.drawArc(6, 6, 4, 4, 135 * 16, 270 * 16)
                    
                elif "网络" in name:
                    # 网络工具图标 - 网络图标
                    painter.setPen(QPen(QColor(80, 140, 160), 1))
                    painter.setBrush(QBrush(QColor(220, 240, 250)))
                    painter.drawEllipse(3, 3, 4, 4)
                    painter.drawEllipse(9, 3, 4, 4)
                    painter.drawEllipse(3, 9, 4, 4)
                    painter.drawEllipse(9, 9, 4, 4)
                    painter.drawLine(5, 5, 9, 5)
                    painter.drawLine(5, 11, 9, 11)
                    painter.drawLine(5, 5, 5, 11)
                    painter.drawLine(11, 5, 11, 11)
                
                elif "tracert" in name.lower() or "路由" in name:
                    # 路由跟踪图标 - 路径图标
                    painter.setPen(QPen(QColor(140, 80, 160), 1))
                    painter.setBrush(QBrush(QColor(240, 220, 250)))
                    painter.drawEllipse(2, 3, 4, 4)
                    painter.drawEllipse(6, 8, 4, 4)
                    painter.drawEllipse(10, 3, 4, 4)
                    painter.drawLine(4, 5, 8, 10)
                    painter.drawLine(12, 5, 8, 10)
                
                elif "whois" in name.lower() or "查询" in name:
                    # Whois查询图标 - 问号和信息图标
                    painter.setPen(QPen(QColor(100, 100, 180), 1))
                    painter.setBrush(QBrush(QColor(230, 230, 250)))
                    painter.drawEllipse(3, 3, 10, 10)
                    painter.setPen(QPen(QColor(80, 80, 160), 2))
                    painter.drawText(6, 12, "W")
                    
                elif "强度" in name or "check" in name.lower():
                    # 检查密码强度图标 - 盾牌图标
                    painter.setPen(QPen(QColor(160, 120, 60), 1))
                    painter.setBrush(QBrush(QColor(250, 240, 220)))
                    painter.drawPolygon([QPoint(8, 2), QPoint(14, 5), QPoint(14, 10), 
                                         QPoint(8, 14), QPoint(2, 10), QPoint(2, 5)])
                    painter.drawLine(5, 8, 8, 11)
                    painter.drawLine(8, 11, 11, 6)
                    
                else:
                    # 默认图标 - 绘制一个简单的圆形
                    painter.setPen(QPen(QColor(120, 120, 120), 1))
                    painter.setBrush(QBrush(QColor(240, 240, 240)))
                    painter.drawEllipse(3, 3, 10, 10)
                
                # 结束绘制
                painter.end()
                
                # 保存图标
                pixmap.save(file_path, "PNG")
                logger.info(f"创建默认图标: {file_path}")
                
            except Exception as e:
                logger.error(f"创建图标 {name} 失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
    
    def get_icon(self, name: str, size: int = 16) -> Optional[QIcon]:
        """
        获取指定名称的图标
        
        Args:
            name (str): 菜单项名称
            size (int): 图标大小
            
        Returns:
            QIcon: 图标对象，如果没有找到则返回None
        """
        # 处理空菜单项名称
        if not name or not name.strip():
            return None
        
        # 检查缓存
        cache_key = f"{name}_{size}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
            
        # 获取图标文件名
        filename = self._menu_icon_map.get(name)
        if filename is None:
            # 如果图标映射中显式设置为None，表示此项不需要图标
            logger.debug(f"此菜单项配置为不需要图标: {name}")
            return None
        elif not filename:
            # 尝试去除可能的前缀后再次查找
            clean_name = name.strip()
            # 处理可能的特殊字符前缀，如"□"或"■"
            if len(clean_name) > 1 and clean_name[0] in ["□", "■", " "]:
                # 先尝试去除前缀但保留整个名称
                clean_name = clean_name[1:]
                filename = self._menu_icon_map.get(clean_name)
                
                # 如果仍然找不到，则也去除可能的空格
                if not filename:
                    clean_name = clean_name.strip()
                    filename = self._menu_icon_map.get(clean_name)
            
            if not filename:
                # 找不到对应的图标
                logger.warning(f"找不到图标映射: {name}")
                return None
            
        # 在所有路径中寻找图标
        icon_path = None
        for path in self._icon_paths:
            temp_path = os.path.join(path, filename)
            if os.path.exists(temp_path):
                icon_path = temp_path
                break
                
        if not icon_path:
            logger.warning(f"找不到图标文件: {filename}")
            return None
            
        try:
            # 创建图标
            icon = QIcon(icon_path)
            if icon.isNull():
                logger.warning(f"创建图标失败: {icon_path}")
                return None
                
            # 添加到缓存
            self._icon_cache[cache_key] = icon
            return icon
            
        except Exception as e:
            logger.error(f"加载图标 {icon_path} 失败: {str(e)}")
            return None
            
    def apply_menu_icons(self, menu_bar):
        """
        为菜单栏中的所有菜单和菜单项应用图标
        
        Args:
            menu_bar: QMenuBar对象
        """
        try:
            # 修正：QMenuBar 使用 actions() 方法获取所有菜单，而不是 count()
            for action in menu_bar.actions():
                # 获取菜单名称
                menu_name = action.text()
                
                # 调试输出菜单项名称的精确表示
                logger.debug(f"菜单项名称: '{menu_name}', 长度: {len(menu_name)}, 十六进制表示: {menu_name.encode('utf-8').hex()}")
                
                # 跳过空菜单项
                if not menu_name or not menu_name.strip():
                    continue
                
                # 人员列表及其子菜单不需要图标
                clean_menu_name = menu_name.strip()
                if "人员列表" in clean_menu_name or clean_menu_name in ["高文彬", "石航", "徐国明", "石帆"]:
                    logger.debug(f"跳过人员列表相关项: {menu_name}")
                    continue
                
                # 应用菜单图标
                icon = self.get_icon(menu_name)
                if icon:
                    action.setIcon(icon)
                    logger.debug(f"成功应用图标: {menu_name}")
                else:
                    logger.debug(f"未找到图标: {menu_name}")
                    
                # 获取子菜单
                submenu = action.menu()
                if not submenu:
                    continue
                    
                # 遍历子菜单项
                for sub_action in submenu.actions():
                    action_name = sub_action.text()
                    
                    # 调试输出子菜单项名称的精确表示
                    logger.debug(f"子菜单项名称: '{action_name}', 长度: {len(action_name)}, 十六进制表示: {action_name.encode('utf-8').hex()}")
                    
                    # 跳过空菜单项
                    if not action_name or not action_name.strip():
                        continue
                    
                    # 人员列表项不需要图标
                    if action_name.strip() in ["高文彬", "石航", "徐国明", "石帆", "人员列表"]:
                        logger.debug(f"跳过人员列表相关项: {action_name}")
                        continue
                    
                    icon = self.get_icon(action_name)
                    if icon:
                        sub_action.setIcon(icon)
                        logger.debug(f"成功应用子菜单图标: {action_name}")
                    else:
                        logger.debug(f"未找到子菜单图标: {action_name}")
                        
        except Exception as e:
            logger.error(f"应用菜单图标时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def apply_context_menu_icons(self, menu):
        """
        为上下文菜单中的所有菜单项应用图标
        
        Args:
            menu: QMenu对象
        """
        try:
            # 遍历菜单中的所有操作
            for action in menu.actions():
                # 跳过分隔符
                if action.isSeparator():
                    continue
                    
                # 获取操作名称
                action_name = action.text()
                
                # 调试输出菜单项名称的精确表示
                logger.debug(f"上下文菜单项名称: '{action_name}', 长度: {len(action_name)}, 十六进制表示: {action_name.encode('utf-8').hex()}")
                
                # 跳过空菜单项
                if not action_name or not action_name.strip():
                    continue
                
                # 应用图标
                icon = self.get_icon(action_name)
                if icon:
                    action.setIcon(icon)
                    logger.debug(f"成功应用上下文菜单图标: {action_name}")
                else:
                    logger.debug(f"未找到上下文菜单图标: {action_name}")
                    
                # 处理子菜单
                submenu = action.menu()
                if submenu:
                    self.apply_context_menu_icons(submenu)
        except Exception as e:
            logger.error(f"应用上下文菜单图标时出错: {str(e)}") 