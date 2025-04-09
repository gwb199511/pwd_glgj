#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用正确字段名向passwords表插入测试数据
"""

import random
import string
import logging
import os
import json
import time
import pymysql

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 项目名称列表
project_names = [
    "OA系统", "ERP系统", "CRM系统", "HR系统", "财务系统", 
    "邮件服务器", "文件服务器", "数据库服务器", "Web服务器", "监控系统",
    "防火墙", "路由器", "交换机", "VPN", "堡垒机"
]

# 功能描述列表
function_descriptions = [
    "系统管理", "用户管理", "数据管理", "配置管理", "监控告警",
    "日志审计", "备份恢复", "安全管控", "运维支持", "开发测试"
]

# 区域列表
areas = [
    "北京总部", "上海分公司", "广州分公司", "深圳分公司", "成都分公司"
]

# 网络类型列表
network_types = [
    "互联网", "内网", "政务外网", "金融内网", "专线网络"
]

def generate_random_ip():
    """生成随机IP地址"""
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def generate_random_username():
    """生成随机用户名"""
    return f"user{random.randint(1, 99)}"

def generate_random_password():
    """生成随机密码"""
    return f"Password{random.randint(100, 999)}!"

def main():
    """主函数"""
    try:
        # 加载数据库配置
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'db_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            db_config = json.load(f)
            
        logger.info(f"数据库配置: 主机={db_config['host']}, 端口={db_config['port']}, 数据库={db_config['database']}")
        
        # 连接数据库
        conn = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4',
            connect_timeout=5
        )
        
        logger.info("数据库连接成功")
        
        try:
            with conn.cursor() as cursor:
                # 所有者列表
                owners = ["徐国明", "高文彬", "石帆"]
                
                # 为每个所有者生成测试数据
                for owner in owners:
                    # 查询当前记录数
                    cursor.execute("SELECT COUNT(*) FROM passwords WHERE owner = %s", (owner,))
                    current_count = cursor.fetchone()[0]
                    logger.info(f"{owner} 当前有 {current_count} 条密码记录")
                    
                    # 计算需要添加的记录数
                    target_total = 30  # 简化为固定值10条
                    if current_count >= target_total:
                        logger.info(f"{owner} 已有足够记录，跳过")
                        continue
                    
                    add_count = target_total - current_count
                    logger.info(f"将为 {owner} 添加 {add_count} 条记录")
                    
                    # 插入记录
                    success_count = 0
                    for i in range(add_count):
                        try:
                            # 使用正确的字段名
                            cursor.execute("""
                                INSERT INTO passwords 
                                (owner, project_name, func_desc, ip_address, account, password, area, network_type, other_info, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                owner,
                                random.choice(project_names),
                                random.choice(function_descriptions),
                                generate_random_ip(),
                                generate_random_username(),
                                generate_random_password(),
                                random.choice(areas),
                                random.choice(network_types),
                                f"备用账号: {generate_random_username()}"
                            ))
                            conn.commit()
                            success_count += 1
                            logger.info(f"成功插入第 {i+1}/{add_count} 条记录")
                            # 添加短暂延迟，避免插入太快
                            time.sleep(0.1)
                            
                        except Exception as e:
                            conn.rollback()
                            logger.error(f"插入第 {i+1} 条记录失败: {str(e)}")
                    
                    logger.info(f"为 {owner} 成功添加了 {success_count} 条密码记录")
                
                logger.info("测试数据生成完成")
                
        finally:
            conn.close()
            logger.info("数据库连接已关闭")
            
    except Exception as e:
        logger.error(f"生成测试数据时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 