#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库测试数据生成脚本

向MySQL数据库中插入测试数据，包括用户、密码记录和密码修改历史
"""

import sys
import os
import random
import string
import datetime
import argparse
import logging
from datetime import timedelta
import pymysql
from pymysql.cursors import DictCursor
import traceback

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import DEFAULT_MYSQL_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(current_dir, 'insert_test_data.log'))
    ]
)
logger = logging.getLogger(__name__)

# 测试数据
TEST_OWNERS = ["徐国明", "高文彬", "石帆"]
TEST_PROJECTS = ["ERP系统", "OA系统", "CRM系统", "网站后台", "监控平台", "测试环境", "生产环境"]
TEST_AREAS = ["北京", "上海", "广州", "深圳", "成都", "杭州"]
TEST_NETWORK_TYPES = ["内网", "外网", "VPN"]

def generate_password(length=16):
    """生成随机密码"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?/"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_ip():
    """生成随机IP地址"""
    return f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"

def create_connection(db_config):
    """创建数据库连接"""
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4',
            cursorclass=DictCursor
        )
        logger.info(f"成功连接到数据库 {db_config['host']}:{db_config['port']}/{db_config['database']}")
        return connection
    except Exception as e:
        logger.error(f"连接数据库时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

def insert_users(connection, force=False):
    """插入测试用户"""
    users = [
        ("admin", "admin", 1),  # 管理员
        ("user1", "password1", 0),
        ("user2", "password2", 0),
        ("tester", "test123", 0)
    ]
    
    try:
        with connection.cursor() as cursor:
            # 检查表是否为空
            cursor.execute("SELECT COUNT(*) as count FROM users")
            count = cursor.fetchone()['count']
            
            if count > 0 and not force:
                logger.info(f"users表已有{count}条记录，跳过插入用户数据")
                return
            
            # 如果force为True且表中有数据，先清空表
            if count > 0 and force:
                logger.warning("强制模式：清空users表")
                cursor.execute("TRUNCATE TABLE users")
            
            # 插入用户
            for username, password, is_admin in users:
                cursor.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
                    (username, password, is_admin)
                )
            
            connection.commit()
            logger.info(f"成功插入{len(users)}个测试用户")
    except Exception as e:
        logger.error(f"插入用户数据时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        connection.rollback()

def insert_passwords(connection, num_records=None, force=False):
    """插入测试密码记录
    
    Args:
        connection: 数据库连接
        num_records: 为每个所有者生成的记录数量。如果为None，则随机生成10-20条
        force: 是否强制重新插入数据（清空表）
        
    Returns:
        dict: 所有者及其密码记录ID的映射
    """
    try:
        with connection.cursor() as cursor:
            # 检查表中是否已有数据
            cursor.execute("SELECT COUNT(*) as count FROM passwords")
            count = cursor.fetchone()['count']
            
            if count > 0 and not force:
                logger.info(f"passwords表已有{count}条记录，跳过插入")
                return {}
            
            # 如果force为True且表中有数据，先清空表
            if count > 0 and force:
                logger.warning("强制模式：清空passwords表")
                cursor.execute("TRUNCATE TABLE passwords")
            
            # 每个所有者创建指定或随机数量的记录
            password_records = []
            ids_by_owner = {}
            total_records = 0
            
            for owner in TEST_OWNERS:
                ids_by_owner[owner] = []
                record_count = num_records if num_records is not None else random.randint(10, 20)
                
                for _ in range(record_count):
                    project = random.choice(TEST_PROJECTS)
                    func_desc = f"{project}{random.choice(['登录账号', '管理员账号', '运维账号', 'API账号'])}"
                    ip = generate_ip()
                    account = f"admin_{random.randint(100, 999)}"
                    password = generate_password()
                    area = random.choice(TEST_AREAS)
                    network_type = random.choice(TEST_NETWORK_TYPES)
                    other_info = f"测试数据 - {datetime.datetime.now().strftime('%Y-%m-%d')}"
                    
                    cursor.execute(
                        """
                        INSERT INTO passwords 
                        (owner, project_name, func_desc, ip_address, account, password, area, network_type, other_info) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (owner, project, func_desc, ip, account, password, area, network_type, other_info)
                    )
                    
                    # 获取插入的ID
                    password_id = cursor.lastrowid
                    ids_by_owner[owner].append((password_id, ip, account, password))
                    password_records.append((owner, password_id))
                    total_records += 1
            
            connection.commit()
            logger.info(f"成功插入{total_records}条密码记录")
            
            # 返回插入的记录ID，以便创建历史记录
            return ids_by_owner
    except Exception as e:
        logger.error(f"插入密码记录时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        connection.rollback()
        return {}

def insert_password_history(connection, ids_by_owner, force=False):
    """插入密码历史记录"""
    if not ids_by_owner:
        logger.info("无密码记录，跳过创建历史记录")
        return
    
    try:
        with connection.cursor() as cursor:
            # 检查表中是否已有数据
            cursor.execute("SELECT COUNT(*) as count FROM password_history")
            count = cursor.fetchone()['count']
            
            if count > 0 and not force:
                logger.info(f"password_history表已有{count}条记录，跳过插入")
                return
            
            # 如果force为True且表中有数据，先清空表
            if count > 0 and force:
                logger.warning("强制模式：清空password_history表")
                cursor.execute("TRUNCATE TABLE password_history")
            
            total_history = 0
            
            # 为每个所有者的部分密码创建历史记录
            modify_users = ["admin", "user1", "user2", "tester", "system"]
            modify_reasons = ["定期更新", "安全审计", "密码泄露", "系统自动更新", ""]
            
            for owner, password_records in ids_by_owner.items():
                # 为30%-50%的密码创建历史记录
                sample_size = max(1, int(len(password_records) * random.uniform(0.3, 0.5)))
                sampled_records = random.sample(password_records, sample_size)
                
                for password_id, ip, account, current_password in sampled_records:
                    # 为每个密码创建1-5条历史记录
                    history_count = random.randint(1, 5)
                    
                    # 从当前密码开始，向前生成历史密码
                    new_password = current_password
                    
                    for i in range(history_count):
                        # 生成旧密码
                        old_password = generate_password()
                        
                        # 计算修改时间(从现在向前推)
                        days_ago = random.randint(i*30, i*30+29)  # 每30天左右更新一次
                        modify_time = datetime.datetime.now() - timedelta(days=days_ago)
                        
                        # 随机选择修改人和原因
                        modify_user = random.choice(modify_users)
                        modify_reason = random.choice(modify_reasons)
                        
                        cursor.execute(
                            """
                            INSERT INTO password_history 
                            (password_id, old_password, new_password, ip_address, modify_user, modify_reason, modify_time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (password_id, old_password, new_password, ip, modify_user, modify_reason, modify_time)
                        )
                        
                        # 当前密码变成下一条记录的新密码
                        new_password = old_password
                        total_history += 1
            
            connection.commit()
            logger.info(f"成功插入{total_history}条密码历史记录")
    except Exception as e:
        logger.error(f"插入密码历史记录时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        connection.rollback()

def insert_user_settings(connection, force=False):
    """插入用户设置数据"""
    try:
        with connection.cursor() as cursor:
            # 检查表中是否已有数据
            cursor.execute("SELECT COUNT(*) as count FROM user_settings")
            count = cursor.fetchone()['count']
            
            if count > 0 and not force:
                logger.info(f"user_settings表已有{count}条记录，跳过插入")
                return
            
            # 如果force为True且表中有数据，先清空表
            if count > 0 and force:
                logger.warning("强制模式：清空user_settings表")
                cursor.execute("TRUNCATE TABLE user_settings")
            
            # 插入用户设置示例
            settings_data = [
                ("admin", "guides.main_features", '{"completed": true}'),
                ("admin", "ui.table_font_size", '10'),
                ("admin", "ui.show_grid_lines", 'true'),
                ("user1", "guides.main_features", '{"completed": false}'),
                ("user1", "password.default_length", '12')
            ]
            
            for username, key, value in settings_data:
                cursor.execute(
                    """
                    INSERT INTO user_settings 
                    (username, setting_key, setting_value)
                    VALUES (%s, %s, %s)
                    """,
                    (username, key, value)
                )
            
            connection.commit()
            logger.info(f"成功插入{len(settings_data)}条用户设置记录")
    except Exception as e:
        logger.error(f"插入用户设置数据时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        connection.rollback()

def insert_audit_logs(connection, force=False):
    """插入审计日志测试数据"""
    try:
        with connection.cursor() as cursor:
            # 检查表中是否已有数据
            cursor.execute("SELECT COUNT(*) as count FROM audit_logs")
            count = cursor.fetchone()['count']
            
            if count > 0 and not force:
                logger.info(f"audit_logs表已有{count}条记录，跳过插入")
                return
            
            # 如果force为True且表中有数据，先清空表
            if count > 0 and force:
                logger.warning("强制模式：清空audit_logs表")
                cursor.execute("TRUNCATE TABLE audit_logs")
            
            # 审计日志测试数据
            usernames = ["admin", "user1", "user2", "tester"]
            operation_types = ["登录", "查询密码", "修改密码", "导出数据", "配置修改"]
            operation_results = ["成功", "失败"]
            log_types = ["用户操作", "系统事件", "安全审计"]
            
            # 为每个用户生成10-20条审计日志
            total_logs = 0
            
            for username in usernames:
                log_count = random.randint(10, 20)
                
                for _ in range(log_count):
                    operation_type = random.choice(operation_types)
                    operation_result = random.choice(operation_results)
                    log_type = random.choice(log_types)
                    
                    # 生成详细信息
                    if operation_type == "登录":
                        details = f"用户从IP {generate_ip()} 登录系统"
                    elif operation_type == "查询密码":
                        details = f"查询了项目 '{random.choice(TEST_PROJECTS)}' 的密码记录"
                    elif operation_type == "修改密码":
                        details = f"修改了项目 '{random.choice(TEST_PROJECTS)}' 的密码"
                    elif operation_type == "导出数据":
                        details = f"导出了 {random.randint(1, 20)} 条密码记录"
                    else:
                        details = f"修改了系统配置 '{random.choice(['界面设置', '数据库设置', '安全策略'])}'"
                    
                    # 生成随机时间（最近30天内）
                    days_ago = random.randint(0, 30)
                    created_at = datetime.datetime.now() - timedelta(days=days_ago, 
                                                                    hours=random.randint(0, 23),
                                                                    minutes=random.randint(0, 59),
                                                                    seconds=random.randint(0, 59))
                    
                    cursor.execute(
                        """
                        INSERT INTO audit_logs 
                        (username, operation_type, operation_result, log_type, details, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (username, operation_type, operation_result, log_type, details, created_at)
                    )
                    total_logs += 1
            
            connection.commit()
            logger.info(f"成功插入{total_logs}条审计日志记录")
    except Exception as e:
        logger.error(f"插入审计日志数据时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        connection.rollback()

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='插入密码管理器测试数据')
    parser.add_argument('--force', '-f', action='store_true', help='强制重新插入数据（清空现有表数据）')
    parser.add_argument('--records', '-r', type=int, help='每个用户插入的密码记录数量')
    parser.add_argument('--host', type=str, help='数据库主机')
    parser.add_argument('--port', type=int, help='数据库端口')
    parser.add_argument('--user', type=str, help='数据库用户名')
    parser.add_argument('--password', type=str, help='数据库密码')
    parser.add_argument('--database', type=str, help='数据库名称')
    parser.add_argument('--verbose', '-v', action='store_true', help='输出详细日志')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("开始插入测试数据...")
    
    # 配置数据库连接
    db_config = DEFAULT_MYSQL_CONFIG.copy()
    if args.host:
        db_config['host'] = args.host
    if args.port:
        db_config['port'] = args.port
    if args.user:
        db_config['user'] = args.user
    if args.password:
        db_config['password'] = args.password
    if args.database:
        db_config['database'] = args.database
    
    connection = create_connection(db_config)
    
    try:
        # 插入测试用户
        insert_users(connection, force=args.force)
        
        # 插入密码记录并获取IDs
        ids_by_owner = insert_passwords(connection, num_records=args.records, force=args.force)
        
        # 插入密码历史记录
        insert_password_history(connection, ids_by_owner, force=args.force)
        
        # 插入用户设置
        insert_user_settings(connection, force=args.force)
        
        # 插入审计日志
        insert_audit_logs(connection, force=args.force)
        
        logger.info("所有测试数据插入完成！")
    except Exception as e:
        logger.error(f"插入测试数据时出错: {str(e)}")
        logger.debug(traceback.format_exc())
    finally:
        connection.close()

if __name__ == "__main__":
    main() 