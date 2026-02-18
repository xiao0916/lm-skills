#!/usr/bin/env python3
"""PSD to Cocos - 新版 CLI 启动脚本

这是整合后的统一入口，提供增强功能：
- 批量处理
- 中文文件名转拼音
- 冲突处理策略
- 失败重试
- 进度显示
"""

import sys
import os

# 添加 scripts 目录到 path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from cli.main import main

if __name__ == '__main__':
    main()
