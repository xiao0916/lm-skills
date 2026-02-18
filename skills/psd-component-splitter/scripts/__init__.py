# -*- coding: utf-8 -*-
"""
PSD 组件拆分器 - 脚本模块

提供从 PSD 图层结构生成 React/Vue 组件的功能。
"""

from .naming_utils import (
    sanitize_component_name,
    to_pascal_case,
    kebab_case,
    ensure_unique_names,
)

from .react_generator import (
    generate_react_split_component,
    generate_react_main_entry,
)

from .vue_generator import (
    generate_vue_split_component,
    generate_vue_main_entry,
)

__all__ = [
    # 命名工具
    'sanitize_component_name',
    'to_pascal_case',
    'kebab_case',
    'ensure_unique_names',
    # React 生成器
    'generate_react_split_component',
    'generate_react_main_entry',
    # Vue 生成器
    'generate_vue_split_component',
    'generate_vue_main_entry',
]