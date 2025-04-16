# 密码管理系统

## 项目结构

```
password_manager/
├── requirements.txt       # 项目依赖
├── README.md              # 项目说明文档
├── run.py                 # 启动脚本
├── main.py                # 主入口程序
├── config.py              # 配置文件
├── core/                  # 核心功能模块
│   ├── __init__.py
│   ├── user.py            # 用户管理
│   ├── password.py        # 密码管理核心
│   ├── database.py        # 数据库操作
│   ├── db_manager.py      # 数据库管理器
│   ├── encrypt.py         # 加密功能
│   └── data_storage.py    # 数据存储
├── ui/                    # 界面相关
│   ├── __init__.py
│   ├── login/             # 登录相关UI
│   │   ├── __init__.py
│   │   └── login_ui.py
│   ├── components/        # UI组件
│   │   ├── __init__.py
│   │   └── ui_components.py
│   ├── dialogs/           # 对话框
│   │   ├── __init__.py
│   │   ├── mysql_config_dialog.py
│   │   ├── excel_dialog.py
│   │   └── password_generator_dialog.py
│   └── password_manager/  # 主密码管理UI
│       ├── __init__.py
│       ├── password_manager_ui.py
│       ├── ui_layout.py
│       ├── ui_operations.py
│       └── ui_utils.py
├── utils/                 # 工具类
│   ├── __init__.py
│   ├── excel_utils.py     # Excel处理工具
│   └── password_generator.py  # 密码生成器
├── features/              # 特性功能
│   ├── __init__.py
│   ├── ssh/               # SSH相关功能
│   │   ├── __init__.py
│   │   ├── ssh_password_updater.py
│   │   └── ssh_log_viewer.py
│   └── audit/             # 审计相关功能
│       ├── __init__.py
│       ├── audit_log.py
│       └── audit_log_viewer.py
├── data/                  # 数据目录
│   └── ...
└── logs/                  # 日志目录
    └── ...
```

## 文件重组说明

该项目是对原有密码管理系统的代码结构重组，目的是提高代码的组织性和可维护性。重组过程中对导入路径进行了调整，确保所有功能正常运行。

### 主要变更

1. 按功能模块划分代码目录
2. 统一导入路径
3. 优化配置文件管理
4. 分离UI和业务逻辑

## 运行方法

1. 安装依赖：`pip install -r requirements.txt`
2. 运行程序：`python run.py`

## 技术架构

- 前端：PyQt5
- 数据库：MySQL
- 额外功能：SSH连接，Excel导入导出，审计日志 