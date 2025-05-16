#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动脚本，解决路径编码问题
"""

import os
import sys
import subprocess
import traceback
import logging
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"已添加项目根目录到Python路径: {project_root}")

# 定义日志目录和文件
LOG_DIR = os.path.join(project_root, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
LOG_FILE = os.path.join(LOG_DIR, f'run_{datetime.now().strftime("%Y%m%d")}.log')

# 配置基本日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    主函数，启动密码管理系统
    """
    try:
        # 在生产环境中注释掉调试代码
        # os.environ["QT_DEBUG_PLUGINS"] = "1"  # 启用Qt插件调试
        
        # 尝试设置可能有效的路径
        plugin_paths = [
            # 虚拟环境中的Qt插件路径
            os.path.join(project_root, "venv", "Lib", "site-packages", "PyQt5", "Qt5", "plugins"),
            os.path.normpath(os.path.join(project_root, "venv/Lib/site-packages/PyQt5/Qt5/plugins")),
        ]
        
        # 动态添加PyQt5路径
        try:
            import PyQt5
            qt5_plugin_path = os.path.join(PyQt5.__path__[0], 'Qt5', 'plugins')
            if qt5_plugin_path not in plugin_paths:
                plugin_paths.append(qt5_plugin_path)
                logger.info(f"从PyQt5模块添加插件路径: {qt5_plugin_path}")
        except Exception as e:
            logger.warning(f"获取PyQt5插件路径时出错: {str(e)}")
        
        # 记录查找插件路径的尝试
        found_valid_path = False
        for path in plugin_paths:
            if os.path.exists(path):
                platforms_path = os.path.join(path, "platforms")
                if os.path.exists(platforms_path) and any(f.endswith('.dll') for f in os.listdir(platforms_path)):
                    logger.info(f"找到Qt插件路径: {path}")
                    os.environ["QT_PLUGIN_PATH"] = path
                    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms_path
                    found_valid_path = True
                    break
                else:
                    logger.debug(f"插件路径存在但没有平台插件: {path}")
            else:
                logger.debug(f"尝试的插件路径不存在: {path}")
        
        # 如果未找到有效路径，记录警告
        if not found_valid_path:
            logger.warning("未找到有效的Qt插件路径，可能会导致UI加载问题")
        
        # 获取python解释器路径
        python_path = sys.executable
        logger.info(f"Python解释器路径: {python_path}")
        
        # 获取main.py的绝对路径
        main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
        logger.info(f"主脚本路径: {main_script}")
        
        # 使用subprocess启动应用程序
        logger.info("正在启动应用程序...")
        result = subprocess.call([python_path, main_script])
        logger.info(f"应用程序退出，返回代码: {result}")
        
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        logger.error(traceback.format_exc())
        # 向用户显示错误信息
        print(f"启动失败: {str(e)}\n请检查日志文件获取详细信息。")

if __name__ == "__main__":
    main() 