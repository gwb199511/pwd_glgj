#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SSH密码更新模块，提供SSH密码更新功能

使用Paramiko库实现安全的SSH密码更新操作，支持各种Linux/Unix系统。
"""

import logging
import os
import platform
import shutil
import datetime
import time
from logging.handlers import RotatingFileHandler
from typing import Tuple, Optional, Union, Dict, Any
import socket

# 导入配置文件中的日志目录路径常量
from config import LOG_DIR

# 配置SSH操作专用日志
ssh_logger = logging.getLogger('ssh_password_updater')
ssh_logger.setLevel(logging.INFO)

# 创建文件处理器 - 使用配置中的LOG_DIR路径
ssh_log_file = os.path.join(LOG_DIR, 'ssh_operations.log')
# 使用RotatingFileHandler，限制单个日志文件大小为1MB，最多保留5个备份文件
file_handler = RotatingFileHandler(
    ssh_log_file,
    maxBytes=1024*1024,  # 1MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# 设置日志格式 - 添加更多详细信息
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(process)d] - %(message)s')
file_handler.setFormatter(formatter)

# 添加处理器到日志记录器
ssh_logger.addHandler(file_handler)

# 确保ssh_logger不会将日志传递给根记录器
ssh_logger.propagate = False

# 导入paramiko
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    ssh_logger.error("未安装paramiko库，服务器密码同步功能将无法使用")

class SSHPasswordUpdater:
    """
    SSH密码更新类
    
    通过SSH连接到远程服务器并更新用户密码，使用paramiko库实现
    """
    
    def __init__(self):
        """
        初始化SSH密码更新器
        """
        self.is_windows = platform.system().lower() == "windows"
        ssh_logger.info("SSH密码更新器初始化，运行平台：" + platform.system())
        
    def update_password(self, ip: str, username: str, old_password: str, new_password: str) -> Tuple[bool, str, bool]:
        """
        更新远程服务器上的用户密码
        
        Args:
            ip (str): 服务器IP地址
            username (str): 用户名
            old_password (str): 旧密码
            new_password (str): 新密码
            
        Returns:
            Tuple[bool, str, bool]: (成功状态, 消息, 验证结果)
        """
        # 记录开始尝试更新密码的操作
        ssh_logger.info(f"等待更新服务器 {ip} 上用户 {username} 的密码")
        
        # 检查paramiko是否可用
        if not PARAMIKO_AVAILABLE:
            error_msg = "未安装paramiko库，请执行 'pip install paramiko' 安装后重试"
            ssh_logger.error(error_msg)
            return False, error_msg, False
        
        # 使用paramiko更新密码
        success, message, verify_success = self._update_password_with_paramiko(ip, username, old_password, new_password)
        
        # 记录操作结果
        if success:
            if verify_success:
                ssh_logger.info(f"更新成功！！！ 服务器 {ip} 上用户 {username} 的密码已更新并验证")
            else:
                ssh_logger.info(f"密码修改成功！服务器 {ip} 上用户 {username} 的密码已更新但验证未成功")
        else:
            ssh_logger.error(f"更新失败: 服务器 {ip} 上用户 {username} 的密码更新失败: {message}")
            
        return success, message, verify_success
    
    def _update_password_with_paramiko(self, ip: str, username: str, old_password: str, new_password: str) -> Tuple[bool, str, bool]:
        """
        使用paramiko更新远程服务器上的用户密码
        
        Args:
            ip (str): 服务器IP地址
            username (str): 用户名
            old_password (str): 旧密码
            new_password (str): 新密码
            
        Returns:
            Tuple[bool, str, bool]: (成功状态, 消息, 验证结果)
        """
        try:
            # 创建SSH客户端
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                # 连接到服务器
                ssh_logger.info(f"尝试连接服务器 {ip}")
                client.connect(
                    hostname=ip,
                    username=username,
                    password=old_password,
                    timeout=10
                )
                
                ssh_logger.info(f"连接成功，开始修改密码 - 服务器 {ip}")
                
                # 使用更智能的交互式密码更改方式
                return self._interactive_password_change(client, username, old_password, new_password)
                
            except Exception as e:
                ssh_logger.error(f"连接失败: 连接到服务器 {ip} 或执行命令失败: {str(e)}")
                return False, f"连接或命令执行失败: {str(e)}", False
            finally:
                ssh_logger.info(f"关闭与服务器 {ip} 的连接")
                client.close()
                
        except Exception as e:
            ssh_logger.error(f"更新失败: 使用paramiko更新密码时出错: {str(e)}")
            return False, f"更新密码失败: {str(e)}", False
            
    def _interactive_password_change(self, client, username, old_password, new_password) -> Tuple[bool, str, bool]:
        """
        执行交互式密码更改
        
        Args:
            client: Paramiko SSH客户端
            username: 用户名
            old_password: 旧密码 (用于连接，不需要在passwd流程中再次输入)
            new_password: 新密码
            
        Returns:
            Tuple[bool, str, bool]: (成功状态, 消息, 验证结果)
        """
        host = client.get_transport().getpeername()[0]  # 获取主机IP
        success_indicators = [
            'password updated successfully',
            'successfully changed',
            'all authentication tokens updated',
            'password has been changed'
        ]
        
        try:
            # 获取通道并打开PTY会话
            channel = client.get_transport().open_session()
            channel.get_pty()
            channel.exec_command('passwd')
            
            ssh_logger.info(f"正在修改密码...")
            
            # 读取初始提示 - 这通常是请求输入新密码的提示
            # 在大多数系统中，使用已验证的SSH会话执行passwd时，不需要再次验证当前密码
            output = self._read_until(channel, 'password:', timeout=3)
            ssh_logger.info(f"密码提示: {output}")
            
            # 直接发送新密码作为第一次输入
            ssh_logger.info("发送新密码")
            channel.send(new_password + '\n')
            time.sleep(1)  # 等待处理
            
            # 读取确认密码提示
            output = self._read_until(channel, 'password:', timeout=3)
            ssh_logger.info(f"确认密码提示: {output}")
            
            # 检查是否有密码长度错误或其他密码策略错误
            if 'bad password' in output.lower():
                # 只记录警告，但不终止操作
                ssh_logger.warning(f"服务器报告密码不符合要求，但将继续尝试: {output}")
                # 不返回错误，继续流程
            
            # 再次发送新密码进行确认
            ssh_logger.info("再次发送新密码进行确认")
            channel.send(new_password + '\n')
            time.sleep(1)  # 等待处理
            
            # 读取最终结果
            output = self._read_until(channel, '', timeout=3)
            ssh_logger.info(f"密码更新操作返回: {output}")
            
            # 检查是否包含明确的失败信息
            has_clear_failure = any(error in output.lower() for error in 
                                    ['password change aborted', 'exhausted maximum number of retries'])
            
            # 如果有明确的失败信息，则返回失败
            if has_clear_failure:
                ssh_logger.error(f"更新失败: 密码更新失败，服务器明确拒绝: {output}")
                return False, f"密码更新失败: {output}", False
            
            # 检查是否成功
            password_modified = any(indicator in output.lower() for indicator in success_indicators)
            if password_modified:
                ssh_logger.info(f"密码修改成功，开始验证...")
            else:
                ssh_logger.warning(f"密码更新状态不明确，将尝试验证")
            
            # 验证密码
            ssh_logger.info(f"开始验证修改...")
            verification_result = self._verify_password_change(host, username, new_password)
            
            if verification_result:
                ssh_logger.info(f"更新成功！！！ 服务器上用户 {username} 的密码已更新并验证成功")
                return True, "密码更新成功并已验证", True
            else:
                ssh_logger.warning(f"密码更新操作可能成功，但验证失败")
                # 如果验证失败但没有明确的错误信息，仍然返回成功
                # 这是因为一些服务器可能需要一些时间来应用新密码
                if password_modified:
                    return True, "密码可能已更新，但无法立即验证", False
                else:
                    return False, "密码更新操作返回但验证失败，密码可能未实际更改", False
                
        except Exception as e:
            ssh_logger.error(f"更新失败: 交互式密码更改过程中出错: {str(e)}")
            return False, f"密码更新失败: {str(e)}", False
            
    def _verify_password_change(self, host: str, username: str, new_password: str) -> bool:
        """
        验证密码是否已成功更改，通过尝试使用新密码建立新连接
        
        Args:
            host: 服务器IP地址
            username: 用户名
            new_password: 新密码
            
        Returns:
            bool: 密码是否验证成功
        """
        ssh_logger.info(f"开始验证修改: 尝试使用新密码连接到 {host}")
        
        # 创建新的SSH客户端
        try:
            test_client = paramiko.SSHClient()
            test_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 尝试使用新密码连接
            ssh_logger.info(f"尝试使用新密码连接...")
            test_client.connect(
                hostname=host,
                username=username,
                password=new_password,
                timeout=10
            )
            
            # 执行简单命令以确认连接有效
            ssh_logger.info(f"新密码连接成功，执行验证命令...")
            _, stdout, stderr = test_client.exec_command('echo "Password verification successful"')
            result = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            if error:
                ssh_logger.warning(f"验证命令执行出错: {error}")
                
            if "verification successful" in result:
                ssh_logger.info(f"密码修改验证成功: 能够使用新密码登录并执行命令")
                test_client.close()
                return True
            else:
                ssh_logger.warning(f"密码修改验证失败: 连接成功但命令执行有问题，返回结果: '{result}'")
                test_client.close()
                return False
                
        except paramiko.AuthenticationException:
            ssh_logger.error(f"验证失败: 使用新密码无法认证")
            return False
        except paramiko.SSHException as e:
            ssh_logger.error(f"验证失败: SSH连接异常: {str(e)}")
            return False
        except socket.timeout:
            ssh_logger.error(f"验证失败: 连接超时")
            return False
        except Exception as e:
            ssh_logger.error(f"验证失败: 未预期的错误: {str(e)}")
            return False

    def _read_until(self, channel, expected_text='', timeout=3):
        """
        从channel读取直到遇到预期文本或超时
        
        Args:
            channel: Paramiko SSH通道
            expected_text (str): 期望的文本（如果为空则读取所有可用数据）
            timeout (int): 超时时间（秒）
            
        Returns:
            str: 读取的文本
        """
        output = ""
        start_time = datetime.datetime.now()
        
        while True:
            # 检查是否超时
            if (datetime.datetime.now() - start_time).total_seconds() > timeout:
                break
                
            # 检查是否有数据可读
            if channel.recv_ready():
                # 接收数据
                chunk = channel.recv(1024).decode('utf-8', errors='ignore')
                output += chunk
                
                # 如果找到预期文本或空的预期文本，则返回
                if expected_text and expected_text.lower() in output.lower():
                    break
                elif not expected_text and not chunk:  # 如果没有预期文本且没有更多数据
                    break
            else:
                # 短暂等待数据
                time.sleep(0.1)
        
        return output

    def test_ssh_connection(self, ip: str, username: str, password: str) -> Tuple[bool, str]:
        """
        测试SSH连接
        
        Args:
            ip (str): 服务器IP地址
            username (str): 用户名
            password (str): 密码
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        # 记录开始尝试测试连接的操作
        ssh_logger.info(f"测试与服务器 {ip} 的SSH连接，用户: {username}")
        
        # 检查paramiko是否可用
        if not PARAMIKO_AVAILABLE:
            error_msg = "未安装paramiko库，请执行 'pip install paramiko' 安装后重试"
            ssh_logger.error(error_msg)
            return False, error_msg
        
        # 使用paramiko测试连接
        result = self._test_connection_with_paramiko(ip, username, password)
        
        # 记录操作结果
        success, message = result
        if success:
            ssh_logger.info(f"成功连接到服务器 {ip}")
        else:
            ssh_logger.error(f"连接到服务器 {ip} 失败: {message}")
            
        return result
    
    def _test_connection_with_paramiko(self, ip: str, username: str, password: str) -> Tuple[bool, str]:
        """
        使用paramiko测试SSH连接
        
        Args:
            ip (str): 服务器IP地址
            username (str): 用户名
            password (str): 密码
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 创建SSH客户端
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                # 连接到服务器
                ssh_logger.info(f"尝试连接到服务器 {ip}")
                client.connect(
                    hostname=ip,
                    username=username,
                    password=password,
                    timeout=10
                )
                
                # 尝试执行简单命令确认连接正常
                channel = client.get_transport().open_session()
                channel.exec_command('echo "Connection successful"')
                output = self._read_until(channel, '', timeout=2)
                
                ssh_logger.info(f"SSH连接成功: {username}@{ip}")
                return True, "SSH连接成功"
            except Exception as e:
                ssh_logger.error(f"SSH连接失败: {str(e)}")
                return False, f"SSH连接失败: {str(e)}"
            finally:
                ssh_logger.info(f"关闭与服务器 {ip} 的连接")
                client.close()
                
        except Exception as e:
            ssh_logger.error(f"测试SSH连接失败: {str(e)}")
            return False, f"SSH连接失败: {str(e)}"
            
    def get_log_file_path(self) -> str:
        """
        获取SSH操作日志文件路径
        
        Returns:
            str: 日志文件路径
        """
        return ssh_log_file


# 创建SSH密码更新器实例
ssh_password_updater = SSHPasswordUpdater() 