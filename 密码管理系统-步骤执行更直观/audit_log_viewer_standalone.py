#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
独立运行的审计日志查看器，提供单独启动审计日志查看功能
"""

import sys
import os
import json
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_audit_log_files():
    """初始化审计日志目录和文件，确保它们存在"""
    try:
        # 从配置中导入路径常量
        from config import LOG_DIR
        
        # 创建审计日志目录
        audit_log_dir = os.path.join(LOG_DIR, 'audit')
        if not os.path.exists(audit_log_dir):
            os.makedirs(audit_log_dir)
            logger.info(f"创建审计日志目录: {audit_log_dir}")
        
        # 检查系统审计日志文件
        system_log_file = os.path.join(audit_log_dir, 'system_audit.json')
        if not os.path.exists(system_log_file) or os.path.getsize(system_log_file) == 0:
            # 创建空的审计日志文件
            with open(system_log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            logger.info(f"创建空的系统审计日志文件: {system_log_file}")
        
        # 检查SSH审计日志文件
        ssh_log_file = os.path.join(audit_log_dir, 'ssh_audit.json')
        if not os.path.exists(ssh_log_file) or os.path.getsize(ssh_log_file) == 0:
            # 创建空的SSH审计日志文件
            with open(ssh_log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            logger.info(f"创建空的SSH审计日志文件: {ssh_log_file}")
        
        return True
    except Exception as e:
        logger.error(f"初始化审计日志文件时出错: {str(e)}")
        return False

def setup_qt_paths():
    """设置Qt插件路径，解决平台插件找不到的问题"""
    try:
        # 尝试设置可能有效的路径
        plugin_paths = [
            os.path.join(os.path.dirname(sys.executable), "Lib/site-packages/PyQt5/Qt5/plugins"),
            os.path.join(os.path.dirname(sys.executable), "Lib/site-packages/PyQt5/Qt/plugins"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv/Lib/site-packages/PyQt5/Qt5/plugins"),
        ]
        
        # 记录查找插件路径的尝试
        found_valid_path = False
        for path in plugin_paths:
            if os.path.exists(path):
                logger.info(f"找到Qt插件路径: {path}")
                os.environ["QT_PLUGIN_PATH"] = path
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(path, "platforms")
                found_valid_path = True
                break
        
        # 如果未找到有效路径，记录警告
        if not found_valid_path:
            logger.warning("未找到有效的Qt插件路径，可能会导致UI加载问题")
            
    except Exception as e:
        logger.error(f"设置Qt路径时出错: {str(e)}")

def main():
    """主函数，用于单独启动审计日志查看器"""
    try:
        # 设置Qt插件路径
        setup_qt_paths()
        
        # 初始化审计日志文件
        init_audit_log_files()
        
        # 导入PyQt5
        from PyQt5.QtWidgets import QApplication
        logger.info("成功导入PyQt5")
        
        # 导入审计日志查看器
        from audit_log_viewer import AuditLogViewer
        logger.info("成功导入AuditLogViewer")
        
        # 创建应用程序
        app = QApplication(sys.argv)
        
        # 创建并显示审计日志查看器
        viewer = AuditLogViewer()
        viewer.show()
        
        # 进入应用程序事件循环
        logger.info("启动事件循环")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"启动审计日志查看器时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 在控制台显示错误
        print(f"启动失败: {str(e)}")
        print("详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    print("启动审计日志查看器...")
    main() 