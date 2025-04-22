#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
审计日志模块，提供系统操作日志记录和查询功能
"""

import os
import json
import logging
import threading
import time
import queue
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

from config import LOG_DIR, DATA_DIR
from core.db_manager import db_manager

# 配置日志
logger = logging.getLogger(__name__)

# 审计日志类型
LOG_TYPE_SYSTEM = "system"  # 系统操作日志
LOG_TYPE_SSH = "ssh"        # SSH更新日志
LOG_TYPE_LOGIN = "login"    # 登录记录日志
LOG_TYPE_ALL = "all"        # 所有日志

# 操作类型
OP_TYPE_LOGIN = "login"           # 登录
OP_TYPE_LOGOUT = "logout"         # 登出
OP_TYPE_QUERY = "query"           # 查询
OP_TYPE_ADD = "add"               # 添加
OP_TYPE_UPDATE = "update"         # 更新
OP_TYPE_DELETE = "delete"         # 删除
OP_TYPE_GENERATE = "generate"     # 生成
OP_TYPE_SSH_UPDATE = "ssh_update" # SSH更新
OP_TYPE_EXPORT = "export"         # 导出
OP_TYPE_IMPORT = "import"         # 导入

# 操作结果
OP_RESULT_SUCCESS = "success"     # 成功
OP_RESULT_FAIL = "fail"           # 失败
OP_RESULT_WARNING = "warning"     # 警告
OP_RESULT_INFO = "info"           # 信息

class AuditLogger:
    """
    审计日志记录器，提供记录和查询系统操作日志的功能
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """
        单例模式，确保日志记录器只有一个实例
        
        Returns:
            AuditLogger: 日志记录器实例
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AuditLogger, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """初始化审计日志记录器"""
        with self.__class__._lock:
            if not self._initialized:
                # 确保审计日志表存在
                self._ensure_audit_table()
                
                # 初始化缓存
                self.cache = {}
                self.cache_time = {}
                self.cache_expiry = 60  # 缓存有效期(秒)
                
                # 初始化日志队列和工作线程
                self.log_queue = queue.Queue()
                self.batch_size = 10  # 批量处理的日志数量
                self.flush_interval = 5  # 强制刷新间隔（秒）
                self.last_flush_time = time.time()
                self.worker_thread = threading.Thread(target=self._log_worker, daemon=True)
                self.worker_thread.start()
                
                self._initialized = True
    
    def _ensure_audit_table(self):
        """确保审计日志表存在"""
        try:
            # 检查audit_logs表是否存在
            check_table_sql = "SHOW TABLES LIKE 'audit_logs'"
            tables = db_manager.execute_query(check_table_sql)
            
            if not tables:
                logger.info("audit_logs表不存在，将创建表")
                # 创建表
                create_table_sql = """
                CREATE TABLE `audit_logs` (
                  `id` bigint NOT NULL AUTO_INCREMENT,
                  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                  `operation_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                  `operation_result` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                  `log_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
                  `details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
                  `target` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
                  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`) USING BTREE,
                  INDEX `username`(`username` ASC) USING BTREE,
                  INDEX `created_at`(`created_at` ASC) USING BTREE
                ) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;
                """
                db_manager.execute_update(create_table_sql)
                logger.info("成功创建audit_logs表")
            else:
                # 检查是否需要添加target字段
                check_column_sql = "SHOW COLUMNS FROM `audit_logs` LIKE 'target'"
                target_column = db_manager.execute_query(check_column_sql)
                
                if not target_column:
                    logger.info("audit_logs表缺少target字段，将添加该字段")
                    add_column_sql = "ALTER TABLE `audit_logs` ADD COLUMN `target` varchar(255) NULL AFTER `details`"
                    db_manager.execute_update(add_column_sql)
                    logger.info("成功添加target字段到audit_logs表")
        except Exception as e:
            logger.error(f"确保audit_logs表存在时出错: {str(e)}")
    
    def _log_worker(self):
        """
        日志工作线程，异步处理日志队列
        """
        while True:
            try:
                # 收集批量日志
                logs_batch = []
                current_time = time.time()
                flush_timeout = current_time - self.last_flush_time >= self.flush_interval
                
                # 从队列中获取尽可能多的日志条目，直到达到批量大小或队列为空
                while len(logs_batch) < self.batch_size:
                    try:
                        log_entry = self.log_queue.get(block=not logs_batch, timeout=0.1)
                        logs_batch.append(log_entry)
                        self.log_queue.task_done()
                    except queue.Empty:
                        # 队列为空，跳出循环
                        break
                
                # 如果收集到了日志或者到了强制刷新时间
                if logs_batch or flush_timeout:
                    if logs_batch:
                        self._batch_write_logs(logs_batch)
                    self.last_flush_time = time.time()
                
                # 如果队列为空，稍微等待一下再继续
                if self.log_queue.empty():
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"日志工作线程出错: {str(e)}")
                time.sleep(1)  # 出错后等待1秒再继续
    
    def _batch_write_logs(self, log_entries):
        """
        批量写入日志到数据库
        
        Args:
            log_entries (List[Dict]): 日志条目列表
            
        Returns:
            bool: 写入成功返回True，否则返回False
        """
        try:
            if not log_entries:
                return True
                
            # 准备批量插入SQL和参数
            sql = """
                INSERT INTO audit_logs 
                (username, operation_type, operation_result, log_type, details, target) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params_list = []
            for entry in log_entries:
                params_list.append((
                    entry.get('user', '未知用户'),
                    entry.get('operation', ''),
                    entry.get('result', ''),
                    entry.get('log_type', LOG_TYPE_SYSTEM),
                    entry.get('details', ''),
                    entry.get('target', '')
                ))
            
            # 批量插入数据库
            result = db_manager.execute_batch(sql, params_list)
            
            if result:
                logger.debug(f"成功批量插入 {len(log_entries)} 条审计日志")
                return True
            else:
                logger.warning(f"批量插入审计日志失败")
                return False
                
        except Exception as e:
            logger.error(f"批量写入审计日志时出错: {str(e)}")
            return False
            
    def log_operation(self, 
                      operation_type: str, 
                      result: str, 
                      details: str,
                      user: Optional[str] = None, 
                      target: Optional[str] = None,
                      log_type: str = LOG_TYPE_SYSTEM) -> bool:
        """
        记录操作日志
        
        Args:
            operation_type (str): 操作类型
            result (str): 操作结果
            details (str): 详细信息
            user (Optional[str]): 操作用户，如果为None则使用当前登录用户
            target (Optional[str]): 操作目标，例如"密码记录", "用户账户"等
            log_type (str): 日志类型，默认为系统日志
            
        Returns:
            bool: 记录成功返回True，否则返回False
        """
        try:
            # 获取当前用户 - 避免循环导入
            if user is None:
                # 动态导入以避免循环引用
                from core.user import user_manager
                user = user_manager.get_current_user() or "未知用户"
            
            # 创建日志条目
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user": user,
                "operation": operation_type,
                "result": result,
                "target": target or "未指定",
                "details": details,
                "log_type": log_type
            }
            
            # 将日志条目添加到队列中异步处理
            self.log_queue.put(log_entry)
            
            return True
        
        except Exception as e:
            logger.error(f"记录审计日志时出错: {str(e)}")
            return False
    
    def get_logs(self, 
                 log_type: str = LOG_TYPE_SYSTEM, 
                 start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None,
                 operation_types: Optional[List[str]] = None,
                 users: Optional[List[str]] = None,
                 results: Optional[List[str]] = None,
                 keyword: Optional[str] = None,
                 limit: int = 1000,
                 offset: int = 0) -> List[Dict[str, Any]]:
        """
        从数据库查询日志
        
        Args:
            log_type (str): 日志类型
            start_time (Optional[datetime]): 开始时间
            end_time (Optional[datetime]): 结束时间
            operation_types (Optional[List[str]]): 操作类型列表
            users (Optional[List[str]]): 用户列表
            results (Optional[List[str]]): 结果类型列表
            keyword (Optional[str]): 关键词搜索
            limit (int): 限制返回的记录数
            offset (int): 偏移量，用于分页
            
        Returns:
            List[Dict[str, Any]]: 日志条目列表
        """
        try:
            # 生成缓存键
            cache_key = f"{log_type}_{start_time}_{end_time}_{operation_types}_{users}_{results}_{keyword}_{limit}_{offset}"
            
            # 检查是否有缓存
            if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < self.cache_expiry:
                return self.cache[cache_key]
            
            # 构建SQL查询
            sql_parts = ["SELECT * FROM audit_logs WHERE 1=1"]
            params = []
            
            # 添加日志类型条件
            if log_type != LOG_TYPE_ALL:
                sql_parts.append("AND log_type = %s")
                params.append(log_type)
            
            # 添加时间范围条件
            if start_time:
                sql_parts.append("AND created_at >= %s")
                params.append(start_time.strftime('%Y-%m-%d %H:%M:%S'))
            
            if end_time:
                sql_parts.append("AND created_at <= %s")
                params.append(end_time.strftime('%Y-%m-%d %H:%M:%S'))
            
            # 添加操作类型条件
            if operation_types and len(operation_types) > 0:
                placeholders = ', '.join(['%s'] * len(operation_types))
                sql_parts.append(f"AND operation_type IN ({placeholders})")
                params.extend(operation_types)
            
            # 添加用户条件
            if users and len(users) > 0:
                placeholders = ', '.join(['%s'] * len(users))
                sql_parts.append(f"AND username IN ({placeholders})")
                params.extend(users)
            
            # 添加结果条件
            if results and len(results) > 0:
                placeholders = ', '.join(['%s'] * len(results))
                sql_parts.append(f"AND operation_result IN ({placeholders})")
                params.extend(results)
            
            # 添加关键词搜索条件
            if keyword:
                sql_parts.append("AND (details LIKE %s OR target LIKE %s OR username LIKE %s OR operation_type LIKE %s)")
                keyword_param = f"%{keyword}%"
                params.extend([keyword_param, keyword_param, keyword_param, keyword_param])
            
            # 添加排序、分页条件
            sql_parts.append("ORDER BY created_at DESC")
            sql_parts.append("LIMIT %s OFFSET %s")
            params.append(limit)
            params.append(offset)
            
            # 组合最终SQL
            sql = " ".join(sql_parts)
            
            # 执行查询
            logs = db_manager.execute_query(sql, params)
            
            # 转换为标准格式
            formatted_logs = []
            for log in logs:
                formatted_log = {
                    "timestamp": log.get("created_at").isoformat() if isinstance(log.get("created_at"), datetime) else log.get("created_at"),
                    "user": log.get("username"),
                    "operation": log.get("operation_type"),
                    "result": log.get("operation_result"),
                    "target": log.get("target"),
                    "details": log.get("details"),
                    "log_type": log.get("log_type")
                }
                formatted_logs.append(formatted_log)
            
            # 更新缓存
            self.cache[cache_key] = formatted_logs
            self.cache_time[cache_key] = time.time()
            
            return formatted_logs
            
        except Exception as e:
            logger.error(f"获取审计日志时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def get_statistics(self, 
                       log_type: str = LOG_TYPE_SYSTEM,
                       days: int = 30) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Args:
            log_type (str): 日志类型
            days (int): 统计天数
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 确定时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
            
            stats = {
                "total": 0,
                "by_result": {},
                "by_operation": {},
                "by_user": {},
                "by_day": {}
            }
            
            # 构建基础条件
            base_condition = "log_type = %s AND created_at BETWEEN %s AND %s"
            base_params = [log_type, start_time_str, end_time_str]
            
            if log_type == LOG_TYPE_ALL:
                base_condition = "created_at BETWEEN %s AND %s"
                base_params = [start_time_str, end_time_str]
            
            # 获取总数
            count_sql = f"SELECT COUNT(*) AS count FROM audit_logs WHERE {base_condition}"
            count_result = db_manager.execute_query(count_sql, base_params)
            if count_result:
                stats["total"] = count_result[0].get("count", 0)
            
            # 按结果统计
            result_sql = f"""
                SELECT operation_result, COUNT(*) AS count 
                FROM audit_logs 
                WHERE {base_condition}
                GROUP BY operation_result
            """
            result_stats = db_manager.execute_query(result_sql, base_params)
            for row in result_stats:
                stats["by_result"][row.get("operation_result", "unknown")] = row.get("count", 0)
            
            # 按操作类型统计
            op_sql = f"""
                SELECT operation_type, COUNT(*) AS count 
                FROM audit_logs 
                WHERE {base_condition}
                GROUP BY operation_type
            """
            op_stats = db_manager.execute_query(op_sql, base_params)
            for row in op_stats:
                stats["by_operation"][row.get("operation_type", "unknown")] = row.get("count", 0)
            
            # 按用户统计
            user_sql = f"""
                SELECT username, COUNT(*) AS count 
                FROM audit_logs 
                WHERE {base_condition}
                GROUP BY username
                ORDER BY count DESC
                LIMIT 10
            """
            user_stats = db_manager.execute_query(user_sql, base_params)
            for row in user_stats:
                stats["by_user"][row.get("username", "unknown")] = row.get("count", 0)
            
            # 按天统计
            day_sql = f"""
                SELECT DATE(created_at) AS day, COUNT(*) AS count 
                FROM audit_logs 
                WHERE {base_condition}
                GROUP BY DATE(created_at)
                ORDER BY day
            """
            day_stats = db_manager.execute_query(day_sql, base_params)
            for row in day_stats:
                day_str = row.get("day").strftime("%Y-%m-%d") if isinstance(row.get("day"), datetime) else str(row.get("day"))
                stats["by_day"][day_str] = row.get("count", 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取审计日志统计信息时出错: {str(e)}")
            return {
                "total": 0,
                "by_result": {},
                "by_operation": {},
                "by_user": {},
                "by_day": {},
                "error": str(e)
            }

    def get_time_range_options(self) -> List[Dict[str, Any]]:
        """
        获取时间范围选项列表
        
        Returns:
            List[Dict[str, Any]]: 时间范围选项列表
        """
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
        
        return [
            {
                "name": "今天",
                "start_time": today_start,
                "end_time": now
            },
            {
                "name": "昨天",
                "start_time": today_start - timedelta(days=1),
                "end_time": today_start - timedelta(seconds=1)
            },
            {
                "name": "本周",
                "start_time": today_start - timedelta(days=now.weekday()),
                "end_time": now
            },
            {
                "name": "上周",
                "start_time": today_start - timedelta(days=now.weekday() + 7),
                "end_time": today_start - timedelta(days=now.weekday() + 1) - timedelta(seconds=1)
            },
            {
                "name": "本月",
                "start_time": datetime(now.year, now.month, 1),
                "end_time": now
            },
            {
                "name": "上月",
                "start_time": datetime(now.year, now.month - 1, 1) if now.month > 1 else datetime(now.year - 1, 12, 1),
                "end_time": datetime(now.year, now.month, 1) - timedelta(seconds=1)
            },
            {
                "name": "最近7天",
                "start_time": now - timedelta(days=7),
                "end_time": now
            },
            {
                "name": "最近30天",
                "start_time": now - timedelta(days=30),
                "end_time": now
            },
            {
                "name": "最近90天",
                "start_time": now - timedelta(days=90),
                "end_time": now
            },
            {
                "name": "全部",
                "start_time": None,
                "end_time": None
            }
        ]
    
    def export_logs(self, 
                   logs: List[Dict[str, Any]], 
                   file_path: str,
                   format: str = "csv") -> bool:
        """
        导出日志
        
        Args:
            logs (List[Dict[str, Any]]): 日志条目列表
            file_path (str): 导出文件路径
            format (str): 导出格式，支持 'csv' 和 'json'
            
        Returns:
            bool: 导出成功返回True，否则返回False
        """
        try:
            if format.lower() == "csv":
                return self._export_to_csv(logs, file_path)
            elif format.lower() == "json":
                return self._export_to_json(logs, file_path)
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False
        except Exception as e:
            logger.error(f"导出日志时出错: {str(e)}")
            return False
    
    def _export_to_csv(self, logs: List[Dict[str, Any]], file_path: str) -> bool:
        """导出为CSV格式"""
        try:
            import csv
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 确定字段
                fieldnames = ["timestamp", "user", "operation", "result", "target", "details", "log_type"]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for log in logs:
                    writer.writerow({k: v for k, v in log.items() if k in fieldnames})
            
            return True
        except Exception as e:
            logger.error(f"导出CSV时出错: {str(e)}")
            return False
    
    def _export_to_json(self, logs: List[Dict[str, Any]], file_path: str) -> bool:
        """导出为JSON格式"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(logs, jsonfile, ensure_ascii=False, indent=4)
            
            return True
        except Exception as e:
            logger.error(f"导出JSON时出错: {str(e)}")
            return False


# 创建单例实例
audit_logger = AuditLogger() 