"""生成 Cocos 布局 JSON"""
import json
import sys
import os


# 添加脚本目录到路径，支持直接运行
sys.path.insert(0, os.path.dirname(__file__))
from converter import bbox_to_cocos_position, validate_bbox, get_canvas_size_from_root
from common import extract_visible_layers, create_button_config, create_cocos_layout_output


def generate_layout(psd_layers_json_path, output_path, psd_file_name,
                   flat=False, normalized_name=""):
    """
    读取 psd-layers.json，生成 cocos_layout.json

    Args:
        psd_layers_json_path: psd-layers.json 文件路径
        output_path: 输出目录路径
        psd_file_name: 原始 PSD 文件名
        flat: 是否使用平铺结构
        normalized_name: 规范化后的 PSD 名称（可选）

    Returns:
        bool: 是否成功
    """
    try:
        # 读取 psd-layers.json
        with open(psd_layers_json_path, 'r', encoding='utf-8') as f:
            psd_data = json.load(f)
    except Exception as e:
        print(f"Error reading {psd_layers_json_path}: {e}")
        return False
    
    # 提取画布尺寸
    canvas_size = None
    if isinstance(psd_data, list) and len(psd_data) > 0:
        canvas_size = get_canvas_size_from_root(psd_data[0])
    elif isinstance(psd_data, dict):
        canvas_size = get_canvas_size_from_root(psd_data)
    
    if not canvas_size:
        print("Warning: Could not extract canvas size from PSD data")
        canvas_size = [1920, 1080]  # 默认尺寸
    
    if flat:
        # 平铺模式（向后兼容）
        visible_layers = extract_visible_layers(psd_data)
        
        # 生成元素列表
        elements = []
        for layer in visible_layers:
            bbox = layer["bbox"]
            cocos_data = bbox_to_cocos_position(bbox, canvas_size)
            name = layer["name"]
            is_button = isinstance(name, str) and name.startswith("btn-")

            element = {
                "id": name,
                "name": name,
                "original_name": layer["original_name"],
                "type": "button" if is_button else ("sprite" if layer["kind"] == "pixel" else "node"),
                "visible": True,
                "psd_bbox": bbox,
                "cocos_position": {
                    "x": cocos_data["x"],
                    "y": cocos_data["y"]
                },
                "cocos_size": {
                    "width": cocos_data["width"],
                    "height": cocos_data["height"]
                },
                "cocos_anchor": {
                    "x": 0.5,
                    "y": 0.5
                },
                "image_file": f"images/{name}.png"
            }

            if is_button:
                element["button_config"] = create_button_config()

            elements.append(element)
    else:
        # 嵌套模式（默认）
        from common.layer_utils import extract_visible_layers_nested
        from common.element_builder import create_element_nested
        
        visible_layers = extract_visible_layers_nested(psd_data)
        
        elements = []
        for layer_info in visible_layers:
            element = create_element_nested(layer_info, canvas_size, bbox_to_cocos_position,
                                          center_coordinates=False, parent_cocos_pos=None)
            elements.append(element)
    
    # 构建输出 JSON
    output_data = create_cocos_layout_output(elements, psd_file_name, canvas_size)
    
    # 确保输出目录存在
    os.makedirs(output_path, exist_ok=True)
    
    # 写入文件
    output_file = os.path.join(output_path, "cocos_layout.json")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Generated: {output_file}")
        print(f"  - Elements: {len(elements)}")
        print(f"  - Canvas: {canvas_size[0]}x{canvas_size[1]}")
        return True
    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Cocos layout from PSD layers')
    parser.add_argument('psd_layers_json', help='Path to psd_layers.json')
    parser.add_argument('output_path', help='Output directory')
    parser.add_argument('psd_file_name', help='Original PSD file name')
    parser.add_argument('--flat', '-f', action='store_true',
                       help='Use flat structure instead of nested (default: nested)')
    parser.add_argument('--nested', '-n', action='store_true',
                       help='Use nested structure (default)')
    
    args = parser.parse_args()
    
    flat_mode = args.flat
    
    from utils.filename_normalizer import normalize_psd_filename
    normalized_name = normalize_psd_filename(args.psd_file_name)
    
    success = generate_layout(args.psd_layers_json, args.output_path, 
                             args.psd_file_name, flat=flat_mode, 
                             normalized_name=normalized_name)
    sys.exit(0 if success else 1)
