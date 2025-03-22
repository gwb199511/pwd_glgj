#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
审计日志查看器测试脚本
"""

import sys
import logging
import traceback

print("1. 脚本开始执行")

# 配置详细日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

print("2. 日志配置完成")

def main():
    """主函数"""
    print("3. 进入main函数")
    logger.info("启动审计日志查看器测试")
    
    print("4. 准备导入PyQt5模块")
    try:
        # 导入需要的模块
        from PyQt5.QtWidgets import QApplication
        print("5. PyQt5模块导入成功")
    except Exception as e:
        print(f"导入PyQt5模块失败: {str(e)}")
        logger.error(f"导入PyQt5模块失败: {str(e)}")
        logger.error(traceback.format_exc())
        return
    
    print("6. 准备导入AuditLogViewer")
    try:
        # 导入审计日志查看器
        from audit_log_viewer import AuditLogViewer
        print("7. AuditLogViewer导入成功")
    except Exception as e:
        print(f"导入AuditLogViewer失败: {str(e)}")
        logger.error(f"导入AuditLogViewer失败: {str(e)}")
        logger.error(traceback.format_exc())
        return
    
    print("8. 准备创建Qt应用程序")
    try:
        # 创建Qt应用程序
        app = QApplication(sys.argv)
        print("9. Qt应用程序创建成功")
    except Exception as e:
        print(f"创建Qt应用程序失败: {str(e)}")
        logger.error(f"创建Qt应用程序失败: {str(e)}")
        logger.error(traceback.format_exc())
        return
    
    print("10. 准备创建AuditLogViewer实例")
    try:
        # 创建审计日志查看器
        viewer = AuditLogViewer()
        print("11. AuditLogViewer实例创建成功")
    except Exception as e:
        print(f"创建AuditLogViewer实例失败: {str(e)}")
        logger.error(f"创建AuditLogViewer实例失败: {str(e)}")
        logger.error(traceback.format_exc())
        return
    
    print("12. 准备显示日志查看器窗口")
    try:
        # 显示日志查看器
        viewer.show()
        print("13. 日志查看器窗口显示成功")
    except Exception as e:
        print(f"显示日志查看器窗口失败: {str(e)}")
        logger.error(f"显示日志查看器窗口失败: {str(e)}")
        logger.error(traceback.format_exc())
        return
    
    print("14. 准备启动应用程序事件循环")
    try:
        # 启动应用程序事件循环
        sys.exit(app.exec_())
        print("15. 应用程序事件循环结束")  # 这一行正常情况下不会执行
    except Exception as e:
        print(f"启动应用程序事件循环失败: {str(e)}")
        logger.error(f"启动应用程序事件循环失败: {str(e)}")
        logger.error(traceback.format_exc())
        return

print("16. 准备调用main函数")
if __name__ == "__main__":
    try:
        main()
        print("17. main函数执行完成")
    except Exception as e:
        print(f"main函数执行失败: {str(e)}")
        traceback.print_exc()

print("18. 脚本执行结束")