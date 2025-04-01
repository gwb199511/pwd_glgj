#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件，定义系统常量和配置参数
"""

import os
import logging
from datetime import datetime

# 基本路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 数据文件路径
ENCRYPTION_KEY_FILE = os.path.join(DATA_DIR, 'encryption.key')
DB_CONFIG_FILE = os.path.join(DATA_DIR, 'db_config.json')

# 确保目录存在
for directory in [DATA_DIR, LOG_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# 密码表格配置
PASSWORD_COLUMNS = [
    "项目名称", "功能", "IP地址", "账户", "密码", "所在区域", "网络类型", "其他账号"
]
REQUIRED_FIELDS = [0, 2, 3, 4]  # 项目名称、IP地址、账户、密码为必填字段

# UI配置
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
FONT_FAMILY = "Microsoft YaHei"
REMEMBER_EXPIRE_DAYS = 30

# 颜色配置
COLORS = {
    "primary": "#4a6fa5",
    "secondary": "#6c757d",
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8",
    "light": "#f8f9fa",
    "dark": "#343a40",
    "bg_light": "#f5f5f5",
    "text_dark": "#212529",
    "border": "#dee2e6"
}

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(LOG_DIR, f'app_{datetime.now().strftime("%Y%m%d")}.log')

# 加密配置
ENCRYPTION_ENCODING = 'utf-8'
ENCRYPTION_PREFIX = 'gAAAAAB'  # Fernet加密数据的前缀

# 数据库配置
DEFAULT_MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "password_manager"
}

# 版本信息
VERSION = "1.0.0"
BUILD_DATE = "2024-03-01" 