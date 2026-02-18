#!/usr/bin/env python3
"""PSD to Cocos CLI 入口"""
import sys
import os
import subprocess
import argparse
import json

# Import common modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import extract_visible_layers, create_button_config, create_cocos_layout_output
from utils.filename_normalizer import normalize_psd_filename


def check_dependencies():
    """检查必需的依赖是否已安装"""
    try:
        import psd_tools
    except ImportError:
        print("Error: psd-tools not installed.")
        print("Please run: pip install psd-tools")
        sys.exit(1)
    
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow not installed.")
        print("Please run: pip install Pillow")
        sys.exit(1)


def get_skill_path(skill_name):
    """获取技能脚本路径"""
    # 首先检查环境变量
    base_path = os.environ.get("CLAUDE_SKILLS_PATH")
    if base_path:
        return os.path.join(base_path, skill_name, "scripts")
    
    # 默认路径：当前技能目录的同级目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    skills_base = os.path.dirname(current_dir)
    return os.path.join(skills_base, skill_name, "scripts")


def run_psd_layer_reader(psd_file, output_dir):
    """运行 psd-layer-reader 导出图层结构"""
    reader_script = os.path.join(get_skill_path("psd-layer-reader"), "psd_layers.py")
    
    if not os.path.exists(reader_script):
        print(f"Error: psd-layer-reader not found at {reader_script}")
        print("Please ensure psd-layer-reader skill is installed")
        return False
    
    output_file = os.path.join(output_dir, "psd_layers.json")
    
    try:
        result = subprocess.run(
            [sys.executable, reader_script, "--psd", psd_file, "-o", output_file],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running psd-layer-reader: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def run_psd_slicer(psd_file, output_dir, mapping_json):
    """运行 psd-slicer 导出 PNG 切片"""
    slicer_script = os.path.join(get_skill_path("psd-slicer"), "export_slices.py")
    
    if not os.path.exists(slicer_script):
        print(f"Error: psd-slicer not found at {slicer_script}")
        print("Please ensure psd-slicer skill is installed")
        return False
    
    images_dir = os.path.join(output_dir, "images")
    
    try:
        result = subprocess.run(
            [sys.executable, slicer_script, "--psd", psd_file, "-o", images_dir, "--mapping-json", mapping_json],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running psd-slicer: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def generate_cocos_layout(psd_layers_json, output_dir, psd_file_name, flat=False, normalized_name=""):
    """生成 Cocos 布局 JSON"""
    # 导入 converter 函数
    from converter import bbox_to_cocos_position, validate_bbox, get_canvas_size_from_root
    
    try:
        with open(psd_layers_json, 'r', encoding='utf-8') as f:
            psd_data = json.load(f)
    except Exception as e:
        print(f"Error reading {psd_layers_json}: {e}")
        return False
    
    def extract_canvas_size(data):
        candidates = []
        
        def collect_layers(item):
            if isinstance(item, list):
                for child in item:
                    collect_layers(child)
            elif isinstance(item, dict):
                if item.get("visible", True) and "bbox" in item:
                    bbox = item["bbox"]
                    if validate_bbox(bbox):
                        x1, y1, x2, y2 = bbox
                        width = x2 - x1
                        height = y2 - y1
                        area = width * height
                        is_origin = abs(x1) < 10 and abs(y1) < 10
                        candidates.append({
                            "width": width,
                            "height": height,
                            "area": area,
                            "is_origin": is_origin,
                            "bbox": bbox,
                            "name": item.get("name", "unnamed")
                        })
                if "children" in item:
                    collect_layers(item["children"])
        
        collect_layers(data)
        
        if not candidates:
            return None
        
        origin_candidates = [c for c in candidates if c["is_origin"]]
        if origin_candidates:
            best = max(origin_candidates, key=lambda x: x["area"])
            return [best["width"], best["height"]]
        
        best = max(candidates, key=lambda x: x["area"])
        return [best["width"], best["height"]]
    
    canvas_size = extract_canvas_size(psd_data)
    
    if not canvas_size:
        print("Warning: Could not extract canvas size from visible layers, using default 1920x1080")
        canvas_size = [1920, 1080]
    
    if flat:
        # 平铺模式（向后兼容）
        visible_layers_data = extract_visible_layers(psd_data)
        
        elements = []
        canvas_width, canvas_height = canvas_size
        for layer_info in visible_layers_data:
            bbox = layer_info["bbox"]
            cocos = bbox_to_cocos_position(bbox, canvas_size)
            name = layer_info["name"]
            is_button = isinstance(name, str) and name.startswith("btn-")

            element = {
                "id": name,
                "name": name,
                "original_name": layer_info["original_name"],
                "type": "button" if is_button else ("sprite" if layer_info["kind"] == "pixel" else "node"),
                "visible": True,
                "psd_bbox": bbox,
                "cocos_position": {
                    "x": round(cocos["x"] - canvas_width / 2, 2),
                    "y": round(cocos["y"] - canvas_height / 2, 2)
                },
                "cocos_size": {"width": cocos["width"], "height": cocos["height"]},
                "cocos_anchor": {"x": 0.5, "y": 0.5},
                "image_file": f"images/{name}.png"
            }

            if is_button:
                element["button_config"] = create_button_config()

            elements.append(element)
    else:
        # 嵌套模式（默认）
        from common.layer_utils import extract_visible_layers_nested
        from common.element_builder import create_element_nested
        
        visible_layers_data = extract_visible_layers_nested(psd_data)
        
        elements = []
        for layer_info in visible_layers_data:
            element = create_element_nested(layer_info, canvas_size, bbox_to_cocos_position,
                                          center_coordinates=True, parent_cocos_pos=None)
            elements.append(element)
    
    # 使用公共模块构建输出
    output_data = create_cocos_layout_output(elements, psd_file_name, canvas_size)
    
    output_file = os.path.join(output_dir, "cocos_layout.json")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Generated cocos_layout.json")
        print(f"  - Elements: {len(elements)}")
        print(f"  - Canvas: {canvas_size[0]}x{canvas_size[1]}")
        return True
    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        return False


def main():
    # Python 版本检查
    if sys.version_info < (3, 8):
        print("Error: Python 3.8+ required")
        sys.exit(1)
    
    # 依赖检查
    check_dependencies()
    
    # 解析参数
    parser = argparse.ArgumentParser(
        description='Convert PSD to Cocos Creator layout',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python psd_to_cocos.py design.psd              # Nested structure (default)
  python psd_to_cocos.py design.psd --flat       # Flat structure
  python psd_to_cocos.py design.psd -o ./assets/ui/
  python psd_to_cocos.py design.psd -v
        """
    )
    parser.add_argument('psd_file', help='PSD file path')
    parser.add_argument('-o', '--output', default='./output/', help='Output directory (default: ./output/)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--flat', '-f', action='store_true',
                       help='Use flat structure instead of nested (default: nested)')
    parser.add_argument('--nested', '-n', action='store_true',
                       help='Use nested structure (default)')
    args = parser.parse_args()
    
    # 检查 PSD 文件存在
    if not os.path.exists(args.psd_file):
        print(f"Error: File not found: {args.psd_file}")
        sys.exit(1)
    
    # 检查是否是 PSD 文件
    if not args.psd_file.lower().endswith('.psd'):
        print(f"Warning: File does not have .psd extension: {args.psd_file}")
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    psd_name = os.path.basename(args.psd_file)
    
    print(f"Converting: {psd_name}")
    print(f"Output: {os.path.abspath(args.output)}\n")
    
    # Step 1: 导出图层结构
    print("Step 1/3: Exporting layer structure...")
    if not run_psd_layer_reader(args.psd_file, args.output):
        sys.exit(1)
    
    # Step 2: 导出 PNG 切片
    print("\nStep 2/3: Exporting PNG slices...")
    psd_layers_json = os.path.join(args.output, "psd_layers.json")
    if not run_psd_slicer(args.psd_file, args.output, psd_layers_json):
        sys.exit(1)
    
    # Step 3: 生成 Cocos 布局
    print("\nStep 3/3: Generating Cocos layout...")
    flat_mode = args.flat

    # 计算 normalized_name
    normalized_name = normalize_psd_filename(psd_name)

    if not generate_cocos_layout(psd_layers_json, args.output, psd_name,
                                flat=flat_mode, normalized_name=normalized_name):
        sys.exit(1)
    
    print("\n" + "="*50)
    print("✓ Conversion completed successfully!")
    print("="*50)
    print(f"\nOutput files:")
    print(f"  - {os.path.join(args.output, 'psd_layers.json')}")
    print(f"  - {os.path.join(args.output, 'images/*.png')}")
    print(f"  - {os.path.join(args.output, 'cocos_layout.json')}")
    print(f"\nNext steps:")
    print(f"  1. Copy images to your Cocos project's assets folder")
    print(f"  2. Reference cocos_layout.json for positioning sprites")


if __name__ == '__main__':
    main()
