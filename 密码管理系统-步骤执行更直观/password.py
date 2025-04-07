#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理模块，提供密码的增删改查功能
"""

import logging
from typing import List, Dict, Any, Tuple, Optional, Callable
import os
import traceback

from config import PASSWORD_DATA_FILE
from database import Database
from encrypt import encryptor
from ssh_password_updater import ssh_password_updater
from audit_log import audit_logger, OP_TYPE_ADD, OP_TYPE_UPDATE, OP_TYPE_DELETE, OP_TYPE_GENERATE, OP_TYPE_SSH_UPDATE, OP_RESULT_SUCCESS, OP_RESULT_FAIL, OP_RESULT_WARNING, OP_RESULT_INFO, LOG_TYPE_SSH, LOG_TYPE_LOGIN

# 配置日志
logger = logging.getLogger(__name__)


class PasswordManager:
    """
    密码管理类，处理密码的CRUD操作
    
    提供密码的添加、查询、更新和删除功能，
    管理按所有者分类的密码记录，支持密码加密和搜索。
    """

    _instance = None

    def __new__(cls):
        """
        单例模式，确保密码管理器只有一个实例
        
        Returns:
            PasswordManager: 密码管理器实例
        """
        if cls._instance is None:
            cls._instance = super(PasswordManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        初始化密码管理器
        """
        # 导入存储接口
        import sys
        import os.path
        # 添加项目根目录到Python路径
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from data_storage import get_password_storage
        
        # 使用存储接口
        self.db = get_password_storage()

    def get_all_owners(self) -> List[str]:
        """
        获取所有所有者列表
        
        Returns:
            List[str]: 所有者名称列表
        """
        return list(self.db.get_all().keys())

    def _log_operation(self, operation_type: str, result: str, details: str,
                      target: str, log_type: str = None):
        """
        封装审计日志记录操作
        
        Args:
            operation_type: 操作类型
            result: 操作结果
            details: 详细信息
            target: 操作目标
            log_type: 日志类型，默认为None则使用系统日志
        """
        audit_logger.log_operation(
            operation_type=operation_type,
            result=result,
            details=details,
            target=target,
            log_type=log_type
        )
    
    def _decrypt_password(self, password_record: List[str]) -> List[str]:
        """
        解密密码记录中的密码字段
        
        Args:
            password_record: 密码记录
            
        Returns:
            解密后的密码记录副本
        """
        if not password_record or len(password_record) <= 4:
            return password_record
            
        result = password_record.copy()
        result[4] = encryptor.decrypt(result[4])
        return result

    def add_password(self, owner: str, site_info: List[str], position: Optional[int] = None) -> Tuple[bool, str]:
        """
        添加密码记录
        
        Args:
            owner (str): 所有者
            site_info (List[str]): 密码记录，格式为[项目名称, 功能, IP地址, 账户, 密码, 所在区域, 网络类型, 其他账号]
            position (Optional[int], optional): 插入位置，如果为None则添加到末尾。默认为None。
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 获取所有者的现有密码列表，如果不存在则创建新列表
            passwords = self.db.get(owner, [])
            
            # 确保site_info长度正确
            if len(site_info) < 5:  # 至少需要项目名称、功能、IP地址、账户、密码
                return False, "密码信息不完整"
                
            # 提取项目名称用于日志记录
            project_name = site_info[0] if site_info else "未知"
                
            # 加密密码字段（索引为4）
            site_info[4] = encryptor.encrypt(site_info[4])
            
            # 在指定位置添加新记录，或添加到末尾
            if position is not None and 0 <= position <= len(passwords):
                logger.info(f"在位置 {position+1} 插入新记录")
                passwords.insert(position, site_info)
            else:
                # 添加到末尾
                passwords.append(site_info)
            
            # 保存到数据库
            if self.db.set(owner, passwords):
                logger.info(f"为所有者 {owner} 添加密码记录成功")
                
                # 记录审计日志
                self._log_operation(
                    operation_type=OP_TYPE_ADD,
                    result=OP_RESULT_SUCCESS,
                    details=f"添加密码记录成功，项目：{project_name}",
                    target=f"{owner}/{project_name}"
                )
                
                return True, "添加成功"
            else:
                logger.error(f"为所有者 {owner} 添加密码记录失败")
                
                # 记录审计日志
                self._log_operation(
                    operation_type=OP_TYPE_ADD,
                    result=OP_RESULT_FAIL,
                    details=f"添加密码记录失败，项目：{project_name}",
                    target=f"{owner}/{project_name}"
                )
                
                return False, "添加失败，请稍后重试"
        except Exception as e:
            logger.error(f"添加密码时出错: {str(e)}")
            
            # 记录审计日志
            project_name = site_info[0] if site_info and len(site_info) > 0 else "未知"
            self._log_operation(
                operation_type=OP_TYPE_ADD,
                result=OP_RESULT_FAIL,
                details=f"添加密码记录出错：{str(e)}，项目：{project_name}",
                target=f"{owner}/{project_name}"
            )
            
            return False, f"添加失败: {str(e)}"

    def get_passwords_by_owner(self, owner: str) -> List[List[str]]:
        """
        获取指定所有者的密码列表
        
        Args:
            owner (str): 所有者
            
        Returns:
            List[List[str]]: 密码记录列表
        """
        try:
            # 获取所有者的密码列表
            passwords = self.db.get(owner, [])
            
            # 解密密码字段
            return [self._decrypt_password(password) for password in passwords]
        except Exception as e:
            logger.error(f"获取所有者 {owner} 的密码时出错: {str(e)}")
            return []

    def update_password(self, owner: str, index: int, new_site_info: List[str], skip_server_sync: bool = False) -> Tuple[bool, str]:
        """
        更新密码记录
        
        Args:
            owner (str): 所有者
            index (int): 记录索引
            new_site_info (List[str]): 新的密码记录
            skip_server_sync (bool, optional): 是否跳过服务器同步，适用于新添加行。默认为False。
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 记录详细的操作信息
            project_name = new_site_info[0] if new_site_info else "未知"
            logger.info(f"更新密码记录 - 所有者: {owner}, 索引: {index}, 项目: {project_name}, 跳过服务器同步: {'是' if skip_server_sync else '否'}")
            
            # 获取所有者的密码列表
            passwords = self.db.get(owner, [])
            
            # 检查索引是否有效
            if not passwords or index < 0 or index >= len(passwords):
                # 如果是添加新行但索引无效，将索引调整为列表末尾
                if skip_server_sync and index >= len(passwords):
                    logger.info(f"自动调整新记录索引为: {len(passwords)}")
                    index = len(passwords)
                    # 对于新记录，直接添加到列表末尾
                    if len(new_site_info) < 5:  # 至少需要项目名称、功能、IP地址、账户、密码
                        # 记录审计日志
                        self._log_operation(
                            operation_type=OP_TYPE_ADD,
                            result=OP_RESULT_FAIL,
                            details=f"添加新密码记录失败：密码信息不完整，项目：{project_name}",
                            target=f"{owner}/{project_name}"
                        )
                        return False, "密码信息不完整"
                    
                    # 加密密码字段
                    new_site_info[4] = encryptor.encrypt(new_site_info[4])
                    
                    # 添加新记录
                    passwords.append(new_site_info)
                    
                    # 保存到数据库
                    if self.db.set(owner, passwords):
                        logger.info(f"为所有者 {owner} 添加新记录成功")
                        
                        # 记录审计日志
                        self._log_operation(
                            operation_type=OP_TYPE_ADD,
                            result=OP_RESULT_SUCCESS,
                            details=f"添加新密码记录成功，项目：{project_name}",
                            target=f"{owner}/{project_name}"
                        )
                        
                        return True, "添加成功"
                    else:
                        logger.error(f"为所有者 {owner} 添加新记录失败")
                        
                        # 记录审计日志
                        self._log_operation(
                            operation_type=OP_TYPE_ADD,
                            result=OP_RESULT_FAIL,
                            details=f"添加新密码记录失败：数据库保存失败，项目：{project_name}",
                            target=f"{owner}/{project_name}"
                        )
                        
                        return False, "添加失败，请稍后重试"
                else:
                    logger.error(f"无效的记录索引: {index}, 可用记录数: {len(passwords)}")
                    
                    # 记录审计日志
                    self._log_operation(
                        operation_type=OP_TYPE_UPDATE,
                        result=OP_RESULT_FAIL,
                        details=f"更新密码记录失败：无效的记录索引 {index}，项目：{project_name}",
                        target=f"{owner}/{project_name}"
                    )
                    
                    return False, "无效的记录索引"
                
            # 确保new_site_info长度正确
            if len(new_site_info) < 5:  # 至少需要项目名称、功能、IP地址、账户、密码
                # 记录审计日志
                self._log_operation(
                    operation_type=OP_TYPE_UPDATE,
                    result=OP_RESULT_FAIL,
                    details=f"更新密码记录失败：密码信息不完整，项目：{project_name}",
                    target=f"{owner}/{project_name}"
                )
                
                return False, "密码信息不完整"
            
            # 获取原密码数据（用于同步到服务器）
            old_site_info = passwords[index]
            old_decrypted_password = encryptor.decrypt(old_site_info[4]) if len(old_site_info) > 4 else ""
            new_decrypted_password = new_site_info[4]  # 新密码还未加密
            
            # 如果要求跳过服务器同步，则直接更新本地数据库
            if skip_server_sync:
                logger.info(f"跳过SSH密码更新步骤 - 项目: {project_name}")
                
                # 加密密码字段
                new_site_info[4] = encryptor.encrypt(new_site_info[4])
                
                # 更新记录
                passwords[index] = new_site_info
                
                # 保存到数据库
                if self.db.set(owner, passwords):
                    logger.info(f"更新所有者 {owner} 的密码记录成功 (跳过服务器同步)")
                    
                    # 记录审计日志
                    self._log_operation(
                        operation_type=OP_TYPE_UPDATE,
                        result=OP_RESULT_SUCCESS,
                        details=f"仅更新本地密码记录成功（跳过服务器同步），项目：{project_name}",
                        target=f"{owner}/{project_name}"
                    )
                    
                    return True, "更新成功 (跳过服务器同步)"
                else:
                    logger.error(f"更新所有者 {owner} 的密码记录失败")
                    
                    # 记录审计日志
                    self._log_operation(
                        operation_type=OP_TYPE_UPDATE,
                        result=OP_RESULT_FAIL,
                        details=f"更新本地密码记录失败：数据库保存失败，项目：{project_name}",
                        target=f"{owner}/{project_name}"
                    )
                    
                    return False, "更新失败，请稍后重试"
            
            # 以下是不跳过服务器同步的正常流程
            # 检查是否需要同步到服务器 (有IP地址、账号，且密码已更改)
            ip_address = new_site_info[2] if len(new_site_info) > 2 else ""
            username = new_site_info[3] if len(new_site_info) > 3 else ""
            
            server_sync_needed = bool(ip_address and username and old_decrypted_password != new_decrypted_password)
            server_sync_success = True
            server_sync_message = ""
            
            if server_sync_needed:
                logger.info(f"需要SSH更新密码 - 项目: {project_name}, IP: {ip_address}, 用户: {username}")
                
                try:
                    # 记录SSH更新开始
                    self._log_operation(
                        operation_type=OP_TYPE_SSH_UPDATE,
                        result=OP_RESULT_INFO,
                        details=f"开始SSH密码更新，项目：{project_name}，IP：{ip_address}，用户：{username}",
                        target=f"{owner}/{project_name}",
                        log_type=LOG_TYPE_SSH
                    )
                    
                    # 尝试连接到服务器并更新密码
                    server_sync_success, server_sync_message = ssh_password_updater.update_password(
                        ip=ip_address,
                        username=username,
                        old_password=old_decrypted_password,
                        new_password=new_decrypted_password
                    )
                    
                    # 记录SSH更新结果
                    self._log_operation(
                        operation_type=OP_TYPE_SSH_UPDATE,
                        result=OP_RESULT_SUCCESS if server_sync_success else OP_RESULT_FAIL,
                        details=f"SSH密码更新{'成功' if server_sync_success else '失败'}：{server_sync_message}，项目：{project_name}，IP：{ip_address}，用户：{username}",
                        target=f"{owner}/{project_name}",
                        log_type=LOG_TYPE_SSH
                    )
                    
                    # 记录日志文件路径
                    ssh_log_file = ssh_password_updater.get_log_file_path()
                    logger.info(f"SSH密码更新操作已记录到日志文件: {ssh_log_file}")
                except ImportError as e:
                    server_sync_success = False
                    server_sync_message = f"导入SSH密码更新模块失败: {str(e)}"
                    logger.error(f"导入SSH密码更新模块失败: {str(e)}")
                    
                    # 记录SSH模块导入失败
                    self._log_operation(
                        operation_type=OP_TYPE_SSH_UPDATE,
                        result=OP_RESULT_FAIL,
                        details=f"SSH密码更新失败：导入SSH模块失败 - {str(e)}，项目：{project_name}",
                        target=f"{owner}/{project_name}",
                        log_type=LOG_TYPE_SSH
                    )
            
            # 无论SSH同步是否成功，都更新本地数据库
            # 加密密码字段
            new_site_info[4] = encryptor.encrypt(new_site_info[4])
            
            # 更新记录
            passwords[index] = new_site_info
            
            # 保存到数据库
            if self.db.set(owner, passwords):
                logger.info(f"更新所有者 {owner} 的密码记录成功")
                
                # 根据服务器同步需求和结果，选择不同的日志记录和返回信息
                if server_sync_needed:
                    if server_sync_success:
                        # 本地和服务器都更新成功
                        self._log_operation(
                            operation_type=OP_TYPE_UPDATE,
                            result=OP_RESULT_SUCCESS,
                            details=f"更新密码记录成功（本地和服务器都已更新），项目：{project_name}",
                            target=f"{owner}/{project_name}"
                        )
                        return True, "更新成功（本地和服务器都已更新）"
                    else:
                        # SSH同步失败，但本地数据库已更新
                        logger.warning(f"服务器密码更新失败，但本地密码已更新：{server_sync_message}")
                        self._log_operation(
                            operation_type=OP_TYPE_UPDATE,
                            result=OP_RESULT_WARNING,
                            details=f"本地密码已更新，但服务器密码更新失败：{server_sync_message}，项目：{project_name}",
                            target=f"{owner}/{project_name}"
                        )
                        return True, f"本地密码已更新，但服务器密码更新失败：{server_sync_message}"
                else:
                    # 仅本地更新成功
                    self._log_operation(
                        operation_type=OP_TYPE_UPDATE,
                        result=OP_RESULT_SUCCESS,
                        details=f"更新密码记录成功，项目：{project_name}",
                        target=f"{owner}/{project_name}"
                    )
                    return True, "更新成功"
            else:
                logger.error(f"更新所有者 {owner} 的密码记录失败")
                
                # 本地更新失败
                self._log_operation(
                    operation_type=OP_TYPE_UPDATE,
                    result=OP_RESULT_FAIL,
                    details=f"更新本地密码记录失败：数据库保存失败，项目：{project_name}",
                    target=f"{owner}/{project_name}"
                )
                return False, "更新失败，请稍后重试"
                
        except Exception as e:
            logger.error(f"更新密码时出错: {str(e)}")
            
            # 更新出错
            project_name = new_site_info[0] if new_site_info and len(new_site_info) > 0 else "未知"
            self._log_operation(
                operation_type=OP_TYPE_UPDATE,
                result=OP_RESULT_FAIL,
                details=f"更新密码记录出错：{str(e)}，项目：{project_name}",
                target=f"{owner}/{project_name}"
            )
            return False, f"更新失败: {str(e)}"

    def delete_password(self, owner: str, index: int) -> Tuple[bool, str]:
        """
        删除密码记录
        
        Args:
            owner (str): 所有者
            index (int): 记录索引
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 获取所有者的密码列表
            passwords = self.db.get(owner, [])
            
            # 检查索引是否有效
            if not passwords or index < 0 or index >= len(passwords):
                # 记录审计日志 - 无效索引
                self._log_operation(
                    operation_type=OP_TYPE_DELETE,
                    result=OP_RESULT_FAIL,
                    details=f"删除密码记录失败：无效的记录索引 {index}",
                    target=f"{owner}/未知记录"
                )
                return False, "无效的记录索引"
                
            # 获取项目名称用于日志记录
            project_name = passwords[index][0] if passwords[index] and len(passwords[index]) > 0 else "未知"
                
            # 删除记录
            del passwords[index]
            
            # 保存到数据库
            if self.db.set(owner, passwords):
                logger.info(f"删除所有者 {owner} 的密码记录成功")
                
                # 记录审计日志 - 删除成功
                self._log_operation(
                    operation_type=OP_TYPE_DELETE,
                    result=OP_RESULT_SUCCESS,
                    details=f"删除密码记录成功，项目：{project_name}",
                    target=f"{owner}/{project_name}"
                )
                return True, "删除成功"
            else:
                logger.error(f"删除所有者 {owner} 的密码记录失败")
                
                # 记录审计日志 - 删除失败
                self._log_operation(
                    operation_type=OP_TYPE_DELETE,
                    result=OP_RESULT_FAIL,
                    details=f"删除密码记录失败：数据库保存失败，项目：{project_name}",
                    target=f"{owner}/{project_name}"
                )
                return False, "删除失败，请稍后重试"
        except Exception as e:
            logger.error(f"删除密码时出错: {str(e)}")
            
            # 记录审计日志 - 删除出错
            self._log_operation(
                operation_type=OP_TYPE_DELETE,
                result=OP_RESULT_FAIL,
                details=f"删除密码记录出错：{str(e)}",
                target=f"{owner}/未知记录"
            )
            return False, f"删除失败: {str(e)}"

    def search_passwords(self, keyword: str, owner: Optional[str] = None) -> List[Tuple[str, List[str]]]:
        """
        搜索密码记录
        
        Args:
            keyword (str): 搜索关键词
            owner (Optional[str], optional): 指定所有者，如果为None则搜索所有所有者的密码。默认为None
            
        Returns:
            List[Tuple[str, List[str]]]: 搜索结果列表，每个元素为(所有者, 密码记录)
        """
        results = []
        keyword = keyword.lower()  # 转换为小写以进行不区分大小写的搜索
        
        try:
            # 确定要搜索的所有者列表
            owners = [owner] if owner else self.get_all_owners()
                
            for current_owner in owners:
                passwords = self.db.get(current_owner, [])
                
                for password in passwords:
                    # 解密密码进行搜索
                    password_for_search = self._decrypt_password(password)
                    
                    # 在所有字段中搜索关键词
                    if any(keyword in str(field).lower() for field in password_for_search):
                        # 将解密后的密码记录添加到结果中
                        results.append((current_owner, password_for_search))
                        
            return results
        except Exception as e:
            logger.error(f"搜索密码时出错: {str(e)}")
            return []

    def get_latest_ssh_operations(self, lines: int = 20) -> List[str]:
        """
        获取最新的SSH操作日志
        
        Args:
            lines (int, optional): 要获取的行数。默认为20。
            
        Returns:
            List[str]: 日志行列表
        """
        try:
            # 获取日志文件路径
            log_file = ssh_password_updater.get_log_file_path()
            
            # 如果日志文件不存在，返回空列表
            if not os.path.exists(log_file):
                logger.warning(f"SSH操作日志文件不存在: {log_file}")
                return []
                
            # 使用view_ssh_logs模块的函数读取文件最后几行
            from view_ssh_logs import read_last_lines
            return read_last_lines(log_file, lines)
        except Exception as e:
            logger.error(f"获取SSH操作日志失败: {str(e)}")
            return [f"获取日志失败: {str(e)}"]


# 创建密码管理器实例
password_manager = PasswordManager() 