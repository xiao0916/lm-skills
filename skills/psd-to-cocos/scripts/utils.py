# -*- coding: utf-8 -*-
"""
极简工具库

整合了路径解析、文件名规范化和基础日志功能。
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import Optional, List, Callable
from pypinyin import pinyin, Style

# --- 日志系统 ---

def setup_logger(name="psd-to-cocos", level=logging.INFO):
    """设置简单的日志记录器"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

logger = setup_logger()

# --- 文件名规范化 (来自原 filename_normalizer.py) ---

def normalize_psd_filename(filename: str) -> str:
    """将 PSD 文件名规范化为合法的目录名/标识符"""
    # 移除扩展名
    name = os.path.splitext(os.path.basename(filename))[0]
    
    # 1. 将中文转为拼音
    # pinyin 返回格式样例: [['zhong'], ['xin']]
    name = "".join([item[0] for item in pinyin(name, style=Style.NORMAL)])
    
    # 2. 替换任何非字母数字字符为连字符
    name = re.sub(r'[^a-zA-Z0-9]+', '-', name)
    
    # 3. 移除首尾连字符
    name = name.strip('-')
    
    return name.lower() or "unnamed-psd"

# --- 工具搜索 (来自原 tool_resolver.py) ---

class ToolResolver:
    """寻找 psd-layer-reader 和 psd-slicer 的路径"""
    
    @staticmethod
    def get_search_paths() -> List[Path]:
        return [
            Path(__file__).parent.parent.parent.parent / '.claude' / 'skills',
            Path.cwd() / '.claude' / 'skills',
            Path.home() / '.claude' / 'skills',
            Path(os.environ.get('CLAUDE_SKILLS_PATH', '')),
        ]

    def resolve(self, skill_name: str, script_name: str) -> Path:
        for base_path in self.get_search_paths():
            if not base_path or not base_path.exists():
                continue
            script_path = base_path / skill_name / 'scripts' / script_name
            if script_path.exists():
                return script_path
        
        # 兜底：尝试在当前目录及其父目录中寻找 .agents/skills
        current = Path(__file__).parent
        for _ in range(5):
            agents_skills = current / '.agents' / 'skills'
            if agents_skills.exists():
                script_path = agents_skills / skill_name / 'scripts' / script_name
                if script_path.exists():
                    return script_path
            if current.parent == current: break
            current = current.parent
            
        raise RuntimeError(f"未找到工具: {skill_name}/{script_name}。请通过 CLAUDE_SKILLS_PATH 环境变量设置路径。")

    def resolve_reader(self) -> Path:
        return self.resolve('psd-layer-reader', 'psd_layers.py')

    def resolve_slicer(self) -> Path:
        return self.resolve('psd-slicer', 'export_slices.py')
