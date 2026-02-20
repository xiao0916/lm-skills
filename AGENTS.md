# AGENTS.md - LM-Skills 开发指南

本文档为在此代码库中工作的 AI Agent 提供开发规范和运行指南。

## 项目概述

**LM-Skills** 是一个技能包（Skills）集合仓库，包含多个 Python 脚本技能：
- **PSD 处理**：psd-slicer, psd-layer-reader, psd-component-splitter, psd-json-preview, psd-to-preview, psd-to-cocos
- **代码分析**：code-splitter, component-analyzer
- **HTML 优化**：html-semantic-optimizer
- **OCR 识别**：ocr-recognition
- **Docker**：docker-first-runner
- **环境管理**：venv-manager

每个技能位于 `skills/<skill-name>/` 目录下，包含：
- `SKILL.md` - 技能文档
- `scripts/` - Python 脚本
- `tests/` - 测试文件（可选）
- `references/` - 参考文档（可选）

---

## 测试命令

### 运行单个测试
```bash
# 方法 1：使用 pytest（推荐）
cd skills/code-splitter
python -m pytest tests/test_splitter.py::TestJSXParser::test_parse_simple_jsx -v

# 方法 2：使用 unittest
python -m unittest skills.code-splitter.tests.test_splitter.TestJSXParser.test_parse_simple_jsx -v
```

### 运行所有测试
```bash
python -m pytest skills/code-splitter/tests/ -v
```

### 技能脚本运行
```bash
cd skills/code-splitter
py -3 scripts/split_component.py --input ./my-component/ --dry-run
```

---

## 代码风格规范

### 1. 语言规范
- **文档与注释**：使用**中文**编写所有文档（README.md、SKILL.md）和代码注释
- **代码变量**：英文变量名 + 中文注释

```python
def parse_jsx(jsx_string):
    """解析 JSX 字符串，返回元素树"""
    pass
```

### 2. 导入规范
- 标准库 → 第三方库 → 项目模块
- 测试文件需添加 sys.path 处理

```python
import os
import sys
from pathlib import Path

# 测试文件需要
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from jsx_parser import JSXParser
```

### 3. 格式化规范
- Python 3.6+ 语法
- 行长度：不超过 100 字符
- 缩进：4 空格
- 文件编码：`utf-8`

### 4. 类型规范
- 优先使用类型注解
- 复杂函数添加 docstring

```python
from typing import List, Dict, Optional

def parse_jsx(jsx_string: str) -> List[Dict]:
    """解析 JSX 字符串"""
    ...
```

### 5. 命名规范
- **函数/方法**：snake_case
- **类名**：PascalCase
- **常量**：UPPER_SNAKE_CASE
- **文件**：snake_case.py

### 6. 错误处理规范
- 使用具体异常类型
- 提供有意义的错误信息

```python
try:
    result = parse_jsx_file(file_path)
except FileNotFoundError:
    raise ValueError(f"文件不存在: {file_path}") from None
```

---

## 技能开发规范

### 创建新技能

1. **使用 skill-creator**：创建或修改技能时，优先使用 skill-creator 技能辅助

2. **搜索已有技能**：在创建新技能前，使用 find-skills 搜索全网已有的技能包，避免重复造轮子

3. **技能目录结构**：

```
skills/<skill-name>/
├── SKILL.md              # 必需
├── skill.json            # 可选
├── scripts/              # 必需
│   └── main_script.py   # 主入口
├── tests/                # 可选
│   └── test_xxx.py
└── references/           # 可选
```

### SKILL.md 必需内容
```markdown
---
name: <skill-name>
description: <技能描述>
---

# <Skill Name>

## 快速开始
```bash
py -3 scripts/main_script.py --arg1 value
```

## 系统要求
- Python 3.6+

## 命令行参数
| 参数 | 说明 |
|------|------|
| --xxx | xxx |

## 核心功能
...

## 已知限制
...
```

---

## 现有技能快速参考

| 技能 | 用途 | 入口脚本 |
|------|------|----------|
| code-splitter | React 组件拆分 | scripts/split_component.py |
| component-analyzer | 组件代码分析 | scripts/analyze_components.py |
| psd-component-splitter | PSD 组件拆分 | scripts/split_components.py |
| html-semantic-optimizer | HTML 语义优化 | html_optimizer.py |
| venv-manager | Python 环境管理 | - |

---

## 注意事项

1. **不要删除测试**：即使测试失败，也不要删除测试文件来"修复"
2. **保持向后兼容**：修改现有技能时注意兼容已有接口
3. **更新文档**：修改代码后同步更新 SKILL.md
4. **单一职责**：每个脚本应该专注于一件事
