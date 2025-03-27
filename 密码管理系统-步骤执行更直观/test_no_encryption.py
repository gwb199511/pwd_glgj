#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试修改后的加密模块
确认数据以明文存储，但系统功能正常
"""

import os
import sys
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入项目模块
from encrypt import encryptor
from user import user_manager
from password import password_manager
from config import PASSWORD_DATA_FILE, USER_DATA_FILE

def test_encryption_removed():
    """测试加密功能已被移除"""
    logger.info("测试加密功能已被移除")
    
    # 测试加密函数
    test_data = "这是测试数据"
    encrypted = encryptor.encrypt(test_data)
    logger.info(f"原始数据: {test_data}")
    logger.info(f"加密后数据: {encrypted}")
    
    # 检查加密是否被移除（数据应保持不变）
    assert test_data == encrypted, "加密功能未正确移除，数据发生了变化"
    logger.info("✓ 加密功能已正确移除，数据保持不变")
    
    # 测试加密检测函数
    is_encrypted = encryptor.is_encrypted(encrypted)
    assert not is_encrypted, "is_encrypted函数未正确修改，应始终返回False"
    logger.info("✓ is_encrypted函数已正确修改，始终返回False")
    
    # 测试解密函数
    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == test_data, "解密功能未正确修改，数据发生了变化"
    logger.info("✓ 解密功能已正确修改，数据保持不变")
    
    logger.info("所有加密相关测试已通过，功能已正确移除")
    
def test_user_registration():
    """测试用户注册功能"""
    logger.info("测试用户注册功能")
    
    # 创建测试用户
    test_username = f"test_user_{os.urandom(4).hex()}"
    test_password = "test_password"
    
    # 注册用户
    success, message = user_manager.register(test_username, test_password)
    assert success, f"用户注册失败: {message}"
    logger.info(f"✓ 用户 {test_username} 注册成功")
    
    # 检查用户数据文件
    with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
    
    # 验证用户数据是否以明文存储
    assert test_username in user_data, f"用户 {test_username} 未在数据文件中找到"
    assert user_data[test_username] == test_password, "用户密码未以明文存储"
    logger.info("✓ 用户密码已正确以明文存储")
    
    # 测试登录
    login_success, login_message = user_manager.login(test_username, test_password)
    assert login_success, f"用户登录失败: {login_message}"
    logger.info("✓ 用户登录成功")
    
def test_password_storage():
    """测试密码记录存储"""
    logger.info("测试密码记录存储")
    
    # 创建测试用户
    test_owner = f"test_owner_{os.urandom(4).hex()}"
    
    # 创建测试密码记录
    test_record = [
        "测试项目",          # 项目名称
        "测试功能",          # 功能
        "192.168.1.1",      # IP地址
        "admin",            # 账户
        "secure_password",  # 密码
        "测试区域",          # 所在区域
        "内网",              # 网络类型
        "备注信息"           # 其他信息
    ]
    
    # 添加密码记录
    success, message = password_manager.add_password(test_owner, test_record)
    assert success, f"添加密码记录失败: {message}"
    logger.info(f"✓ 为用户 {test_owner} 添加密码记录成功")
    
    # 检查密码数据文件
    with open(PASSWORD_DATA_FILE, 'r', encoding='utf-8') as f:
        password_data = json.load(f)
    
    # 验证密码数据是否以明文存储
    assert test_owner in password_data, f"用户 {test_owner} 未在密码数据文件中找到"
    assert len(password_data[test_owner]) == 1, "密码记录数量不正确"
    
    # 验证密码字段是明文存储
    stored_record = password_data[test_owner][0]
    assert stored_record[4] == "secure_password", "密码未以明文存储"
    logger.info("✓ 密码已正确以明文存储")
    
    # 获取密码记录并验证
    records = password_manager.get_passwords_by_owner(test_owner)
    assert len(records) == 1, "获取的密码记录数量不正确"
    assert records[0][4] == "secure_password", "获取的密码不正确"
    logger.info("✓ 密码记录获取成功，值正确")
    
def main():
    """主函数"""
    logger.info("开始测试移除加密功能后的系统")
    
    # 测试加密功能移除
    test_encryption_removed()
    
    # 测试用户注册
    test_user_registration()
    
    # 测试密码存储
    test_password_storage()
    
    logger.info("所有测试已完成，系统正常工作且数据以明文存储")
    
if __name__ == "__main__":
    main() 