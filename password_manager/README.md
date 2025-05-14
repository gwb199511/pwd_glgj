# 密码管理系统

## 项目简介

本系统是一个安全、高效、功能完善的密码管理解决方案，专为个人和团队设计，可以安全存储和管理各类密码及敏感信息。

### 主要功能

- **密码安全存储**：使用高级加密算法保护所有密码信息
- **密码自动生成**：提供强密码生成功能，满足不同安全要求
- **分类管理**：按类别整理和管理密码，便于查找
- **导入导出**：支持Excel格式密码数据的导入导出
- **SSH连接**：直接通过SSH连接远程服务器并自动填充凭据
- **审计日志**：记录所有密码操作，便于安全审计
- **数据库集成**：支持MySQL数据库存储，提供可靠的数据持久化

## 技术架构

- **前端**：PyQt5构建的跨平台图形界面
- **数据库**：MySQL数据库存储
- **加密**：使用cryptography库实现高级加密
- **远程连接**：基于paramiko实现SSH功能
- **数据处理**：pandas和openpyxl处理Excel数据

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
│   ├── database.py        # 数据库基础操作
│   ├── db_manager.py      # 数据库管理器
│   ├── db_user_settings.py # 用户设置数据库操作
│   ├── user_settings.py   # 用户设置管理
│   ├── encrypt.py         # 加密功能
│   └── data_storage.py    # 数据存储
├── ui/                    # 界面相关
│   ├── __init__.py
│   ├── login/             # 登录相关UI
│   ├── components/        # UI组件
│   ├── dialogs/           # 对话框
│   └── password_manager/  # 主密码管理UI
├── utils/                 # 工具类
│   ├── __init__.py
│   ├── excel_utils.py     # Excel处理工具
│   └── password_generator.py  # 密码生成器
├── features/              # 特性功能
│   ├── __init__.py
│   ├── ssh/               # SSH相关功能
│   └── audit/             # 审计相关功能
├── data/                  # 数据目录
├── db/                    # 数据库相关文件
├── logs/                  # 日志目录
└── scripts/               # 辅助脚本
```

## 安装和运行

### 系统要求

- Python 3.8或更高版本
- MySQL数据库服务器（可选，用于数据库模式）

### 安装步骤

1. 克隆或下载项目代码
2. 创建并激活虚拟环境（推荐）:
   ```
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```
3. 安装依赖:
   ```
   pip install -r requirements.txt
   ```
4. 配置数据库（如使用MySQL模式）:
   - 创建MySQL数据库
   - 在首次运行时配置数据库连接信息

### 运行方法

直接运行启动脚本:
```
python run.py
```

## 使用说明

1. **首次使用**:
   - 创建主账户和主密码
   - 选择数据存储方式（本地文件或MySQL数据库）

2. **密码管理**:
   - 添加、编辑、删除密码条目
   - 按类别、名称或其他属性搜索密码
   - 使用密码生成器创建强密码

3. **数据导入导出**:
   - 使用Excel模板导入密码数据
   - 导出密码数据为Excel文件
   - 使用系统提供的"密码记录导入模板.xlsx"作为导入参考

4. **SSH功能**:
   - 存储SSH连接信息
   - 直接从应用程序发起SSH连接

5. **审计功能**:
   - 查看密码访问和修改记录
   - 导出审计日志

## 安全说明

- 所有密码使用高级加密算法存储
- 主密码从不存储，仅用于加密/解密数据
- 支持会话超时自动锁定
- 建议定期备份加密数据

## 故障排除

- 如遇登录问题，检查主密码是否正确
- 数据库连接问题请确认MySQL服务运行状态
- 日志文件位于logs目录，可用于诊断问题

## 联系与支持

如有问题或建议，请联系开发团队。 