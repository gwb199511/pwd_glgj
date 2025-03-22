#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
审计日志功能测试脚本
"""

import os
import json
import logging
import traceback
from datetime import datetime

from audit_log import AuditLogger, OP_TYPE_LOGIN, OP_TYPE_LOGOUT, OP_RESULT_SUCCESS, OP_RESULT_FAIL
from config import LOG_DIR
from user import UserManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_audit_logging():
    """测试审计日志功能"""
    logger.info("开始测试审计日志功能")
    
    # 创建审计日志记录器
    audit_logger = AuditLogger()
    
    # 显示日志目录
    audit_log_dir = os.path.join(LOG_DIR, 'audit')
    system_log_file = os.path.join(audit_log_dir, 'system_audit.json')
    
    logger.info(f"审计日志目录: {audit_log_dir}")
    logger.info(f"系统审计日志文件: {system_log_file}")
    
    if os.path.exists(audit_log_dir):
        logger.info(f"审计日志目录存在")
    else:
        logger.error(f"审计日志目录不存在")
        # 尝试创建目录
        try:
            os.makedirs(audit_log_dir, exist_ok=True)
            logger.info(f"已创建审计日志目录: {audit_log_dir}")
        except Exception as e:
            logger.error(f"创建审计日志目录时出错: {str(e)}")
    
    # 测试登录审计日志
    logger.info("测试登录审计日志")
    try:
        result = audit_logger.log_operation(
            operation_type=OP_TYPE_LOGIN,
            result=OP_RESULT_SUCCESS,
            details="测试登录成功",
            user="test_user",
            target="用户认证"
        )
        logger.info(f"记录登录成功日志: {'成功' if result else '失败'}")
    except Exception as e:
        logger.error(f"记录登录成功日志时出错: {str(e)}")
        logger.error(traceback.format_exc())
    
    # 测试登录失败审计日志
    logger.info("测试登录失败审计日志")
    try:
        result = audit_logger.log_operation(
            operation_type=OP_TYPE_LOGIN,
            result=OP_RESULT_FAIL,
            details="测试登录失败 - 密码错误",
            user="test_user",
            target="用户认证"
        )
        logger.info(f"记录登录失败日志: {'成功' if result else '失败'}")
    except Exception as e:
        logger.error(f"记录登录失败日志时出错: {str(e)}")
        logger.error(traceback.format_exc())
    
    # 测试登出审计日志
    logger.info("测试登出审计日志")
    try:
        result = audit_logger.log_operation(
            operation_type=OP_TYPE_LOGOUT,
            result=OP_RESULT_SUCCESS,
            details="测试登出成功",
            user="test_user",
            target="用户认证"
        )
        logger.info(f"记录登出日志: {'成功' if result else '失败'}")
    except Exception as e:
        logger.error(f"记录登出日志时出错: {str(e)}")
        logger.error(traceback.format_exc())
    
    # 检查日志文件是否存在
    if os.path.exists(system_log_file):
        logger.info(f"审计日志文件存在: {system_log_file}")
        
        # 读取日志内容并显示
        try:
            with open(system_log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                
            logger.info(f"系统审计日志中有 {len(logs)} 条记录")
            
            # 显示最近的3条日志
            for i, log in enumerate(logs[-3:]):
                logger.info(f"日志 #{i+1}:")
                logger.info(f"  时间戳: {log.get('timestamp')}")
                logger.info(f"  用户: {log.get('user')}")
                logger.info(f"  操作: {log.get('operation')}")
                logger.info(f"  结果: {log.get('result')}")
                logger.info(f"  详情: {log.get('details')}")
                logger.info("---")
        except Exception as e:
            logger.error(f"读取审计日志时出错: {str(e)}")
            logger.error(traceback.format_exc())
    else:
        logger.error(f"审计日志文件不存在: {system_log_file}")
        
        # 列出日志目录中的文件
        try:
            files = os.listdir(audit_log_dir)
            logger.info(f"审计日志目录中的文件: {files}")
        except Exception as e:
            logger.error(f"列出审计日志目录内容时出错: {str(e)}")

if __name__ == "__main__":
    test_audit_logging() 