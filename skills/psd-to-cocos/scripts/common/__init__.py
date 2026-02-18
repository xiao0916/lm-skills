"""
psd-to-cocos 公共工具模块

提供图层处理、元素配置和 JSON 输出等通用功能。

支持嵌套结构和平铺结构两种输出模式。
"""

from .layer_utils import extract_visible_layers, extract_visible_layers_nested
from .element_builder import create_button_config, BUTTON_DEFAULT_CONFIG, create_element_nested
from .json_utils import create_cocos_layout_output, write_layout_json

__all__ = [
    "extract_visible_layers",
    "extract_visible_layers_nested",  # 新增：嵌套提取
    "create_button_config",
    "BUTTON_DEFAULT_CONFIG",
    "create_element_nested",  # 新增：嵌套元素构建
    "create_cocos_layout_output",
    "write_layout_json",
]
