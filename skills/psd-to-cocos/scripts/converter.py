# -*- coding: utf-8 -*-
"""
核心引擎：包含坐标转换、图层数据提取和 Cocos 元素构建。
整合了原 common 目录下的核心逻辑。
"""

import json
from datetime import datetime

def validate_bbox(bbox):
    """验证 bbox 是否有效且不为空面积"""
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False
    try:
        x1, y1, x2, y2 = bbox
        return float(x1) < float(x2) and float(y1) < float(y2)
    except (ValueError, TypeError):
        return False

def bbox_to_cocos_position(bbox, canvas_size):
    """
    将 PSD bbox 转换为 Cocos 坐标系统。
    注意：在 Cocos 中 Y 轴向上，而 PSD 中 Y 轴向下。
    
    Args:
        bbox: [x1, y1, x2, y2] (PSD 坐标：左上角为原点，Y 向下)
        canvas_size: [width, height]
        
    Returns:
        dict: {x, y, width, height} (绝对坐标：原点在 PSD 左上角，但 Y 值将被映射)
    """
    x1, y1, x2, y2 = bbox
    cw, ch = canvas_size
    
    width = x2 - x1
    height = y2 - y1
    
    # 中心点（相对于 PSD 左上角）
    center_x = x1 + width / 2
    center_y = y1 + height / 2
    
    # 返回绝对坐标（保持 PSD 原始中心点，逻辑转换在 create_element_nested 中处理）
    return {
        "x": round(center_x, 2),
        "y": round(center_y, 2),
        "width": int(width),
        "height": int(height)
    }

def extract_canvas_size(psd_data, default_size=(1920, 1080)):
    """智能从图层数据中提取画布尺寸"""
    candidates = []
    
    def collect_layers(item):
        if isinstance(item, list):
            for child in item: collect_layers(child)
        elif isinstance(item, dict):
            if item.get("visible", True) and "bbox" in item:
                bbox = item["bbox"]
                if validate_bbox(bbox):
                    x1, y1, x2, y2 = bbox
                    w, h = x2 - x1, y2 - y1
                    is_origin = abs(x1) < 10 and abs(y1) < 10
                    candidates.append({"w": w, "h": h, "area": w * h, "is_origin": is_origin})
            if "children" in item: collect_layers(item["children"])
    
    collect_layers(psd_data)
    if not candidates: return list(default_size)
    
    origin_candidates = [c for c in candidates if c["is_origin"]]
    if origin_candidates:
        best = max(origin_candidates, key=lambda x: x["area"])
        return [int(best["w"]), int(best["h"])]
    
    best = max(candidates, key=lambda x: x["area"])
    return [int(best["w"]), int(best["h"])]

# --- 图层提取 ---

def extract_visible_layers(data):
    """扁平化提取所有可见图层"""
    layers = []
    def walk(item):
        if isinstance(item, list):
            for i in item: walk(i)
        elif isinstance(item, dict):
            if not item.get("visible", True): return
            if item.get("type") == "layer" and "bbox" in item:
                if validate_bbox(item["bbox"]): layers.append(item)
            if "children" in item: walk(item["children"])
    walk(data)
    return layers

def extract_visible_layers_nested(data):
    """保持嵌套结构的可见图层提取"""
    if isinstance(data, list):
        result = []
        for item in data:
            extracted = extract_visible_layers_nested(item)
            if extracted: result.append(extracted)
        return result
    elif isinstance(data, dict):
        if not data.get("visible", True): return None
        new_item = data.copy()
        if "children" in data:
            new_children = []
            for child in data["children"]:
                child_extracted = extract_visible_layers_nested(child)
                if child_extracted: new_children.append(child_extracted)
            new_item["children"] = new_children
            if not new_children and "bbox" not in data: return None
        return new_item
    return None

# --- 元素构建 ---

def create_element_nested(layer, canvas_size, parent_pos=(0, 0), images_dir="images"):
    """递归构建 Cocos 元素数据"""
    name = layer.get("name", "unnamed")
    bbox = layer.get("bbox")
    
    # 坐标转换：获取 PSD 坐标系下的中心点
    cocos = bbox_to_cocos_position(bbox, canvas_size) if bbox else {"x": 0, "y": 0, "width": 0, "height": 0}
    
    # 计算相对于画布中心的坐标，并翻转 Y 轴
    # PSD: Y 轴向下为正，原点在左上角
    # Cocos: Y 轴向上为正，原点在屏幕中心（相对 parent）
    cw, ch = canvas_size
    
    # 当前节点在“画布中心原点且 Y 轴向上”坐标系下的绝对坐标
    abs_x = cocos["x"] - cw / 2
    abs_y = -(cocos["y"] - ch / 2)  # 翻转 Y 轴
    
    # 计算相对于父节点的局部坐标
    rel_x = round(abs_x - parent_pos[0], 2)
    rel_y = round(abs_y - parent_pos[1], 2)
    
    is_button = isinstance(name, str) and name.startswith("btn-")
    # 扩展支持：除了 pixel，smartobject 和 shape 也作为 sprite 处理（只要它们有对应的切图）
    kind = layer.get("kind")
    is_sprite = kind in ("pixel", "smartobject", "shape")
    el_type = "button" if is_button else ("sprite" if is_sprite else "node")
    
    element = {
        "id": name,
        "name": name,
        "type": el_type,
        "visible": True,
        "cocos_position": {"x": rel_x, "y": rel_y},
        "cocos_size": {"width": int(cocos["width"]), "height": int(cocos["height"])},
        "cocos_anchor": {"x": 0.5, "y": 0.5},
    }
    
    if is_sprite:
        element["image_file"] = f"{images_dir}/{name}.png"
        
    if "children" in layer and layer["children"]:
        children = []
        # 当前节点在画布中心坐标系下的坐标作为子节点的父坐标
        current_abs_center_pos = (abs_x, abs_y)
        for child_layer in layer["children"]:
            child_el = create_element_nested(child_layer, canvas_size, current_abs_center_pos, images_dir)
            children.append(child_el)
        if children:
            element["children"] = children
            
    return element

# --- 结构组装 ---

def create_cocos_layout_output(elements, canvas_size, psd_name=""):
    """构建最终的 JSON 输出格式"""
    return {
        "metadata": {
            "psd_name": psd_name,
            "canvas_size": {"width": int(canvas_size[0]), "height": int(canvas_size[1])},
            "generated_at": datetime.now().isoformat(),
            "version": "2.0.0-minimal"
        },
        "elements": elements
    }
