import threading
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from password_manager.core.db_manager import DBManager

def show_message(parent, title, message, icon=QMessageBox.Information):
    """显示消息对话框"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(icon)
    msg.exec_()

class MySQLConfigDialog:
    def __init__(self):
        self.db_manager = DBManager()
        self.test_in_progress = False

    def get_config_from_ui(self):
        """
        从UI获取MySQL配置信息
        此方法需要在子类中实现
        """
        # 在实际实现中，需要从UI组件获取配置
        raise NotImplementedError("子类必须实现get_config_from_ui方法")

    def test_connection(self):
        """测试数据库连接"""
        # 防止重复点击
        if self.test_in_progress:
            return
            
        # 获取配置
        try:
            config = self.get_config_from_ui()
            
            # 基本验证
            if not config.get('host'):
                show_message(self, "配置错误", "请输入数据库主机地址", QMessageBox.Warning)
                return
                
            if not config.get('database'):
                show_message(self, "配置错误", "请输入数据库名称", QMessageBox.Warning)
                return
                
            # 端口验证
            try:
                port = int(config.get('port', 3306))
                if port <= 0 or port > 65535:
                    show_message(self, "配置错误", "端口号必须在1-65535之间", QMessageBox.Warning)
                    return
                config['port'] = port
            except ValueError:
                show_message(self, "配置错误", "端口号必须是有效的数字", QMessageBox.Warning)
                return
        except Exception as e:
            show_message(self, "配置错误", f"获取配置失败: {str(e)}", QMessageBox.Critical)
            return
            
        # 设置测试状态
        self.test_in_progress = True
        
        # 禁用按钮并更新文本
        self.test_button.setEnabled(False)
        self.test_button.setText("正在连接...")
        if hasattr(self, 'save_button'):
            self.save_button.setEnabled(False)
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setEnabled(False)
        
        # 创建测试专用的DBManager实例，避免修改全局配置
        temp_db_manager = DBManager()
        temp_db_manager.config = config.copy()  # 只设置配置，不触发连接池创建
        
        # 创建工作线程
        def worker():
            try:
                # 测试连接
                success, message = temp_db_manager.test_connection()
                return success, message
            except Exception as e:
                return False, f"测试连接时发生异常: {str(e)}"
        
        # 创建线程
        thread = threading.Thread(target=lambda: self._handle_test_result(worker()))
        thread.daemon = True
        thread.start()
    
    def _handle_test_result(self, result):
        """处理测试结果"""
        success, message = result
        
        # 使用QTimer确保在主线程中更新UI
        def update_ui():
            # 恢复按钮状态
            self.test_button.setText("测试连接")
            self.test_button.setEnabled(True)
            if hasattr(self, 'save_button'):
                self.save_button.setEnabled(True)
            if hasattr(self, 'cancel_button'):
                self.cancel_button.setEnabled(True)
            
            # 重置标志
            self.test_in_progress = False
            
            # 显示结果
            if success:
                show_message(self, "连接成功", f"MySQL连接测试成功！\n{message}", QMessageBox.Information)
            else:
                show_message(self, "连接失败", f"MySQL连接测试失败：\n{message}", QMessageBox.Critical)
        
        # 确保在主线程中更新UI
        QTimer.singleShot(0, update_ui) 