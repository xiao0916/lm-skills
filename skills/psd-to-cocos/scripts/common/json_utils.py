"""JSON 输出工具"""
from datetime import datetime
import json
import os

def create_cocos_layout_output(elements, psd_file_name, canvas_size,
                               normalized_name="", version="1.0.0"):
    """
    创建 Cocos 布局输出数据结构

    Args:
        elements: 元素列表（可以是嵌套结构）
        psd_file_name: 原始 PSD 文件名
        canvas_size: [width, height] 画布尺寸
        normalized_name: 规范化后的 PSD 名称（可选，用于 metadata）
        version: 版本号

    Returns:
        dict: 完整的 cocos_layout.json 数据结构
    """
    def count_recursive(element_list):
        count = 0
        for elem in element_list:
            count += 1
            if 'children' in elem:
                count += count_recursive(elem['children'])
        return count

    # 构建基础 metadata
    metadata = {
        "version": version,
        "psd_file": psd_file_name,
        "canvas_size": canvas_size,
        "export_time": datetime.now().isoformat(),
        "element_count": count_recursive(elements)
    }

    # 只有当 normalized_name 非空时才添加到 metadata
    if normalized_name:
        metadata["normalized_name"] = normalized_name

    return {
        "metadata": metadata,
        "elements": elements
    }

def write_layout_json(output_data, output_file_path):
    """
    将布局数据写入 JSON 文件
    
    Args:
        output_data: create_cocos_layout_output 返回的数据
        output_file_path: 输出文件完整路径
    
    Returns:
        bool: 是否成功
    """
    try:
        os.makedirs(os.path.dirname(output_file_path) or '.', exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error writing {output_file_path}: {e}")
        return False
