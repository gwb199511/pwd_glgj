#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SSH操作日志查看工具

提供命令行界面，方便查看和分析SSH操作日志。
"""

import os
import sys
import argparse
import datetime
import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def read_log_file(log_file: str, lines: int = 0) -> List[str]:
    """
    读取日志文件
    
    Args:
        log_file (str): 日志文件路径
        lines (int, optional): 要读取的行数，0表示全部读取。默认为0。
        
    Returns:
        List[str]: 日志行列表
    """
    if not os.path.exists(log_file):
        print(f"错误: 日志文件不存在 - {log_file}")
        return []
    
    if lines == 0:
        # 如果需要读取全部行，直接按行读取
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f]
        except Exception as e:
            logger.error(f"读取日志文件出错: {str(e)}")
            return []
    else:
        # 如果只需要读取最后几行，使用高效方法
        return read_last_lines(log_file, lines)


def read_last_lines(file_path: str, lines: int) -> List[str]:
    """
    高效地读取文件的最后几行
    
    Args:
        file_path (str): 文件路径
        lines (int): 要读取的行数
        
    Returns:
        List[str]: 文件最后几行
    """
    try:
        with open(file_path, 'rb') as f:
            # 获取文件大小
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            
            # 如果文件为空，直接返回空列表
            if file_size == 0:
                return []
                
            # 设置初始位置为文件末尾前的1024字节或文件大小（取较小值）
            block_size = 1024
            block_num = -1
            # 保存读取的行
            lines_found = []
            
            # 从文件末尾开始，每次读取一个块
            while len(lines_found) < lines and file_size > abs(block_num * block_size):
                # 定位到文件的特定位置
                position = max(file_size + block_num * block_size, 0)
                f.seek(position)
                
                # 读取一个数据块
                data = f.read(min(abs(block_num * block_size), file_size))
                
                # 解码数据并分割成行
                text = data.decode('utf-8', errors='replace')
                current_lines = text.split('\n')
                
                # 如果不是第一个数据块且最后一行不完整，则与前一块的第一行合并
                if position > 0 and len(lines_found) > 0:
                    lines_found[0] = current_lines[-1] + lines_found[0]
                    current_lines = current_lines[:-1]
                
                # 将当前块的行添加到结果列表前面
                lines_found = current_lines + lines_found
                
                # 移动到下一个块
                block_num -= 1
            
            # 返回最后 'lines' 行
            return [line.rstrip('\r') for line in lines_found[-lines:] if line]
    except Exception as e:
        logger.error(f"读取文件最后几行时出错: {str(e)}")
        return []


def parse_log_line(line: str) -> Optional[Dict[str, str]]:
    """
    解析日志行
    
    Args:
        line (str): 日志行
        
    Returns:
        Optional[Dict[str, str]]: 解析结果，如果解析失败则返回None
    """
    try:
        # 假设日志格式为: "2024-03-15 10:23:45 - INFO - [12345] - 开始尝试更新服务器 192.168.1.100 上用户 admin 的密码"
        parts = line.split(' - ', 3)
        if len(parts) != 4:
            return None
            
        timestamp, level, process_id, message = parts
        
        # 提取IP地址和用户名（如果存在）
        ip_address = None
        username = None
        
        if "服务器" in message and "用户" in message:
            # 尝试提取IP地址
            ip_start = message.find("服务器 ") + 4
            ip_end = message.find(" 上用户")
            if ip_start > 4 and ip_end > ip_start:
                ip_address = message[ip_start:ip_end]
                
            # 尝试提取用户名
            user_start = message.find("用户 ") + 3
            user_end = message.find(" 的密码")
            if user_start > 3 and user_end > user_start:
                username = message[user_start:user_end]
        
        return {
            "timestamp": timestamp,
            "level": level,
            "process_id": process_id.strip('[]'),
            "message": message,
            "ip_address": ip_address,
            "username": username
        }
    except Exception as e:
        logger.debug(f"解析日志行失败: {str(e)}, 行内容: {line}")
        return None

def filter_logs(logs: List[str], level: Optional[str] = None, ip: Optional[str] = None, 
                username: Optional[str] = None, success_only: bool = False, 
                error_only: bool = False) -> List[str]:
    """
    根据条件过滤日志
    
    Args:
        logs (List[str]): 日志行列表
        level (Optional[str], optional): 日志级别过滤。默认为None。
        ip (Optional[str], optional): IP地址过滤。默认为None。
        username (Optional[str], optional): 用户名过滤。默认为None。
        success_only (bool, optional): 只显示成功记录。默认为False。
        error_only (bool, optional): 只显示错误记录。默认为False。
        
    Returns:
        List[str]: 过滤后的日志行列表
    """
    filtered_logs = []
    
    for log in logs:
        parsed = parse_log_line(log)
        if not parsed:
            continue
            
        # 应用过滤条件
        if level and parsed["level"] != level:
            continue
            
        if ip and (not parsed["ip_address"] or ip not in parsed["ip_address"]):
            continue
            
        if username and (not parsed["username"] or username not in parsed["username"]):
            continue
            
        if success_only and "成功" not in parsed["message"]:
            continue
            
        if error_only and "ERROR" not in parsed["level"]:
            continue
            
        filtered_logs.append(log)
        
    return filtered_logs

def analyze_logs(logs: List[str]) -> Dict[str, any]:
    """
    分析日志内容
    
    Args:
        logs (List[str]): 日志行列表
        
    Returns:
        Dict[str, any]: 分析结果
    """
    results = {
        "总日志行数": len(logs),
        "信息日志数": 0,
        "错误日志数": 0,
        "成功操作数": 0,
        "失败操作数": 0,
        "服务器IP统计": Counter(),
        "用户名统计": Counter(),
        "错误类型统计": Counter(),
        "最早记录时间": None,
        "最新记录时间": None
    }
    
    for log in logs:
        parsed = parse_log_line(log)
        if not parsed:
            continue
            
        # 日志级别统计
        if parsed["level"] == "INFO":
            results["信息日志数"] += 1
        elif parsed["level"] == "ERROR":
            results["错误日志数"] += 1
            
        # 操作成功/失败统计
        if "成功" in parsed["message"]:
            results["成功操作数"] += 1
        elif "失败" in parsed["message"] or "ERROR" in parsed["level"]:
            results["失败操作数"] += 1
            # 分析错误类型
            if "失败" in parsed["message"]:
                error_type = "未知错误"
                if "timed out" in parsed["message"]:
                    error_type = "连接超时"
                elif "拒绝" in parsed["message"] or "denied" in parsed["message"]:
                    error_type = "访问拒绝"
                elif "无法连接" in parsed["message"] or "连接失败" in parsed["message"]:
                    error_type = "连接失败"
                results["错误类型统计"][error_type] += 1
            
        # IP地址和用户名统计
        if parsed["ip_address"]:
            results["服务器IP统计"][parsed["ip_address"]] += 1
        if parsed["username"]:
            results["用户名统计"][parsed["username"]] += 1
            
        # 记录时间范围
        try:
            timestamp = datetime.datetime.strptime(parsed["timestamp"], "%Y-%m-%d %H:%M:%S,%f")
            if results["最早记录时间"] is None or timestamp < results["最早记录时间"]:
                results["最早记录时间"] = timestamp
            if results["最新记录时间"] is None or timestamp > results["最新记录时间"]:
                results["最新记录时间"] = timestamp
        except Exception:
            pass
            
    return results

def print_analysis(analysis: Dict[str, any]):
    """
    打印分析结果
    
    Args:
        analysis (Dict[str, any]): 分析结果
    """
    print("\n==== SSH操作日志分析 ====")
    print(f"总日志行数: {analysis['总日志行数']}")
    print(f"信息日志数: {analysis['信息日志数']}")
    print(f"错误日志数: {analysis['错误日志数']}")
    print(f"成功操作数: {analysis['成功操作数']}")
    print(f"失败操作数: {analysis['失败操作数']}")
    
    if analysis["最早记录时间"] and analysis["最新记录时间"]:
        print(f"日志时间范围: {analysis['最早记录时间']} 至 {analysis['最新记录时间']}")
    
    print("\n服务器IP统计:")
    for ip, count in analysis["服务器IP统计"].most_common(10):
        print(f"  {ip}: {count}次")
    
    print("\n用户名统计:")
    for username, count in analysis["用户名统计"].most_common(10):
        print(f"  {username}: {count}次")
        
    print("\n错误类型统计:")
    for error_type, count in analysis["错误类型统计"].most_common():
        print(f"  {error_type}: {count}次")

def main():
    """
    主函数，解析命令行参数并执行相应的操作
    """
    parser = argparse.ArgumentParser(description='SSH操作日志查看和分析工具')
    parser.add_argument('-f', '--file', default='logs/ssh_operations.log', help='日志文件路径')
    parser.add_argument('-n', '--lines', type=int, default=0, help='要显示的行数，0表示全部显示')
    parser.add_argument('-l', '--level', choices=['INFO', 'ERROR'], help='按日志级别过滤')
    parser.add_argument('-i', '--ip', help='按IP地址过滤')
    parser.add_argument('-u', '--username', help='按用户名过滤')
    parser.add_argument('-s', '--success', action='store_true', help='只显示成功记录')
    parser.add_argument('-e', '--error', action='store_true', help='只显示错误记录')
    parser.add_argument('-a', '--analyze', action='store_true', help='分析日志内容')
    
    args = parser.parse_args()
    
    # 读取日志文件
    logs = read_log_file(args.file, args.lines)
    if not logs:
        return
        
    # 应用过滤条件
    filtered_logs = filter_logs(
        logs, 
        level=args.level, 
        ip=args.ip, 
        username=args.username, 
        success_only=args.success, 
        error_only=args.error
    )
    
    # 分析日志（如果需要）
    if args.analyze:
        analysis = analyze_logs(filtered_logs)
        print_analysis(analysis)
        return
        
    # 打印日志
    for log in filtered_logs:
        print(log)
    
    print(f"\n共显示 {len(filtered_logs)} 行日志记录")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"程序执行异常: {str(e)}")
        print(f"程序执行异常: {str(e)}")
        sys.exit(1) 