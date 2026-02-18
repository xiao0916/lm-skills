"""元素构建工具 - 仅包含通用配置"""

# 默认按钮配置常量
BUTTON_DEFAULT_CONFIG = {
    "transition": "scale",
    "zoom_scale": 0.9,
    "duration": 0.1
}

def create_button_config(transition="scale", zoom_scale=0.9, duration=0.1):
    """
    创建按钮配置
    
    Args:
        transition: 过渡动画类型 (默认: "scale")
        zoom_scale: 缩放比例 (默认: 0.9)
        duration: 动画持续时间秒数 (默认: 0.1)
    
    Returns:
        dict: 按钮配置对象
    
    Example:
        >>> create_button_config()
        {'transition': 'scale', 'zoom_scale': 0.9, 'duration': 0.1}
        >>> create_button_config('fade', 0.8, 0.2)
        {'transition': 'fade', 'zoom_scale': 0.8, 'duration': 0.2}
    """
    return {
        "transition": transition,
        "zoom_scale": zoom_scale,
        "duration": duration
    }

def create_element_nested(layer_info, canvas_size, bbox_to_cocos_func,
                         center_coordinates=True, parent_cocos_pos=None):
    """
    递归创建嵌套的 Cocos 元素对象

    Args:
        layer_info: 图层信息字典
        canvas_size: [width, height] 画布尺寸
        bbox_to_cocos_func: bbox_to_cocos_position 函数
        center_coordinates: 是否居中坐标（默认 True）
        parent_cocos_pos: 父元素的 Cocos 坐标 (x, y)，用于计算相对位置

    Returns:
        dict: 嵌套的 Cocos 元素对象
    """
    name = layer_info["name"]
    is_button = isinstance(name, str) and name.startswith("btn-")
    is_group = layer_info.get("kind") == "group"
    
    # 处理 bbox（group 可能没有）
    if "bbox" in layer_info:
        bbox = layer_info["bbox"]
        cocos = bbox_to_cocos_func(bbox, canvas_size)
        
        # 根据 center_coordinates 决定是否居中
        if center_coordinates:
            pos_x = round(cocos["x"] - canvas_size[0] / 2, 4)
            pos_y = round(cocos["y"] - canvas_size[1] / 2, 4)
        else:
            pos_x = round(cocos["x"], 4)
            pos_y = round(cocos["y"], 4)
        
        # 计算相对坐标（如果有父元素）
        if parent_cocos_pos is not None:
            pos_x = round(pos_x - parent_cocos_pos[0], 4)
            pos_y = round(pos_y - parent_cocos_pos[1], 4)
        
        size = {"width": cocos["width"], "height": cocos["height"]}
    else:
        # Group 无 bbox，从 children 计算包围盒
        if "children" in layer_info and layer_info["children"]:
            child_elements = []
            for child in layer_info["children"]:
                if "bbox" in child:
                    child_cocos = bbox_to_cocos_func(child["bbox"], canvas_size)
                    if center_coordinates:
                        child_x = round(child_cocos["x"] - canvas_size[0] / 2, 4)
                        child_y = round(child_cocos["y"] - canvas_size[1] / 2, 4)
                    else:
                        child_x = round(child_cocos["x"], 4)
                        child_y = round(child_cocos["y"], 4)
                    child_elements.append({
                        "x": child_x,
                        "y": child_y,
                        "width": child_cocos["width"],
                        "height": child_cocos["height"]
                    })
            
            if child_elements:
                min_x = min(e["x"] - e["width"]/2 for e in child_elements)
                max_x = max(e["x"] + e["width"]/2 for e in child_elements)
                min_y = min(e["y"] - e["height"]/2 for e in child_elements)
                max_y = max(e["y"] + e["height"]/2 for e in child_elements)
                pos_x = round((min_x + max_x) / 2, 4)
                pos_y = round((min_y + max_y) / 2, 4)
                size = {"width": round(max_x - min_x, 4), "height": round(max_y - min_y, 4)}
            else:
                pos_x = 0
                pos_y = 0
                size = {"width": 0, "height": 0}
        else:
            pos_x = 0
            pos_y = 0
            size = {"width": 0, "height": 0}
    
    element = {
        "id": name,
        "name": name,
        "original_name": layer_info.get("originalName", name),
        "type": "button" if is_button else ("group" if is_group else "sprite"),
        "visible": True,
        "cocos_position": {"x": pos_x, "y": pos_y},
        "cocos_size": size,
        "cocos_anchor": {"x": 0.5, "y": 0.5},
        "image_file": f"images/{name}.png"
    }
    
    # 添加 psd_bbox（如果有）
    if "bbox" in layer_info:
        element["psd_bbox"] = layer_info["bbox"]
    
    if is_button:
        element["button_config"] = create_button_config()
    
    # 递归处理子元素
    if "children" in layer_info and layer_info["children"]:
        element["children"] = [
            create_element_nested(child, canvas_size, bbox_to_cocos_func, center_coordinates, (pos_x, pos_y))
            for child in layer_info["children"]
        ]
    
    return element
