#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSD JSON to HTML/CSS Preview Generator (入口)
- Renders image layers with background-image CSS
- Renders text layers as divs with CSS styling
- Supports text info (font size, line height, color)
"""

import argparse
import sys
from pathlib import Path

# 导入共享工具模块
_SHARED_DIR = str(Path(__file__).resolve().parent / "utils")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)
    
from layer_name_translator import LayerNameTranslator
from shared_psd_utils import (
    load_json, find_root_bbox, collect_layers_hierarchical,
    ensure_dir, collect_all_images_hierarchical
)

# 导入各模块生成器
from generators.html_generator import write_html_hierarchical, write_css_hierarchical
from generators.react_generator import generate_react_component
from generators.vue_generator import generate_vue_component
from generators.common import copy_images

IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

def count_layers(layers_list):
    total = 0
    groups = 0
    images = 0
    for layer in layers_list:
        total += 1
        if layer.get("children"):
            groups += 1
            child_t, child_g, child_i = count_layers(layer["children"])
            total += child_t
            groups += child_g
            images += child_i
        elif layer.get("image"):
            images += 1
    return total, groups, images

def main():
    parser = argparse.ArgumentParser(
        description="PSD JSON to HTML/CSS Preview Generator (默认保留分组结构)"
    )
    parser.add_argument("--json", required=True, help="JSON layer file path")
    parser.add_argument("--images", required=True, help="Images directory path")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--copy-all", action="store_true", help="Copy all images")
    parser.add_argument("--include-text", action="store_true", help="Render text layers as divs")
    parser.add_argument("--flatten", action="store_true", help="平铺所有图层（不保留分组结构）")
    parser.add_argument("--dict", default=None, help="项目级图层名翻译字典 JSON 文件路径")
    parser.add_argument("--generate-react", action="store_true", help="同时生成 React 组件（JSX + CSS Modules）")
    parser.add_argument("--generate-vue", action="store_true", help="同时生成 Vue 组件（Vue 3 SFC）")
    parser.add_argument("--component-name", default="PsdComponent", help="React/Vue 组件名称（默认：PsdComponent）")
    parser.add_argument("--preserve-names", action="store_true", help="React/Vue 组件中保留 PSD 原始图层名作为类名")
    parser.add_argument("--react-only", action="store_true", help="仅生成 React 组件（不生成 HTML 预览）")
    args = parser.parse_args()

    json_path = Path(args.json)
    images_dir = Path(args.images)
    out_dir = Path(args.out)
    
    if not json_path.exists():
        raise SystemExit("JSON file not found: {}".format(json_path))
    if not images_dir.exists():
        raise SystemExit("Images directory not found: {}".format(images_dir))
    
    data = load_json(json_path)
    
    root_bbox = find_root_bbox(data)
    if not root_bbox:
        raise SystemExit("Unable to find root bbox in JSON")
    
    x1, y1, x2, y2 = root_bbox
    canvas_size = (x2 - x1, y2 - y1)
    
    # HTML 预览输出到 preview 子目录
    preview_dir = out_dir / "preview"
    ensure_dir(preview_dir)
    
    # 初始化翻译器
    translator = LayerNameTranslator(args.dict)
    
    if args.flatten:
        print("[错误] 平铺模式暂不支持，请移除 --flatten 参数")
        raise SystemExit(1)
    else:
        # 嵌套模式（新逻辑，默认）
        print("[模式] 保留分组嵌套结构（默认）")
        layers = collect_layers_hierarchical(data, images_dir, args.include_text)
        
        from utils.shared_psd_utils import process_layout_rules
        process_layout_rules(layers)

        # 仅生成 React（不生成 HTML）
        if args.react_only:
            react_out_dir = out_dir / "react-component"
            generate_react_component(
                layers,
                canvas_size,
                react_out_dir,
                args.component_name,
                preserve_names=args.preserve_names,
                translator=translator,
            )
            print("[OK] React component generated: {}".format(react_out_dir))
            return

        # 默认：生成 HTML 预览（向后兼容）
        write_html_hierarchical(preview_dir, layers, translator)
        write_css_hierarchical(preview_dir, canvas_size, layers, translator)
        
        # 复制图片
        images_out_dir = preview_dir / "images"
        copy_images(layers, images_out_dir, args.copy_all, images_dir)

        # 可选：同时生成 React 组件
        if args.generate_react:
            react_out_dir = out_dir / "react-component"
            generate_react_component(
                layers,
                canvas_size,
                react_out_dir,
                args.component_name,
                preserve_names=args.preserve_names,
                translator=translator,
            )
        
        # 可选：同时生成 Vue 组件
        if args.generate_vue:
            vue_out_dir = out_dir / "vue-component"
            generate_vue_component(
                layers,
                canvas_size,
                vue_out_dir,
                args.component_name,
                preserve_names=args.preserve_names,
                translator=translator,
            )
        
        total, groups, images = count_layers(layers)
        
        print("[OK] Preview generated: {}".format(out_dir))
        print("  Canvas size: {}x{} px".format(canvas_size[0], canvas_size[1]))
        print("  Total layers: {}".format(total))
        print("  Group layers: {}".format(groups))
        print("  Image layers: {}".format(images))

if __name__ == "__main__":
    main()
