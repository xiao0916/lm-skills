"""PSD bbox 到 Cocos position 的坐标转换"""


def bbox_to_cocos_position(bbox, canvas_size):
    """
    将 PSD bbox 转换为 Cocos 锚点中心坐标
    
    PSD 坐标系：原点在左上角，Y 轴向下
    Cocos 坐标系：锚点中心点(0.5, 0.5)，Y 轴向上
    
    转换步骤：
    1. PSD 左上原点 → Cocos 左下原点: y = canvas_height - y2
    2. Cocos 左下原点 → 锚点中心: x = x1 + width/2, y = y + height/2
    
    Args:
        bbox: [x1, y1, x2, y2] - PSD 图层边界框（左上右下）
        canvas_size: [width, height] - 画布尺寸
    
    Returns:
        dict: {"x": float, "y": float, "width": int, "height": int}
              Cocos 锚点中心坐标和尺寸
    
    Example:
        >>> bbox = [100, 200, 300, 260]  # 宽 200, 高 60
        >>> canvas = [1920, 1080]
        >>> bbox_to_cocos_position(bbox, canvas)
        {'x': 200.0, 'y': 850.0, 'width': 200, 'height': 60}
    """
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    canvas_width, canvas_height = canvas_size
    
    # PSD 左上原点 → Cocos 左下原点
    cocos_y_bottom = canvas_height - y2
    
    # Cocos 左下原点 → 锚点中心 (0.5, 0.5)
    cocos_x = x1 + width / 2
    cocos_y = cocos_y_bottom + height / 2
    
    return {
        "x": round(cocos_x, 2),
        "y": round(cocos_y, 2),
        "width": width,
        "height": height
    }


def validate_bbox(bbox):
    """
    验证 bbox 格式是否正确
    
    Args:
        bbox: 待验证的 bbox 列表
    
    Returns:
        bool: 是否有效
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False
    
    try:
        x1, y1, x2, y2 = bbox
        # 确保是数字
        float(x1), float(y1), float(x2), float(y2)
        # 确保 x2 > x1 且 y2 > y1
        return x2 > x1 and y2 > y1
    except (ValueError, TypeError):
        return False


def get_canvas_size_from_root(root_layer):
    """
    从根图层提取画布尺寸
    
    Args:
        root_layer: psd-layers.json 中的根图层对象
    
    Returns:
        list: [width, height] 或 None（如果无法提取）
    """
    if "bbox" not in root_layer:
        return None
    
    bbox = root_layer["bbox"]
    if not validate_bbox(bbox):
        return None
    
    x1, y1, x2, y2 = bbox
    return [x2 - x1, y2 - y1]
