#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成测试数据脚本，为三个固定人员生成随机密码记录
"""

import random
import string
import logging
from typing import List, Dict, Any
import os
import sys

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入项目模块
from password import password_manager

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 项目名称列表
project_names = [
    "OA系统", "ERP系统", "CRM系统", "HR系统", "财务系统", 
    "邮件服务器", "文件服务器", "数据库服务器", "Web服务器", "监控系统",
    "防火墙", "路由器", "交换机", "VPN", "堡垒机",
    "备份系统", "域控制器", "打印服务器", "办公电脑", "笔记本电脑",
    "门禁系统", "考勤系统", "视频会议", "即时通讯", "项目管理系统",
    "Git仓库", "Jenkins", "Zabbix", "Kubernetes", "Docker",
    "MySQL", "Oracle", "SQL Server", "PostgreSQL", "MongoDB",
    "Redis", "Elasticsearch", "Nginx", "Apache", "Tomcat",
    "Windows Server", "CentOS", "Ubuntu", "Debian", "RHEL",
    "Office365", "阿里云", "腾讯云", "华为云", "AWS",
    "Azure", "政务外网", "互联网", "内网", "专线"
]

# 功能描述列表
function_descriptions = [
    "系统管理", "用户管理", "数据管理", "配置管理", "监控告警",
    "日志审计", "备份恢复", "安全管控", "运维支持", "开发测试",
    "生产环境", "测试环境", "开发环境", "灾备环境", "培训环境",
    "数据库管理", "应用管理", "网络管理", "存储管理", "虚拟化管理",
    "容器管理", "中间件管理", "安全设备管理", "终端管理", "账号管理",
    "权限管理", "密钥管理", "证书管理", "漏洞管理", "补丁管理"
]

# 区域列表
areas = [
    "北京总部", "上海分公司", "广州分公司", "深圳分公司", "成都分公司",
    "武汉分公司", "西安分公司", "南京分公司", "杭州分公司", "重庆分公司",
    "天津分公司", "长沙分公司", "青岛分公司", "大连分公司", "厦门分公司",
    "数据中心一区", "数据中心二区", "灾备中心", "云平台", "边缘节点"
]

# 网络类型列表
network_types = [
    "互联网", "内网", "政务外网", "金融内网", "专线网络",
    "VPN网络", "DMZ区", "管理网", "存储网", "备份网",
    "办公网", "生产网", "测试网", "开发网", "物联网"
]

def generate_random_ip() -> str:
    """生成随机IP地址"""
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def generate_random_username() -> str:
    """生成随机用户名"""
    username_types = [
        lambda: f"admin{random.randint(1, 999)}",
        lambda: f"user{random.randint(1, 999)}",
        lambda: f"root{random.randint(1, 99)}",
        lambda: f"sysadmin{random.randint(1, 99)}",
        lambda: f"operator{random.randint(1, 99)}",
        lambda: ''.join(random.choice(string.ascii_lowercase) for _ in range(6))
    ]
    return random.choice(username_types)()

def generate_random_password() -> str:
    """生成随机密码"""
    password_types = [
        # 简单密码
        lambda: f"password{random.randint(1, 999)}",
        lambda: f"admin{random.randint(1, 999)}",
        lambda: f"P@ssw0rd{random.randint(1, 99)}",
        # 复杂密码
        lambda: ''.join(random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(12)),
        lambda: ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10)),
        # 特殊格式密码
        lambda: f"{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_lowercase) * 5}{random.randint(100, 999)}!",
        lambda: f"Aa@{''.join(random.choice(string.digits) for _ in range(6))}"
    ]
    return random.choice(password_types)()

def generate_random_record() -> List[str]:
    """生成一条随机密码记录"""
    record = [
        random.choice(project_names),                        # 项目名称
        random.choice(function_descriptions),                # 功能
        generate_random_ip(),                               # IP地址
        generate_random_username(),                         # 账户
        generate_random_password(),                         # 密码
        random.choice(areas),                               # 所在区域
        random.choice(network_types),                       # 网络类型
        f"备用账号: {generate_random_username()}"           # 其他账号
    ]
    return record

def generate_records_for_user(owner: str, count: int) -> None:
    """为指定用户生成多条记录"""
    success_count = 0
    for _ in range(count):
        record = generate_random_record()
        success, message = password_manager.add_password(owner, record)
        if success:
            success_count += 1
        else:
            logger.error(f"为 {owner} 添加记录失败: {message}")
    
    logger.info(f"为 {owner} 成功添加了 {success_count} 条密码记录")

def main():
    """主函数"""
    try:
        # 获取所有者列表
        owners = ["徐国明", "高文彬", "石帆"]
        
        # 检查现有记录数
        current_counts = {}
        for owner in owners:
            passwords = password_manager.get_passwords_by_owner(owner)
            current_counts[owner] = len(passwords)
            logger.info(f"{owner} 当前有 {current_counts[owner]} 条密码记录")
        
        # 为每个人员生成随机记录
        for owner in owners:
            # 随机生成30-50条记录，减去已有记录数
            target_total = random.randint(30, 50)
            current_count = current_counts.get(owner, 0)
            
            # 如果已有记录数超过目标，则不添加
            if current_count >= target_total:
                logger.info(f"{owner} 已有 {current_count} 条记录，不需要添加")
                continue
                
            # 计算需要添加的记录数
            add_count = target_total - current_count
            logger.info(f"将为 {owner} 添加 {add_count} 条记录，目标总数: {target_total}")
            
            # 生成记录
            generate_records_for_user(owner, add_count)
            
        logger.info("随机数据生成完成")
        
    except Exception as e:
        logger.error(f"生成随机数据时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 