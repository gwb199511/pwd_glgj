import threading
from PyQt5.QtWidgets import QMessageBox
from password_manager.db.db_manager import DBManager

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

    def test_connection(self):
        """测试数据库连接"""
        # 获取配置
        config = self.get_config_from_ui()
        
        # 禁用按钮
        self.test_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # 更新按钮文本
        original_text = self.test_button.text()
        self.test_button.setText("正在连接...")
        
        # 创建工作线程
        def worker():
            try:
                # 更新配置
                self.db_manager.update_config(config)
                # 测试连接
                success, message = self.db_manager.test_connection()
                return success, message
            except Exception as e:
                return False, str(e)
        
        # 创建线程
        thread = threading.Thread(target=lambda: self._handle_test_result(worker()))
        thread.daemon = True
        thread.start()
    
    def _handle_test_result(self, result):
        """处理测试结果"""
        success, message = result
        
        # 在主线程中更新UI
        self.test_button.setText("测试连接")
        self.test_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
        # 显示结果
        if success:
            show_message(self, "连接成功", f"MySQL连接测试成功！\n{message}", QMessageBox.Information)
        else:
            show_message(self, "连接失败", f"MySQL连接测试失败：\n{message}", QMessageBox.Critical) 