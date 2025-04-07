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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

from config import LOG_DIR, DATA_DIR

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
                # 确保日志目录存在
                self.log_dir = os.path.join(LOG_DIR, 'audit')
                self.system_log_file = os.path.join(self.log_dir, 'system_audit.json')
                
                if not os.path.exists(self.log_dir):
                    os.makedirs(self.log_dir)
                
                # 初始化缓存
                self.cache = {}
                self.cache_time = {}
                self.cache_expiry = 60  # 缓存有效期(秒)
                
                self._initialized = True
    
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
                from user import user_manager
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
            
            # 确定日志文件
            log_file = self._get_log_file(log_type)
            
            # 读取现有日志
            logs = self._read_logs(log_file)
            
            # 添加新日志条目
            logs.append(log_entry)
            
            # 保存日志
            return self._write_logs(log_file, logs)
        
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
        查询日志
        
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
            
            # 读取日志
            if log_type == LOG_TYPE_ALL:
                # 读取所有类型的日志
                logs = []
                logs.extend(self._read_logs(self._get_log_file(LOG_TYPE_SYSTEM)))
                logs.extend(self._read_logs(self._get_log_file(LOG_TYPE_SSH)))
                logs.extend(self._read_logs(self._get_log_file(LOG_TYPE_LOGIN)))
            else:
                # 读取特定类型的日志
                logs = self._read_logs(self._get_log_file(log_type))
            
            # 应用筛选条件
            filtered_logs = []
            for log in logs:
                # 解析时间戳
                try:
                    log_time = datetime.fromisoformat(log.get("timestamp", ""))
                except (ValueError, TypeError):
                    continue
                
                # 时间范围筛选
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue
                
                # 操作类型筛选
                if operation_types and log.get("operation") not in operation_types:
                    continue
                
                # 用户筛选
                if users and log.get("user") not in users:
                    continue
                
                # 结果筛选
                if results and log.get("result") not in results:
                    continue
                
                # 关键词搜索
                if keyword:
                    keyword_lower = keyword.lower()
                    found = False
                    # 在各个字段中搜索关键词
                    for field in ["details", "target", "user", "operation"]:
                        if field in log and isinstance(log[field], str) and keyword_lower in log[field].lower():
                            found = True
                            break
                    if not found:
                        continue
                
                filtered_logs.append(log)
            
            # 排序：按时间戳降序
            filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # 分页
            paginated_logs = filtered_logs[offset:offset+limit]
            
            # 缓存结果
            self.cache[cache_key] = paginated_logs
            self.cache_time[cache_key] = time.time()
            
            return paginated_logs
        
        except Exception as e:
            logger.error(f"查询审计日志时出错: {str(e)}")
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
            Dict[str, Any]: 统计结果
        """
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # 获取日志
            logs = self.get_logs(log_type, start_time, end_time)
            
            # 初始化统计结果
            stats = {
                "total_operations": len(logs),
                "operations_by_type": {},
                "operations_by_result": {},
                "operations_by_user": {},
                "operations_by_day": {},
                "success_rate": 0,
                "top_targets": {},
                "recent_trends": []
            }
            
            # 没有日志时直接返回
            if not logs:
                return stats
            
            # 按操作类型统计
            for log in logs:
                op_type = log.get("operation", "未知")
                stats["operations_by_type"][op_type] = stats["operations_by_type"].get(op_type, 0) + 1
                
                # 按结果统计
                result = log.get("result", "未知")
                stats["operations_by_result"][result] = stats["operations_by_result"].get(result, 0) + 1
                
                # 按用户统计
                user = log.get("user", "未知")
                stats["operations_by_user"][user] = stats["operations_by_user"].get(user, 0) + 1
                
                # 按目标统计
                target = log.get("target", "未知")
                stats["top_targets"][target] = stats["top_targets"].get(target, 0) + 1
                
                # 按日期统计
                try:
                    log_time = datetime.fromisoformat(log.get("timestamp", ""))
                    day_key = log_time.date().isoformat()
                    stats["operations_by_day"][day_key] = stats["operations_by_day"].get(day_key, 0) + 1
                except (ValueError, TypeError):
                    continue
            
            # 计算成功率
            success_count = stats["operations_by_result"].get(OP_RESULT_SUCCESS, 0)
            total_count = sum(stats["operations_by_result"].values())
            stats["success_rate"] = int(success_count / total_count * 100) if total_count else 0
            
            # 计算最近趋势 (最近7天)
            for i in range(7):
                day = (end_time - timedelta(days=i)).date().isoformat()
                stats["recent_trends"].append({
                    "date": day,
                    "count": stats["operations_by_day"].get(day, 0)
                })
            
            # 排序结果
            stats["top_users"] = sorted(
                [{"user": k, "count": v} for k, v in stats["operations_by_user"].items()],
                key=lambda x: x["count"],
                reverse=True
            )[:5]
            
            stats["top_operations"] = sorted(
                [{"type": k, "count": v} for k, v in stats["operations_by_type"].items()],
                key=lambda x: x["count"],
                reverse=True
            )
            
            stats["top_targets"] = sorted(
                [{"target": k, "count": v} for k, v in stats["top_targets"].items()],
                key=lambda x: x["count"],
                reverse=True
            )[:5]
            
            return stats
            
        except Exception as e:
            logger.error(f"生成审计日志统计时出错: {str(e)}")
            return {"error": str(e)}
    
    def get_time_range_options(self) -> List[Dict[str, Any]]:
        """
        获取时间范围选项
        
        Returns:
            List[Dict[str, Any]]: 时间范围选项列表
        """
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        
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
    
    def _get_log_file(self, log_type: str) -> str:
        """
        根据日志类型获取日志文件路径
        
        Args:
            log_type (str): 日志类型
            
        Returns:
            str: 日志文件路径
        """
        if log_type == LOG_TYPE_SSH:
            return os.path.join(self.log_dir, 'ssh_audit.json')
        elif log_type == LOG_TYPE_LOGIN:
            return os.path.join(self.log_dir, 'login_audit.json')
        return self.system_log_file
    
    def _read_logs(self, log_file: str) -> List[Dict[str, Any]]:
        """
        读取日志文件
        
        Args:
            log_file (str): 日志文件路径
            
        Returns:
            List[Dict[str, Any]]: 日志列表
        """
        try:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"读取日志文件 {log_file} 时出错: {str(e)}")
                    # 重新创建一个有效的空JSON文件
                    with open(log_file, 'w', encoding='utf-8') as f:
                        json.dump([], f)
                    logger.info(f"已重新创建空日志文件: {log_file}")
            return []
        except Exception as e:
            logger.error(f"读取日志文件 {log_file} 时出错: {str(e)}")
            return []
    
    def _write_logs(self, log_file: str, logs: List[Dict[str, Any]]) -> bool:
        """
        写入日志文件
        
        Args:
            log_file (str): 日志文件路径
            logs (List[Dict[str, Any]]): 日志列表
            
        Returns:
            bool: 写入成功返回True，否则返回False
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # 写入新日志
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"成功写入 {len(logs)} 条日志记录到 {log_file}")
            return True
            
        except Exception as e:
            logger.error(f"写入日志文件 {log_file} 时出错: {str(e)}")
            # 尝试以安全方式写入
            try:
                # 使用临时文件写入
                temp_file = f"{log_file}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)
                
                # 如果写入成功，重命名替换原文件
                if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                    import shutil
                    shutil.move(temp_file, log_file)
                    logger.info(f"通过临时文件成功写入日志: {log_file}")
                    return True
            except Exception as temp_err:
                logger.error(f"通过临时文件写入日志时出错: {str(temp_err)}")
            
            return False


# 创建单例实例
audit_logger = AuditLogger() 