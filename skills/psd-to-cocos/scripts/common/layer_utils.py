"""图层可见性提取工具"""

def extract_visible_layers(layer_data, parent_path="", parent_visible=True):
    """
    递归提取所有可见图层
    
    Args:
        layer_data: 图层数据（可以是单个图层或图层列表）
        parent_path: 父路径（用于生成唯一ID）
        parent_visible: 父元素是否可见（用于传递可见性状态）
    
    Returns:
        list: 可见图层列表，每项包含 name, original_name, kind, bbox, path
    
    Example:
        >>> data = [{'name': 'bg', 'visible': True, 'bbox': [0,0,100,100], 'kind': 'pixel'}]
        >>> extract_visible_layers(data)
        [{'name': 'bg', 'original_name': 'bg', 'kind': 'pixel', 'bbox': [0,0,100,100], 'path': 'bg'}]
    """
    visible_layers = []
    
    if isinstance(layer_data, list):
        for item in layer_data:
            visible_layers.extend(extract_visible_layers(item, parent_path, parent_visible))
        return visible_layers
    
    if not isinstance(layer_data, dict):
        return visible_layers
    
    is_visible = layer_data.get("visible", True)
    if not parent_visible or not is_visible:
        return visible_layers
    
    if "bbox" in layer_data:
        layer_info = {
            "name": layer_data.get("name", "unnamed"),
            "original_name": layer_data.get("originalName", layer_data.get("name", "unnamed")),
            "kind": layer_data.get("kind", "unknown"),
            "bbox": layer_data["bbox"],
            "path": parent_path + "/" + layer_data.get("name", "unnamed") if parent_path else layer_data.get("name", "unnamed")
        }
        visible_layers.append(layer_info)
    
    if "children" in layer_data and isinstance(layer_data["children"], list):
        for child in layer_data["children"]:
            visible_layers.extend(
                extract_visible_layers(
                    child, 
                    parent_path + "/" + layer_data.get("name", "") if parent_path else layer_data.get("name", ""),
                    is_visible
                )
            )
    return visible_layers


def extract_visible_layers_nested(layer_data, parent_visible=True):
    """
    递归提取所有可见图层（保留嵌套结构）
    
    始终返回 list，即使是单个图层也包装成 list
    
    Args:
        layer_data: 图层数据（可以是单个图层或图层列表）
        parent_visible: 父元素是否可见
    
    Returns:
        list: 可见图层列表，保留嵌套结构
    """
    result = []
    
    if isinstance(layer_data, list):
        for item in layer_data:
            result.extend(extract_visible_layers_nested(item, parent_visible))
        return result
    
    if not isinstance(layer_data, dict):
        return []
    
    # 检查可见性
    is_visible = layer_data.get("visible", True)
    if not parent_visible or not is_visible:
        return []
    
    # 构建当前图层信息
    layer_info = {}
    for key, value in layer_data.items():
        if key not in ['visible', 'children']:
            layer_info[key] = value
    
    # 递归处理子图层
    if "children" in layer_data and isinstance(layer_data["children"], list):
        children_result = extract_visible_layers_nested(
            layer_data["children"], is_visible
        )
        if children_result:
            layer_info["children"] = children_result
    
    result.append(layer_info)
    return result

