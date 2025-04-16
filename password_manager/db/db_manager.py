def test_connection(self):
        """测试数据库连接
        
        Returns:
            tuple: (success, message) - 连接是否成功和相关信息
        """
        try:
            # 创建临时连接
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                connect_timeout=5  # 设置连接超时时间为5秒
            )
            
            try:
                # 执行简单查询测试连接
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if result and result[0] == 1:
                        return True, "连接成功"
                    else:
                        return False, "连接测试失败"
            finally:
                # 确保连接被关闭
                conn.close()
                
        except pymysql.Error as e:
            logger.error(f"MySQL连接测试失败: {str(e)}")
            return False, f"连接失败: {str(e)}"
        except Exception as e:
            logger.error(f"MySQL连接测试发生异常: {str(e)}")
            return False, f"发生异常: {str(e)}" 