def save_credentials(self, username: str, password: str) -> bool:
    """
    保存登录凭证（记住密码功能）
    
    Args:
        username (str): 用户名
        password (str): 密码
        
    Returns:
        bool: 操作成功返回True，否则返回False
    """
    try:
        # 加密密码
        encrypted_password = encryptor.encrypt(password)
        
        # 直接保存用户名和密码，而不是保存字典
        return self.remember_db.set(username, encrypted_password)
    except Exception as e:
        logger.error(f"保存登录凭证时出错: {str(e)}")
        return False 