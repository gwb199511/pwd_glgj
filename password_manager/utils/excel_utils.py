#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Excel导入导出工具模块
提供Excel文件导入导出功能
"""

import os
import sys
import logging
import traceback
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

# 确保可以找到配置
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入配置
from config import PASSWORD_COLUMNS, REQUIRED_FIELDS
from core.encrypt import encryptor
from features.audit.audit_log import audit_logger, OP_TYPE_EXPORT, OP_TYPE_IMPORT, OP_RESULT_SUCCESS, OP_RESULT_FAIL

# 配置日志
logger = logging.getLogger(__name__)


class ExcelExporter:
    """
    Excel导出工具类
    提供将密码数据导出为Excel文件的功能
    """
    
    def __init__(self):
        """初始化Excel导出工具"""
        pass
        
    def export_to_excel(self, passwords: List[List[str]], owner: str, file_path: str) -> Tuple[bool, str]:
        """
        导出密码记录到Excel文件
        
        Args:
            passwords: 密码记录列表
            owner: 所有者
            file_path: 导出文件路径
            
        Returns:
            成功标志和消息
        """
        try:
            # 创建DataFrame
            df = pd.DataFrame(passwords, columns=PASSWORD_COLUMNS)
            
            # 创建Excel写入器
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                # 写入数据
                df.to_excel(writer, sheet_name=owner, index=False)
                
                # 获取xlsxwriter工作簿和工作表对象
                workbook = writer.book
                worksheet = writer.sheets[owner]
                
                # 定义格式
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                required_format = workbook.add_format({
                    'bold': True,
                    'border': 1
                })
                
                cell_format = workbook.add_format({
                    'border': 1
                })
                
                # 应用标题格式
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # 设置列宽
                worksheet.set_column('A:A', 20)  # 项目名称
                worksheet.set_column('B:B', 20)  # IP地址
                worksheet.set_column('C:C', 20)  # 所在区域
                worksheet.set_column('D:D', 20)  # 网络类型
                worksheet.set_column('E:E', 25)  # 账户
                worksheet.set_column('F:F', 25)  # 密码
                worksheet.set_column('G:G', 30)  # 其他账号
                worksheet.set_column('H:H', 20)  # 功能
                
                # 应用单元格格式
                for row_num in range(1, len(df) + 1):
                    for col_num, value in enumerate(df.iloc[row_num-1]):
                        if col_num in REQUIRED_FIELDS:
                            worksheet.write(row_num, col_num, value, required_format)
                        else:
                            worksheet.write(row_num, col_num, value, cell_format)
                
                # 冻结首行
                worksheet.freeze_panes(1, 0)
                
                # 添加导出信息
                info_format = workbook.add_format({
                    'italic': True,
                    'font_color': '#6c757d'
                })
                
                row_count = len(df) + 3
                export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                worksheet.write(row_count, 0, f"导出时间: {export_time}", info_format)
                worksheet.write(row_count + 1, 0, f"所有者: {owner}", info_format)
                worksheet.write(row_count + 2, 0, f"记录数: {len(df)}", info_format)
            
            # 记录审计日志
            try:
                # 尝试导入审计日志模块
                sys.path.insert(0, current_dir)
                from features.audit.audit_log import AuditLogger
                
                audit_logger = AuditLogger()
                details = f"导出Excel文件 '{os.path.basename(file_path)}' 包含 {owner} 的 {len(passwords)} 条密码记录"
                    
                audit_logger.log_operation(
                    operation_type="export",
                    result="success",
                    details=details,
                    target=owner
                )
            except Exception as e:
                logger.error(f"记录审计日志时出错: {str(e)}")
                
            return True, f"成功导出 {len(passwords)} 条记录到 {file_path}"
            
        except Exception as e:
            error_message = f"导出Excel文件时出错: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            
            # 记录失败的审计日志
            try:
                from features.audit.audit_log import AuditLogger
                
                audit_logger = AuditLogger()
                details = f"导出Excel文件 '{os.path.basename(file_path)}' 失败: {str(e)}"
                    
                audit_logger.log_operation(
                    operation_type="export",
                    result="failure",
                    details=details,
                    target=owner
                )
            except Exception as log_err:
                logger.error(f"记录失败审计日志时出错: {str(log_err)}")
                
            return False, error_message
            
    def export_multiple_to_excel(self, owners_data: Dict[str, List[List[str]]], file_path: str) -> Tuple[bool, str]:
        """
        将多个人员的密码记录导出到同一个Excel文件的不同工作表中
        
        Args:
            owners_data (Dict[str, List[List[str]]]): 人员名称与密码记录的字典
            file_path (str): 保存路径
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not owners_data:
                return False, "没有数据可导出"
                
            # 记录总记录数
            total_records = sum(len(passwords) for passwords in owners_data.values())
            if total_records == 0:
                return False, "没有数据可导出"
                
            # 创建Excel工作簿
            wb = Workbook()
            
            # 删除默认创建的工作表
            default_sheet = wb.active
            wb.remove(default_sheet)
            
            # 处理每个人员的数据
            first_sheet = None
            total_exported = 0
            
            for owner, passwords in owners_data.items():
                if not passwords:
                    continue
                    
                # 创建工作表
                # 工作表名称不能超过31个字符，且不能包含[]:?*\/
                sheet_name = f"{owner}的密码记录"
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:28] + "..."
                    
                # 确保工作表名称唯一
                sheet_names = [ws.title for ws in wb.worksheets]
                if sheet_name in sheet_names:
                    # 添加序号
                    for i in range(1, 100):
                        new_name = f"{sheet_name[:27]}({i})"
                        if new_name not in sheet_names:
                            sheet_name = new_name
                            break
                
                ws = wb.create_sheet(title=sheet_name)
                
                # 记录第一个工作表
                if first_sheet is None:
                    first_sheet = ws
                
                # 创建DataFrame
                df = pd.DataFrame(passwords, columns=PASSWORD_COLUMNS)
                
                # 写入标题行
                for col_idx, col_name in enumerate(PASSWORD_COLUMNS, start=1):
                    cell = ws.cell(row=1, column=col_idx, value=col_name)
                    # 设置标题样式
                    cell.font = Font(bold=True, size=12)
                    cell.fill = PatternFill(start_color="E6F0F9", end_color="E6F0F9", fill_type="solid")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    
                    # 设置列宽
                    col_width = max(len(col_name) * 2, 15)
                    if col_name == "项目名称" or col_name == "功能":
                        col_width = 20
                    elif col_name == "IP地址" or col_name == "所在区域" or col_name == "网络类型":
                        col_width = 20
                    elif col_name == "密码" or col_name == "账户":
                        col_width = 25  # 设置密码和账户列宽度为25
                    elif col_name == "其他账号":
                        col_width = 30
                    
                    ws.column_dimensions[get_column_letter(col_idx)].width = col_width
                
                # 定义边框样式
                thin_border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
                
                # 写入数据行
                for row_idx, row in enumerate(passwords, start=2):
                    for col_idx, value in enumerate(row, start=1):
                        cell = ws.cell(row=row_idx, column=col_idx, value=value)
                        cell.border = thin_border
                        cell.alignment = Alignment(vertical="center", wrap_text=True)
                        
                        # 高亮必填字段
                        if col_idx - 1 in REQUIRED_FIELDS:
                            cell.font = Font(bold=True)
                
                # 创建表格样式
                # 由于Excel中的表格名称必须唯一，为每个表格生成唯一名称
                table_name = f"Table_{owner.replace(' ', '_')}"
                # 替换非法字符
                table_name = ''.join(c for c in table_name if c.isalnum() or c == '_')
                # 表名最大长度为255个字符
                if len(table_name) > 255:
                    table_name = table_name[:255]
                # 确保不以数字开头
                if table_name[0].isdigit():
                    table_name = f"T_{table_name}"
                
                table_ref = f"A1:{get_column_letter(len(PASSWORD_COLUMNS))}{len(passwords) + 1}"
                table = Table(displayName=table_name, ref=table_ref)
                style = TableStyleInfo(
                    name="TableStyleMedium2",
                    showFirstColumn=False,
                    showLastColumn=False,
                    showRowStripes=True,
                    showColumnStripes=False
                )
                table.tableStyleInfo = style
                ws.add_table(table)
                
                # 冻结首行
                ws.freeze_panes = "A2"
                
                # 添加记录数
                total_exported += len(passwords)
            
            # 创建摘要工作表
            summary_sheet = wb.create_sheet(title="导出摘要", index=0)
            
            # 设置摘要工作表内容
            summary_sheet.column_dimensions['A'].width = 20
            summary_sheet.column_dimensions['B'].width = 40
            
            # 标题
            cell = summary_sheet.cell(row=1, column=1, value="密码记录导出摘要")
            cell.font = Font(bold=True, size=14)
            summary_sheet.merge_cells('A1:B1')
            cell.alignment = Alignment(horizontal="center")
            
            # 导出信息
            export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            row = 3
            summary_sheet.cell(row=row, column=1, value="导出时间:").font = Font(bold=True)
            summary_sheet.cell(row=row, column=2, value=export_time)
            
            row += 1
            summary_sheet.cell(row=row, column=1, value="总人员数:").font = Font(bold=True)
            summary_sheet.cell(row=row, column=2, value=len(owners_data))
            
            row += 1
            summary_sheet.cell(row=row, column=1, value="总记录数:").font = Font(bold=True)
            summary_sheet.cell(row=row, column=2, value=total_exported)
            
            row += 2
            summary_sheet.cell(row=row, column=1, value="导出人员详情:").font = Font(bold=True)
            
            # 添加每个人员的记录数
            for owner, passwords in owners_data.items():
                if passwords:
                    row += 1
                    summary_sheet.cell(row=row, column=1, value=owner)
                    summary_sheet.cell(row=row, column=2, value=f"{len(passwords)} 条记录")
            
            row += 2
            cell = summary_sheet.cell(row=row, column=1, value="此文件包含敏感信息，请妥善保管!")
            cell.font = Font(bold=True, color="FF0000")
            summary_sheet.merge_cells(f'A{row}:B{row}')
            
            # 保存文件
            wb.save(file_path)
            
            # 记录审计日志
            owners_str = ", ".join(owners_data.keys())
            audit_logger.log_operation(
                operation_type=OP_TYPE_EXPORT,
                result=OP_RESULT_SUCCESS,
                details=f"导出多人员密码记录到Excel文件: {os.path.basename(file_path)}，总记录数: {total_exported}，人员: {owners_str}",
                target="多人员/Excel导出"
            )
            
            return True, f"成功导出 {total_exported} 条记录，涉及 {len(owners_data)} 个人员"
            
        except Exception as e:
            logger.error(f"导出多人员Excel时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # 记录审计日志
            audit_logger.log_operation(
                operation_type=OP_TYPE_EXPORT,
                result=OP_RESULT_FAIL,
                details=f"导出多人员密码记录到Excel文件失败: {str(e)}",
                target="多人员/Excel导出"
            )
            
            return False, f"导出失败: {str(e)}"
            
    def generate_template(self, file_path: str) -> Tuple[bool, str]:
        """
        生成Excel导入模板
        
        Args:
            file_path (str): 保存路径
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 创建工作簿
            wb = Workbook()
            ws = wb.active
            ws.title = "密码记录模板"
            
            # 写入标题行
            for col_idx, col_name in enumerate(PASSWORD_COLUMNS, start=1):
                cell = ws.cell(row=1, column=col_idx, value=col_name)
                # 设置标题样式
                cell.font = Font(bold=True, size=12)
                cell.fill = PatternFill(start_color="E6F0F9", end_color="E6F0F9", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                
                # 设置列宽
                col_width = max(len(col_name) * 2, 15)
                if col_name == "项目名称" or col_name == "功能":
                    col_width = 20
                elif col_name == "IP地址" or col_name == "所在区域" or col_name == "网络类型":
                    col_width = 20
                elif col_name == "密码" or col_name == "账户":
                    col_width = 25  # 设置密码和账户列宽度为25
                elif col_name == "其他账号":
                    col_width = 30
                
                ws.column_dimensions[get_column_letter(col_idx)].width = col_width
            
            # 添加示例行
            example_data = [
                "示例-OA系统", "系统管理", "192.168.1.100", "admin", "P@ssw0rd", 
                "北京总部", "内网", "备用账号: auditor"
            ]
            
            for col_idx, value in enumerate(example_data, start=1):
                cell = ws.cell(row=2, column=col_idx, value=value)
                cell.font = Font(italic=True)
            
            # 添加说明
            instructions = [
                "使用说明:",
                "1. 标记 * 的列为必填项 (项目名称、IP地址、账户、密码)",
                "2. 请按照示例行的格式填写数据",
                "3. 填写完成后删除示例行",
                "4. 保存文件后使用\"导入\"功能导入数据"
            ]
            
            for i, text in enumerate(instructions, start=4):
                cell = ws.cell(row=i, column=1, value=text)
                if i == 4:
                    cell.font = Font(bold=True)
                ws.merge_cells(
                    start_row=i,
                    start_column=1,
                    end_row=i,
                    end_column=len(PASSWORD_COLUMNS)
                )
            
            # 标记必填列
            for col_idx in [x+1 for x in REQUIRED_FIELDS]:
                cell = ws.cell(row=1, column=col_idx)
                cell.value = f"{cell.value} *"
                cell.fill = PatternFill(start_color="FFD9D9", end_color="FFD9D9", fill_type="solid")
            
            # 保存文件
            wb.save(file_path)
            
            return True, "成功生成导入模板"
            
        except Exception as e:
            logger.error(f"生成Excel模板时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False, f"生成模板失败: {str(e)}"


class ExcelImporter:
    """
    Excel导入器，负责从Excel文件导入密码记录
    """
    
    def __init__(self):
        """
        初始化Excel导入器
        """
        self.columns = PASSWORD_COLUMNS
        self.required_indices = REQUIRED_FIELDS
        
    def import_from_excel(self, file_path: str, owner: str) -> Tuple[bool, str, List[List[str]]]:
        """
        从Excel文件导入密码记录
        
        Args:
            file_path (str): Excel文件路径
            owner (str): 所有者
            
        Returns:
            Tuple[bool, str, List[List[str]]]: (成功状态, 消息, 导入的记录)
        """
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在", []
                
            # 读取Excel
            df = pd.read_excel(file_path)
            
            # 检查列是否匹配
            for idx, required_col in enumerate(self.columns):
                # 检查必需列是否存在（去掉可能添加的*号）
                if not any(col.replace(" *", "") == required_col for col in df.columns):
                    return False, f"文件格式不正确，缺少必要的列: {required_col}", []
            
            # 重命名列（处理可能的*号）
            col_mapping = {}
            for excel_col in df.columns:
                for req_col in self.columns:
                    if excel_col.replace(" *", "") == req_col:
                        col_mapping[excel_col] = req_col
                        break
            
            df = df.rename(columns=col_mapping)
            
            # 转换为列表
            records = []
            validation_errors = []
            
            for i, row in df.iterrows():
                # 跳过空行
                if pd.isna(row).all():
                    continue
                    
                # 转换行为列表
                record = []
                for col in self.columns:
                    value = row.get(col, "")
                    # 处理NaN
                    if pd.isna(value):
                        value = ""
                    record.append(str(value))
                
                # 验证必填字段
                valid = True
                for idx in self.required_indices:
                    if idx < len(record) and not record[idx]:
                        validation_errors.append(f"第 {i+2} 行: {self.columns[idx]} 不能为空")
                        valid = False
                
                if valid:
                    records.append(record)
            
            # 检查验证错误
            if validation_errors:
                return False, f"导入验证失败:\n" + "\n".join(validation_errors), []
            
            # 加密密码字段
            for record in records:
                if len(record) > 4:
                    record[4] = encryptor.encrypt(record[4])
            
            # 记录审计日志
            audit_logger.log_operation(
                operation_type=OP_TYPE_IMPORT,
                result=OP_RESULT_SUCCESS,
                details=f"从Excel文件导入密码记录: {os.path.basename(file_path)}，记录数: {len(records)}",
                target=f"{owner}/Excel导入"
            )
            
            return True, f"成功导入 {len(records)} 条记录", records
            
        except Exception as e:
            logger.error(f"导入Excel时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # 记录审计日志
            audit_logger.log_operation(
                operation_type=OP_TYPE_IMPORT,
                result=OP_RESULT_FAIL,
                details=f"从Excel文件导入密码记录失败: {str(e)}",
                target=f"{owner}/Excel导入"
            )
            
            return False, f"导入失败: {str(e)}", []


# 创建单例实例
excel_exporter = ExcelExporter()
excel_importer = ExcelImporter() 