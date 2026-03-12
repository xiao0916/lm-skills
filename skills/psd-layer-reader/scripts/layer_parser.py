# -*- coding: utf-8 -*-
from utils import sanitize_name
from text_extractor import extract_text_info
import re

def extract_layout_tag(name):
    """提取 [flow-y] 形式的布局标签"""
    match = re.match(r'^\[([a-zA-Z0-9-]+)\](.*)$', name.strip())
    if match:
        return match.group(1), match.group(2).strip()
    return None, name.strip()

def node_from_layer(layer, used_names=None):
    """
    处理 PSD 图层，返回节点信息。
    自动规范化图层名称为合法格式。

    Args:
        layer: PSD 图层对象
        used_names: 已使用的名称集合（用于全局唯一性检查）
                   如果为 None，则创建新的集合（向后兼容）

    Returns:
        dict: 包含图层信息的字典节点
    """
    if used_names is None:
        used_names = set()

    # 统一在一个 try 块中读取属性，无需逐一 hasattr
    try:
        raw_name = layer.name or "unnamed"
        layout_tag, layer_name = extract_layout_tag(raw_name)
        bbox = layer.bbox
        layer_id = layer.layer_id
        kind = layer.kind
        visible = bool(layer.visible)
        is_group = layer.is_group()
    except Exception:
        raw_name = "unnamed"
        layout_tag, layer_name = None, "unnamed"
        bbox = None
        layer_id = None
        kind = "unknown"
        visible = True
        is_group = False

    # 规范化名称
    layer_kind = 'group' if kind == 'group' else 'layer'
    sanitized_name = sanitize_name(layer_name, used_names, layer_kind, layer_id)

    node = {
        "name": sanitized_name,
        "originalName": raw_name,
        "layoutTag": layout_tag,
        "layerId": layer_id,
        "kind": kind,
        "visible": visible,
        "bbox": [bbox[0], bbox[1], bbox[2], bbox[3]] if bbox is not None else None,
        "children": [],
    }

    # 处理子图层（图层组）
    if is_group:
        try:
            node["children"] = [node_from_layer(child, used_names) for child in layer]
        except Exception:
            node["children"] = []

    # 添加文本层信息
    if kind == 'type':
        try:
            text_info = extract_text_info(layer)
            if text_info:
                node['textInfo'] = text_info
        except Exception:
            pass

    return node
