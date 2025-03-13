# 密码管理表格模块架构

本模块通过类继承和混入（Mixin）方式对原本庞大的表格功能进行了模块化拆分，提高了代码的可维护性和可读性。

## 架构概述

ui_table模块现在由以下几个分组件构成：

1. **基础表格类**（`base_table.py`）：包含表格的基础设置和初始化
2. **表格数据加载**（`table_data.py`）：处理数据加载和基本操作
3. **表格编辑功能**（`table_edit.py`）：处理添加、编辑和删除行的功能
4. **表格搜索功能**（`table_search.py`）：处理搜索和过滤相关功能
5. **表格密码功能**（`table_password.py`）：处理密码生成和特殊处理
6. **表格事件处理**（`table_events.py`）：处理键盘事件和右键菜单等

## 类继承结构

```
PasswordTable (ui_table/__init__.py)
└── BasePasswordTable (base_table.py)
    └── TableDataMixin (table_data.py)
    └── TableEditMixin (table_edit.py)
    └── TableSearchMixin (table_search.py)
    └── TableEventsMixin (table_events.py)
    └── TablePasswordMixin (table_password.py)
```

## 文件功能说明

- **__init__.py**：整合所有模块并提供主要的`PasswordTable`类
- **base_table.py**：基础表格类，提供基本初始化和设置
- **table_data.py**：表格数据管理，包括加载和获取数据
- **table_edit.py**：表格编辑功能，处理添加、编辑和删除行操作
- **table_search.py**：表格搜索功能，提供搜索和过滤方法
- **table_events.py**：表格事件处理，包括右键菜单和事件过滤器
- **table_password.py**：密码生成和服务器密码同步功能

## 向后兼容性

为了保持向后兼容性，原来的`ui_table.py`文件被保留并改为导入新模块的`PasswordTable`和`TableEventFilter`类，这样不会影响其他依赖此模块的代码。

## 使用方式

```python
from ui.password_manager.ui_table import PasswordTable

# 创建表格实例
table_manager = PasswordTable(table_widget)
```

## 维护说明

1. 对基础表格设置的修改应该在`base_table.py`中进行
2. 对数据加载的修改应该在`table_data.py`中进行
3. 对编辑功能的修改应该在`table_edit.py`中进行
4. 对搜索功能的修改应该在`table_search.py`中进行
5. 对事件处理的修改应该在`table_events.py`中进行
6. 对密码功能的修改应该在`table_password.py`中进行
7. 如果添加新功能，可以在对应的文件中扩展，或创建新的混入类文件 