#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码管理表格密码模块
处理密码表格的密码生成和特殊处理功能
"""

import logging
import string
import random
import time
from typing import List, Tuple, Optional

from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from password import password_manager
from ssh_password_updater import ssh_password_updater
from ui.password_manager.ui_guide import show_guide_if_needed

# 配置日志
logger = logging.getLogger(__name__)


class TablePasswordMixin:
    """
    表格密码管理混入类
    
    提供密码生成和特殊处理的方法
    """
    
    def _generate_random_password(self, row: int, col: int, length: int = 12):
        """
        为指定单元格生成随机密码
        
        Args:
            row (int): 行索引
            col (int): 列索引
            length (int, optional): 密码长度. 默认为12
        """
        if row < 0 or row >= self.table.rowCount() or col < 0 or col >= self.table.columnCount():
            return
            
        try:
            # 判断是否是新添加的行
            is_new_row = False
            
            # 首先检查是否有存储在第一个单元格的数据标记
            if self.table.item(row, 0) and self.table.item(row, 0).data(Qt.UserRole + 200):
                is_new_row = True
                logger.info(f"随机密码生成: 根据存储的标记判断第{row+1}行是新添加的行")
            else:
                # 退回到位置判断（作为备用方法）
                is_new_row = (row == self.table.rowCount() - 2)  # 减2是因为有一个按钮行
                logger.info(f"随机密码生成: 根据位置判断第{row+1}行是否为新行: {is_new_row}")
            
            # 检查是否是服务器密码
            is_server_password = False
            ip_item = self.table.item(row, 2)  # IP地址列
            username_item = self.table.item(row, 3)  # 用户名列
            project_item = self.table.item(row, 0)  # 项目名称列
            
            if col == 4 and ip_item and username_item and project_item:
                ip = ip_item.text().strip()
                username = username_item.text().strip()
                project = project_item.text().strip()
                
                # 检查IP格式 (简单验证)
                ip_parts = ip.split('.')
                if len(ip_parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                    is_server_password = True
            
            # 获取当前密码
            password_item = self.table.item(row, col)
            current_password = password_item.text() if password_item else ""
            
            # 生成新密码
            # 确保包含各种字符类型
            lowercase = string.ascii_lowercase
            uppercase = string.ascii_uppercase
            digits = string.digits
            special = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
            
            # 确保至少有一个小写字母、大写字母、数字和特殊字符
            password = [
                random.choice(lowercase),
                random.choice(uppercase),
                random.choice(digits),
                random.choice(special)
            ]
            
            # 填充剩余长度
            all_chars = lowercase + uppercase + digits + special
            for _ in range(length - 4):
                password.append(random.choice(all_chars))
                
            # 打乱密码
            random.shuffle(password)
            new_password = ''.join(password)
            
            # 设置新生成的密码
            password_item.setText(new_password)
            
            # 如果是服务器密码且不是新行，标记为需要SSH更新
            if is_server_password and not is_new_row:
                # 无论是单行还是批量模式，都只标记需要更新，不立即执行
                logger.info(f"已为第{row+1}行生成{length}位随机密码 (服务器密码，需要SSH更新)")
                
                # 保存更新信息到单元格数据中
                password_item.setData(Qt.UserRole + 100, current_password)  # 保存原密码
                password_item.setData(Qt.UserRole + 101, True)  # 标记需要SSH更新
                password_item.setData(Qt.UserRole + 102, ip)  # 保存IP
                password_item.setData(Qt.UserRole + 103, username)  # 保存用户名
                
                # 高亮显示已更改的密码
                highlight_color = QColor("#fff3cd")  # 浅黄色，表示待更新
                password_item.setBackground(highlight_color)
            elif is_server_password and is_new_row:
                # 是服务器密码但是新行，不需要SSH更新
                logger.info(f"已为第{row+1}行生成{length}位随机密码 (服务器密码，新行，跳过SSH更新)")
                
                # 高亮显示已更改的密码，使用不同颜色表示不需要SSH更新
                highlight_color = QColor("#d4edda")  # 浅绿色，表示新行
                password_item.setBackground(highlight_color)
            else:
                # 不是服务器密码，直接设置
                highlight_color = QColor("#cce5ff")  # 浅蓝色
                
                # 记录操作到日志
                row_text = f"第{row+1}行" if col == 4 else f"第{row+1}行"  # 兼容性考虑
                logger.info(f"已为{row_text}生成{length}位随机密码")
                
                password_item.setBackground(highlight_color)
            
        except Exception as e:
            logger.error(f"生成随机密码时出错: {str(e)}")
    
    def _generate_random_passwords(self, cells: List[Tuple[int, int]], length: int):
        """
        为多个单元格生成随机密码
        
        Args:
            cells (List[Tuple[int, int]]): 单元格列表，每个元素为 (行, 列)
            length (int): 密码长度
        """
        if not cells:
            return
            
        # 批量处理前禁用UI更新以提高性能
        self.table.setUpdatesEnabled(False)
        
        try:
            # 遍历所有单元格生成随机密码
            edited_rows = set()
            original_passwords = {}  # 存储原始密码，用于在SSH更新失败时恢复
            
            # 如果正在编辑，取消编辑状态
            if self.editing_row >= 0:
                self.cancel_editing()
                
            # 第一步：保存所有的原始密码
            for row, col in cells:
                if self.table.item(row, col) is not None:
                    original_passwords[(row, col)] = self.table.item(row, col).text()
                    
            # 第二步：生成所有的随机密码
            for row, col in cells:
                # 确保单元格存在
                if self.table.item(row, col) is None:
                    continue
                    
                # 为单元格生成随机密码
                self._generate_random_password(row, col, length)
                edited_rows.add(row)
        finally:
            # 重新启用UI更新
            self.table.setUpdatesEnabled(True)
        
        # 清除链式编辑相关属性
        if hasattr(self, 'pending_edit_rows'):
            delattr(self, 'pending_edit_rows')
        
        if hasattr(self, 'original_confirm_editing'):
            delattr(self, 'original_confirm_editing')
            
        if edited_rows:
            # 将编辑过的行排序
            sorted_rows = sorted(list(edited_rows))
            
            # 批量编辑模式 - 但不进入可视的编辑状态
            logger.info(f"生成密码后一次性进入编辑模式 - 共 {len(sorted_rows)} 行")
            
            # 设置批量编辑标记和数据
            self.batch_editing = True
            self.batch_edited_rows = sorted_rows
            self.original_passwords = original_passwords
            
            # 设置编辑行为最后一个修改的行
            last_row = max(sorted_rows) if sorted_rows else -1
            self.editing_row = last_row
            
            # 只在最后一行下面添加确认和取消按钮
            if hasattr(self, '_add_confirm_cancel_buttons') and last_row >= 0:
                self._add_confirm_cancel_buttons(last_row)
        
        logger.info(f"已为{len(cells)}个密码单元格生成{length}位随机密码")

    def check_ssh_password_updates(self) -> bool:
        """
        在确认编辑时，检查并更新所有标记为需要SSH更新的密码
        
        Returns:
            bool: 是否所有更新都成功，如果有失败则返回False
        """
        # 检查是否是批量编辑模式
        if hasattr(self, 'batch_editing') and self.batch_editing:
            # 批量编辑模式下的SSH更新
            return self._batch_check_ssh_password_updates()
            
        # 以下为原有单行SSH更新逻辑
        # 尝试查找标记为需要SSH更新的单元格
        ssh_updates = []
        
        for row in range(self.table.rowCount()):
            # 判断是否是新添加的行
            is_new_row = False
            
            # 首先检查是否有存储在第一个单元格的数据标记
            if self.table.item(row, 0) and self.table.item(row, 0).data(Qt.UserRole + 200):
                is_new_row = True
                logger.info(f"根据存储的标记判断第{row+1}行是新添加的行")
            else:
                # 退回到位置判断（作为备用方法）
                is_new_row = (row == self.table.rowCount() - 2)  # 减2是因为有一个按钮行
                logger.info(f"根据位置判断第{row+1}行是否为新行: {is_new_row}")
            
            # 跳过新行的SSH更新检查
            if is_new_row:
                logger.info(f"跳过第{row+1}行的SSH更新检查 (新添加的行)")
                continue
                
            password_item = self.table.item(row, 4)  # 密码列 (第5列，索引为4)
            if password_item and password_item.data(Qt.UserRole + 101):
                # 获取保存的SSH更新信息
                ip = password_item.data(Qt.UserRole + 102)
                username = password_item.data(Qt.UserRole + 103)
                old_password = password_item.data(Qt.UserRole + 100)
                new_password = password_item.text()
                
                if ip and username and old_password is not None:
                    # 加入更新列表
                    ssh_updates.append((row, 4, ip, username, old_password, new_password))
                    logger.info(f"找到需要SSH更新的密码 - 行: {row+1}, IP: {ip}, 用户: {username}")
                    
                # 清除标记，无论是否有完整信息
                password_item.setData(Qt.UserRole + 101, None)
        
        # 如果没有需要更新的密码，直接返回成功
        if not ssh_updates:
            logger.info("没有找到需要SSH更新的密码")
            return True
        
        # 显示确认对话框
        if len(ssh_updates) > 0:
            confirm_msg = f"是否要通过SSH更新{len(ssh_updates)}个服务器密码？"
            logger.info(f"显示SSH更新确认对话框: {confirm_msg}")
            reply = QMessageBox.question(None, "SSH密码更新确认", 
                                        confirm_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            
            if reply != QMessageBox.Yes:
                logger.info("用户取消了SSH密码更新")
                return False  # 用户取消，返回失败以阻止本地数据库更新
            
            logger.info(f"用户确认开始SSH更新 {len(ssh_updates)} 个服务器密码")
        
        # 执行SSH密码更新
        failed_updates = []
        success_count = 0
        
        for row, col, ip, username, old_password, new_password in ssh_updates:
            logger.info(f"开始SSH密码更新 - 行: {row+1}, IP: {ip}, 用户: {username}")
            
            # 更新远程密码
            success, message = ssh_password_updater.update_password(
                ip=ip, 
                username=username, 
                old_password=old_password, 
                new_password=new_password
            )
            
            # 记录操作结果
            logger.info("SSH密码更新操作已记录到日志文件: " + ssh_password_updater.get_log_file_path())
            
            # 处理结果
            if success:
                success_count += 1
                logger.info(f"SSH密码更新成功 - 行: {row+1}, IP: {ip}, 用户: {username}")
            else:
                # 处理失败的更新
                failed_updates.append((row, ip, username, message))
                logger.warning(f"更新服务器 {ip} 上用户 {username} 的密码失败: {message}")
        
        # 显示操作结果
        if success_count > 0:
            success_msg = f"成功更新了 {success_count}/{len(ssh_updates)} 个服务器的密码。"
            logger.info(success_msg)
            
            # 显示成功消息
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setWindowTitle("服务器密码更新成功")
            msg_box.setText(success_msg)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
            
            # 手动触发表格刷新以确保内容正确显示
            if hasattr(self, 'current_owner') and self.current_owner:
                if hasattr(self, 'search_mode') and self.search_mode:
                    self._refresh_search_results()
                else:
                    self._load_passwords_internal(self.current_owner)
        
        # 如果有失败的更新，显示警告消息
        if failed_updates:
            error_msg = "以下服务器的密码更新失败：\n\n"
            for row, ip, username, message in failed_updates:
                error_msg += f"• 行 {row+1}: {ip} ({username}) - {message}\n"
            
            error_msg += "\n您可能需要手动更新这些服务器的密码。"
            logger.warning(f"SSH密码更新结果: 失败 {len(failed_updates)}/{len(ssh_updates)} 个")
            
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setWindowTitle("部分服务器更新失败")
            msg_box.setText(error_msg)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
        
        # 手动触发表格刷新以确保内容正确显示
        if hasattr(self, 'current_owner') and self.current_owner:
            if hasattr(self, 'search_mode') and self.search_mode:
                self._refresh_search_results()
            else:
                self._load_passwords_internal(self.current_owner)
        
        return True

    def _batch_check_ssh_password_updates(self) -> bool:
        """
        批量编辑模式下的SSH密码更新处理
        
        Returns:
            bool: 是否所有更新都成功，如果有失败则返回False以阻止本地数据库更新
        """
        if not hasattr(self, 'batch_edited_rows') or not self.batch_edited_rows:
            # 清除批量编辑状态
            self.batch_editing = False
            logger.debug("批量SSH更新: 没有待编辑的行，跳过更新")
            return True
            
        # 查找需要SSH更新的密码
        ssh_updates = []
        
        logger.info(f"批量SSH更新: 开始检查 {len(self.batch_edited_rows)} 行数据")
        
        for row in self.batch_edited_rows:
            # 判断是否是新添加的行
            is_new_row = False
            
            # 首先检查是否有存储在第一个单元格的数据标记
            if self.table.item(row, 0) and self.table.item(row, 0).data(Qt.UserRole + 200):
                is_new_row = True
                logger.info(f"批量SSH更新: 根据存储的标记判断第{row+1}行是新添加的行")
            else:
                # 退回到位置判断（作为备用方法）
                is_new_row = (row == self.table.rowCount() - 2)  # 减2是因为有一个按钮行
                logger.info(f"批量SSH更新: 根据位置判断第{row+1}行是否为新行: {is_new_row}")
            
            # 跳过新行的SSH更新检查
            if is_new_row:
                logger.info(f"批量SSH更新: 跳过第{row+1}行 (新添加的行)")
                continue
                
            # 检查是否有IP和用户名
            ip_item = self.table.item(row, 2)  # IP地址列
            username_item = self.table.item(row, 3)  # 用户名列
            password_item = self.table.item(row, 4)  # 密码列
            project_item = self.table.item(row, 0)  # 项目名称列
            
            if ip_item and username_item and password_item and project_item:
                ip = ip_item.text().strip()
                username = username_item.text().strip()
                new_password = password_item.text()
                project = project_item.text().strip()
                
                # 获取原始密码
                original_password = self.original_passwords.get((row, 4), "")
                
                # 只有当密码发生变化时才需要SSH更新
                if original_password != new_password:
                    # 检查IP格式 (简单验证)
                    ip_parts = ip.split('.')
                    if len(ip_parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                        # 加入更新列表
                        ssh_updates.append((row, 4, ip, username, original_password, new_password, project))
                        logger.info(f"找到需要SSH更新的密码 - 行: {row+1}, IP: {ip}, 用户: {username}, 项目: {project}")
                else:
                    logger.info(f"跳过第{row+1}行的SSH更新检查 (密码未变更)")
        
        # 如果没有需要更新的密码，直接返回成功
        if not ssh_updates:
            logger.info("批量SSH更新: 没有找到需要SSH更新的密码")
            # 清除批量编辑状态
            self.batch_editing = False
            return True
        
        # 执行SSH密码更新
        success_updates = []
        failed_updates = []
        all_failed = True  # 是否所有更新都失败
        
        logger.info(f"批量SSH更新: 开始更新 {len(ssh_updates)} 个服务器密码")
        
        for row, col, ip, username, old_password, new_password, project in ssh_updates:
            logger.info(f"批量SSH更新: 开始更新 - 行: {row+1}, IP: {ip}, 用户: {username}, 项目: {project}")
            
            # 更新远程密码
            success, message = ssh_password_updater.update_password(
                ip=ip, 
                username=username, 
                old_password=old_password, 
                new_password=new_password
            )
            
            # 记录操作结果
            logger.info("SSH密码更新操作已记录到日志文件: " + ssh_password_updater.get_log_file_path())
            
            # 处理结果
            if success:
                success_updates.append((row, ip, username, project))
                all_failed = False  # 至少有一个成功
                logger.info(f"批量SSH更新成功 - 行: {row+1}, IP: {ip}, 用户: {username}, 项目: {project}")
            else:
                failed_updates.append((row, ip, username, message, project))
                logger.warning(f"批量SSH更新失败 - 行: {row+1}, IP: {ip}, 用户: {username}, 项目: {project}, 错误: {message}")
                
                # 将单元格恢复为原始密码
                if (row, col) in self.original_passwords:
                    self.table.item(row, col).setText(self.original_passwords[(row, col)])
                    logger.info(f"已恢复第{row+1}行的原始密码")
        
        # 显示结果消息
        message = ""
        if success_updates:
            message += "以下服务器密码更新成功：\n\n"
            for row, ip, username, project in success_updates:
                message += f"• 第{row+1}行: {project} - {ip} ({username})\n"
                
        if failed_updates:
            if message:
                message += "\n\n"
            message += "以下服务器密码更新失败（这些密码将不会更新）：\n\n"
            for row, ip, username, error, project in failed_updates:
                message += f"• 第{row+1}行: {project} - {ip} ({username}) - {error}\n"
        
        if message:
            # 使用信息对话框显示综合结果
            result_title = "SSH密码更新结果"
            logger.info(f"显示SSH更新结果对话框: 成功 {len(success_updates)}/{len(ssh_updates)}, 失败 {len(failed_updates)}/{len(ssh_updates)}")
            msg_box = QMessageBox()
            msg_box.setWindowTitle(result_title)
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
        
        # 清除批量编辑状态
        self.batch_editing = False
        
        # 如果所有更新都失败，返回False以阻止本地数据库更新
        if all_failed and failed_updates:
            logger.warning(f"批量SSH更新: 所有 {len(failed_updates)} 个更新都失败，取消本地数据库更新")
            return False
            
        # 返回True表示可以继续更新本地数据库
        logger.info(f"批量SSH更新完成: 成功 {len(success_updates)}/{len(ssh_updates)} 个，继续更新本地数据库")
        return True 

    def _generate_and_update_passwords(self, cells: List[Tuple[int, int]], length: int):
        """
        为选中的单元格生成随机密码并更新到服务器
        
        Args:
            cells (List[Tuple[int, int]]): 单元格列表，每个元素为 (行, 列)
            length (int): 密码长度
        """
        if not cells:
            return
            
        # 显示密码更新引导
        if hasattr(self.table, 'parent'):
            parent = self.table.parent()
            if parent:
                show_guide_if_needed("password_update", parent)
        
        # 获取当前选择的所有者
        owner = self.current_owner
        
        # 显示确认对话框
        from ui.password_manager.ui_utils import show_confirmation
        confirm_message = f"将为选中的 {len(cells)} 个单元格生成随机密码，并尝试更新到对应的服务器。\n\n" \
                         f"此操作不可撤销，请确认："
        if not show_confirmation(self.table.parent(), "更新密码", confirm_message):
            logger.info("用户取消了服务器密码更新")
            return
        
        # 获取被选中的服务器信息，用于更新密码
        servers_to_update = []
        for row, col in cells:
            # 确保单元格存在且列为密码列(4)
            if col != 4 or not self.table.item(row, col):
                continue
            
            # 获取IP地址和用户名，用于判断是否需要更新服务器密码
            ip_item = self.table.item(row, 2)  # IP地址列
            username_item = self.table.item(row, 3)  # 用户名列
            project_item = self.table.item(row, 0)  # 项目名称列
            password_item = self.table.item(row, col)  # 密码单元格
            
            # 如果存在IP地址和用户名，则加入待更新列表
            if ip_item and username_item and project_item and password_item:
                ip = ip_item.text().strip()
                username = username_item.text().strip()
                project = project_item.text().strip()
                current_password = password_item.text().strip()
                
                # 简单验证IP格式
                ip_parts = ip.split('.')
                is_valid_ip = len(ip_parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts)
                
                if ip and username and is_valid_ip:
                    # 获取在原始数据中的索引，用于后续更新本地数据库
                    real_index = self._get_real_row_index(row)
                    
                    servers_to_update.append({
                        'row': row,
                        'ip': ip,
                        'username': username,
                        'project': project,
                        'current_password': current_password,
                        'new_password': '',  # 将在下一步生成
                        'real_index': real_index
                    })
        
        # 如果没有有效的服务器信息，给出提示
        if not servers_to_update:
            from ui.password_manager.ui_utils import show_message
            show_message(
                self.table.parent(),
                "无法更新服务器",
                "没有找到有效的服务器信息。\n\n请确保选中的密码单元格对应的记录包含有效的IP地址和用户名。",
                QMessageBox.Warning
            )
            return
        
        # 批量处理前禁用UI更新以提高性能
        self.table.setUpdatesEnabled(False)
        
        try:
            # 为每个服务器生成新密码并进行更新
            logger.info(f"开始更新{len(servers_to_update)}个服务器的密码")
            
            success_count = 0
            for server in servers_to_update:
                row = server['row']
                ip = server['ip']
                username = server['username']
                project = server['project']
                current_password = server['current_password']
                
                # 生成新密码
                new_password = self._generate_secure_password(length)
                server['new_password'] = new_password
                
                # 日志记录
                logger.info(f"开始更新服务器密码 - 行: {row+1}, 项目: {project}, IP: {ip}, 用户: {username}")
                
                # 更新到服务器
                success, message = ssh_password_updater.update_password(
                    ip=ip,
                    username=username,
                    old_password=current_password,
                    new_password=new_password
                )
                
                # 处理结果
                if success:
                    # 更新UI显示
                    password_item = self.table.item(row, 4)  # 密码列
                    if password_item:
                        password_item.setText(new_password)
                        # 设置背景色为绿色，表示成功更新
                        password_item.setBackground(QColor("#d4edda"))
                    
                    # 更新本地数据库
                    real_index = server['real_index']
                    if real_index is not None:
                        # 获取当前行的完整数据
                        data = []
                        for col in range(self.table.columnCount()):
                            item = self.table.item(row, col)
                            text = item.text() if item else ""
                            data.append(text)
                        
                        # 更新本地数据库，但跳过SSH更新步骤（因为已经完成）
                        update_success, update_message = password_manager.update_password(
                            owner, real_index, data, skip_server_sync=True
                        )
                        
                        if update_success:
                            logger.info(f"成功更新本地数据库 - 所有者: {owner}, 行: {row+1}")
                        else:
                            logger.error(f"更新本地数据库失败 - 所有者: {owner}, 行: {row+1}, 错误: {update_message}")
                    
                    success_count += 1
                    logger.info(f"SSH密码更新成功 - 行: {row+1}, IP: {ip}, 用户: {username}")
                else:
                    # 更新失败，设置背景色为红色
                    password_item = self.table.item(row, 4)
                    if password_item:
                        password_item.setBackground(QColor("#f8d7da"))
                        
                    # 显示错误信息
                    from ui.password_manager.ui_utils import show_message
                    show_message(
                        self.table.parent(),
                        "密码更新失败",
                        f"更新服务器 {ip} 的密码失败：\n\n{message}",
                        QMessageBox.Warning
                    )
                    
                    logger.error(f"SSH密码更新失败 - 行: {row+1}, IP: {ip}, 用户: {username}, 错误: {message}")
        
        finally:
            # 重新启用UI更新
            self.table.setUpdatesEnabled(True)
        
        # 显示结果
        logger.info(f"成功更新了 {success_count}/{len(servers_to_update)} 个服务器的密码。")
        
        from ui.password_manager.ui_utils import show_message
        if success_count > 0:
            result_message = f"成功更新了 {success_count}/{len(servers_to_update)} 个服务器的密码。"
            if success_count < len(servers_to_update):
                result_message += "\n\n部分更新失败，请检查错误信息。"
            show_message(self.table.parent(), "密码更新完成", result_message, QMessageBox.Information)
        else:
            show_message(self.table.parent(), "密码更新失败", "所有服务器密码更新均失败，请检查错误信息。", QMessageBox.Warning)
    
    def _update_local_password(self, row: int, new_password: str) -> bool:
        """
        更新本地数据库中的密码
        
        Args:
            row (int): 行索引
            new_password (str): 新密码
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取真实行索引
            real_row = self._get_real_row_index(row) if hasattr(self, 'search_mode') and self.search_mode else row
            
            if real_row is None:
                logger.error(f"无法获取第{row+1}行的真实索引")
                return False
                
            # 获取当前所有者
            owner = self.current_owner
            
            # 获取该所有者的所有密码
            passwords = password_manager.get_passwords_by_owner(owner)
            
            # 检查索引是否有效
            if 0 <= real_row < len(passwords):
                # 获取当前密码记录
                password_record = passwords[real_row]
                
                # 更新密码字段
                password_record[4] = new_password
                
                # 更新数据库
                success, message = password_manager.update_password(owner, real_row, password_record, skip_server_sync=True)
                
                if success:
                    logger.info(f"成功更新本地数据库 - 所有者: {owner}, 行: {real_row+1}")
                    return True
                else:
                    logger.error(f"更新本地数据库失败 - 所有者: {owner}, 行: {real_row+1}, 错误: {message}")
                    return False
            else:
                logger.error(f"无效的行索引: {real_row} (总行数: {len(passwords)})")
                return False
                
        except Exception as e:
            logger.error(f"更新本地数据库时出错: {str(e)}")
            return False
    
    def _generate_secure_password(self, length: int) -> str:
        """
        生成一个安全的随机密码
        
        Args:
            length (int): 密码长度
            
        Returns:
            str: 生成的随机密码
        """
        # 确保包含各种字符类型
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
        
        # 确保至少有一个小写字母、大写字母、数字和特殊字符
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(special)
        ]
        
        # 填充剩余长度
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(random.choice(all_chars))
            
        # 打乱密码
        random.shuffle(password)
        return ''.join(password) 