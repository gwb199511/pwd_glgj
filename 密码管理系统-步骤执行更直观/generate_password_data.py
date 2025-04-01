#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成密码表测试数据脚本
"""

import random
import string
import logging
import argparse
from typing import List, Dict, Any
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入数据库管理器
from db_manager import db_manager

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
    "Office365", "阿里云", "腾讯云", "华为云", "AWS"
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

# 固定所有者列表
owners = ["徐国明", "高文彬", "石帆", "admin"]

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

def generate_random_record(owner: str) -> Dict[str, Any]:
    """生成一条随机密码记录"""
    record = {
        "owner": owner,
        "project_name": random.choice(project_names),
        "func_desc": random.choice(function_descriptions),
        "ip_address": generate_random_ip(),
        "account": generate_random_username(),
        "password": generate_random_password(),
        "area": random.choice(areas),
        "network_type": random.choice(network_types),
        "other_info": f"备用账号: {generate_random_username()}"
    }
    return record

def insert_record_to_db(record: Dict[str, Any]) -> bool:
    """将记录插入到数据库"""
    sql = """
    INSERT INTO passwords 
    (owner, project_name, func_desc, ip_address, account, password, area, network_type, other_info) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        record["owner"],
        record["project_name"],
        record["func_desc"],
        record["ip_address"],
        record["account"],
        record["password"],
        record["area"],
        record["network_type"],
        record["other_info"]
    )
    result = db_manager.execute_insert(sql, params)
    return result > 0

def generate_data_for_owner(owner: str, count: int) -> int:
    """为指定所有者生成指定数量的记录"""
    success_count = 0
    for _ in range(count):
        record = generate_random_record(owner)
        if insert_record_to_db(record):
            success_count += 1
    return success_count

def get_current_record_count(owner: str = None) -> int:
    """获取当前记录数量"""
    if owner:
        sql = "SELECT COUNT(*) as count FROM passwords WHERE owner = %s"
        result = db_manager.execute_query(sql, (owner,))
    else:
        sql = "SELECT COUNT(*) as count FROM passwords"
        result = db_manager.execute_query(sql)
    
    if result and len(result) > 0:
        return result[0]['count']
    return 0

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成密码表测试数据')
    parser.add_argument('--count', type=int, default=10, help='每个所有者生成的记录数量 (默认: 10)')
    parser.add_argument('--owner', type=str, default=None, help='指定所有者 (默认: 为所有所有者生成数据)')
    parser.add_argument('--clear', action='store_true', help='清除现有数据 (默认: False)')
    args = parser.parse_args()
    
    try:
        # 连接数据库
        success, message = db_manager.connect()
        if not success:
            logger.error(f"连接数据库失败: {message}")
            return
        
        logger.info("已连接到数据库")
        
        # 如果需要清除现有数据
        if args.clear:
            confirm = input("确定要清除所有密码记录吗? (y/n): ")
            if confirm.lower() == 'y':
                db_manager.execute_update("DELETE FROM passwords")
                logger.info("已清除所有密码记录")
        
        # 确定要生成数据的所有者列表
        target_owners = [args.owner] if args.owner else owners
        
        # 获取当前记录数量
        total_records = get_current_record_count()
        logger.info(f"数据库中当前共有 {total_records} 条密码记录")
        
        # 为每个所有者生成记录
        total_generated = 0
        for owner in target_owners:
            current_count = get_current_record_count(owner)
            logger.info(f"所有者 {owner} 当前有 {current_count} 条记录")
            
            # 生成记录
            success_count = generate_data_for_owner(owner, args.count)
            logger.info(f"为所有者 {owner} 成功生成了 {success_count} 条记录")
            total_generated += success_count
        
        logger.info(f"总共生成了 {total_generated} 条密码记录")
        
    except Exception as e:
        logger.error(f"生成数据时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # 断开数据库连接
        db_manager.disconnect()

if __name__ == "__main__":
    main() 