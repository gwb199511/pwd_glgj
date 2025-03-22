#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
密码生成器模块，提供密码生成功能
"""

import random
import string
import logging
import math
from typing import List, Dict, Optional, Set, Union

# 配置日志
logger = logging.getLogger(__name__)

class PasswordGenerator:
    """
    密码生成器类，用于生成各种类型的密码
    """
    
    # 字符集常量
    LOWERCASE = string.ascii_lowercase  # 小写字母
    UPPERCASE = string.ascii_uppercase  # 大写字母
    DIGITS = string.digits  # 数字
    SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?/"  # 特殊符号
    
    # 容易混淆的字符
    SIMILAR_CHARS = "Il1O0o"
    
    def __init__(self):
        """
        初始化密码生成器
        """
        logger.debug("密码生成器初始化")
    
    def generate_password(self, 
                          length: int = 16, 
                          use_lowercase: bool = True,
                          use_uppercase: bool = True, 
                          use_digits: bool = True, 
                          use_symbols: bool = True,
                          exclude_similar: bool = False) -> str:
        """
        生成密码
        
        Args:
            length (int): 密码长度
            use_lowercase (bool): 是否使用小写字母
            use_uppercase (bool): 是否使用大写字母
            use_digits (bool): 是否使用数字
            use_symbols (bool): 是否使用特殊符号
            exclude_similar (bool): 是否排除相似字符
            
        Returns:
            str: 生成的密码
        """
        # 验证密码长度
        if length < 1:
            logger.warning(f"无效的密码长度: {length}，使用默认值16")
            length = 16
        
        # 构建字符集
        chars = ""
        if use_lowercase:
            chars += self.LOWERCASE
        if use_uppercase:
            chars += self.UPPERCASE
        if use_digits:
            chars += self.DIGITS
        if use_symbols:
            chars += self.SYMBOLS
        
        # 如果没有选择任何字符集，默认使用小写字母
        if not chars:
            logger.warning("未选择任何字符集，使用小写字母")
            chars = self.LOWERCASE
        
        # 排除相似字符
        if exclude_similar:
            for char in self.SIMILAR_CHARS:
                chars = chars.replace(char, '')
        
        # 生成密码
        try:
            password = ''.join(random.choice(chars) for _ in range(length))
            logger.debug(f"生成了长度为{length}的密码")
            return password
        except Exception as e:
            logger.error(f"生成密码时出错: {str(e)}")
            return "密码生成失败"
    
    def generate_multiple_passwords(self, 
                                    count: int = 5, 
                                    **kwargs) -> List[str]:
        """
        生成多个密码
        
        Args:
            count (int): 密码数量
            **kwargs: 传递给generate_password的参数
            
        Returns:
            List[str]: 生成的密码列表
        """
        if count < 1:
            logger.warning(f"无效的密码数量: {count}，使用默认值5")
            count = 5
        
        passwords = []
        for _ in range(count):
            passwords.append(self.generate_password(**kwargs))
        
        logger.debug(f"生成了{count}个密码")
        return passwords
    
    def calculate_entropy(self, password: str) -> float:
        """
        计算密码熵值
        
        Args:
            password (str): 密码
            
        Returns:
            float: 密码熵值（比特）
        """
        if not password:
            return 0.0
        
        # 确定字符集大小
        char_set_size = 0
        has_lowercase = any(c in self.LOWERCASE for c in password)
        has_uppercase = any(c in self.UPPERCASE for c in password)
        has_digits = any(c in self.DIGITS for c in password)
        has_symbols = any(c in self.SYMBOLS for c in password)
        
        if has_lowercase:
            char_set_size += len(self.LOWERCASE)
        if has_uppercase:
            char_set_size += len(self.UPPERCASE)
        if has_digits:
            char_set_size += len(self.DIGITS)
        if has_symbols:
            char_set_size += len(self.SYMBOLS)
        
        # 计算熵值: 密码长度 * log2(字符集大小)
        entropy = len(password) * math.log2(max(char_set_size, 1))
        return entropy
    
    def evaluate_password_strength(self, password: str) -> Dict[str, Union[str, float]]:
        """
        评估密码强度
        
        Args:
            password (str): 密码
            
        Returns:
            Dict: 包含评估结果的字典
                {
                    'strength': 强度级别 ('弱', '中', '强', '非常强'),
                    'entropy': 熵值,
                    'suggestions': 改进建议
                }
        """
        result = {
            'strength': '',
            'entropy': 0.0,
            'suggestions': []
        }
        
        if not password:
            result['strength'] = '弱'
            result['suggestions'].append('密码不能为空')
            return result
        
        # 计算熵值
        entropy = self.calculate_entropy(password)
        result['entropy'] = entropy
        
        # 基于熵值评估强度
        if entropy < 40:
            result['strength'] = '弱'
        elif entropy < 60:
            result['strength'] = '中'
        elif entropy < 80:
            result['strength'] = '强'
        else:
            result['strength'] = '非常强'
        
        # 提供改进建议
        suggestions = []
        if len(password) < 8:
            suggestions.append('增加密码长度(至少8个字符)')
        
        # 检查字符多样性
        has_lowercase = any(c in self.LOWERCASE for c in password)
        has_uppercase = any(c in self.UPPERCASE for c in password)
        has_digits = any(c in self.DIGITS for c in password)
        has_symbols = any(c in self.SYMBOLS for c in password)
        
        if not has_lowercase:
            suggestions.append('添加小写字母')
        if not has_uppercase:
            suggestions.append('添加大写字母')
        if not has_digits:
            suggestions.append('添加数字')
        if not has_symbols:
            suggestions.append('添加特殊符号')
        
        result['suggestions'] = suggestions
        
        return result
    
    def generate_default_password(self) -> str:
        """
        生成默认密码（16位，包含所有字符类型）
        
        Returns:
            str: 生成的密码
        """
        return self.generate_password(16, True, True, True, True, False)
    
    def generate_numeric_password(self, length: int = 6) -> str:
        """
        生成纯数字密码
        
        Args:
            length (int): 密码长度
            
        Returns:
            str: 生成的密码
        """
        return self.generate_password(length, False, False, True, False, False)
    
    def generate_complex_password(self, length: int = 16) -> str:
        """
        生成复杂密码（包含所有字符类型，排除相似字符）
        
        Args:
            length (int): 密码长度
            
        Returns:
            str: 生成的密码
        """
        return self.generate_password(length, True, True, True, True, True)


# 简单测试函数
def test():
    """
    测试密码生成器功能
    """
    generator = PasswordGenerator()
    
    print("默认密码:", generator.generate_default_password())
    print("数字密码:", generator.generate_numeric_password())
    print("复杂密码:", generator.generate_complex_password())
    
    password = generator.generate_complex_password(32)
    print("32位密码:", password)
    
    strength = generator.evaluate_password_strength(password)
    print(f"密码强度: {strength['strength']}")
    print(f"熵值: {strength['entropy']:.2f} 比特")
    
    if strength['suggestions']:
        print("改进建议:")
        for suggestion in strength['suggestions']:
            print(f"- {suggestion}")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.DEBUG)
    # 运行测试
    test() 