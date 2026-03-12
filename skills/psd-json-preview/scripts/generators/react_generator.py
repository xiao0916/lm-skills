#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 React 组件及 CSS Modules
"""

import html
import json
import shutil
import sys
from pathlib import Path

_SHARED_DIR = str(Path(__file__).resolve().parent.parent)
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

# 从 utils 导入
from utils.layer_name_translator import LayerNameTranslator
from utils.shared_psd_utils import assign_bem_class_names, assign_preserve_names, ensure_dir
from . import text_processor

# 从 generators/common 导入
from generators.common import _clone_layers_hierarchical

def _apply_react_class_names(layers, component_name, preserve_names=False):
    """为 React 输出分配类名，并同步到 layer['class_name']"""
    if preserve_names:
        assign_preserve_names(layers)
    else:
        assign_bem_class_names(layers, component_name)

    def walk(items):
        for it in items:
            bem = it.get("bem_class")
            if bem:
                it["class_name"] = bem
            if it.get("children"):
                walk(it["children"])

    walk(layers)

def generate_jsx_from_layers(layers, component_name, preserve_names=False, translator=None):
    """直接从图层树生成 JSX（不依赖 HTML 解析）"""
    if translator is None:
        translator = LayerNameTranslator()

    def class_attr(class_name):
        return 'className={styles["' + str(class_name) + '"]}'

    def render_layer(layer, indent=8):
        indent_str = " " * indent
        class_name = layer.get("class_name") or "layer"
        children = layer.get("children", [])
        name = layer.get("name", "")
        kind = layer.get("kind", "pixel")

        raw_comment = translator.format_comment(name, kind=kind)
        jsx_comment = ""
        if raw_comment:
            content = raw_comment[4:-3] if raw_comment.startswith("<!--") and raw_comment.endswith("-->") else raw_comment
            jsx_comment = '{/* ' + content + ' */}'

        if children:
            lines = []
            if jsx_comment:
                lines.append('{}{}'.format(indent_str, jsx_comment))
            lines.append("{}<div {}>".format(indent_str, class_attr(class_name)))
            for child in children:
                lines.extend(render_layer(child, indent + 2))
            lines.append("{}</div>".format(indent_str))
            return lines

        if layer.get("image"):
            alt_text = translator.translate_for_alt(name)
            aria = alt_text or name or "图层"
            lines = []
            if jsx_comment:
                lines.append('{}{}'.format(indent_str, jsx_comment))
            lines.append('{}<div {} aria-label="{}" />'.format(
                indent_str,
                class_attr(class_name),
                html.escape(aria, quote=True),
            ))
            return lines

        text_info = layer.get("text_info") or {}
        run_counter = [0]
        text_jsx = text_processor.render_text_as_jsx(text_info, class_name, run_counter, styles_var="styles")
        
        lines = []
        if jsx_comment:
            lines.append('{}{}'.format(indent_str, jsx_comment))
        lines.append("{}<div {}>{}</div>".format(
            indent_str,
            class_attr(class_name),
            text_jsx,
        ))
        return lines

    jsx_lines = [
        "import React from 'react';",
        "import styles from './index.module.css';",
        "",
        "const {} = () => {{".format(component_name),
        "  return (",
        "    <div className={styles[\"page\"]}>",
        "      <div className={styles[\"canvas\"]}>",
    ]

    for layer in layers:
        jsx_lines.extend(render_layer(layer, indent=8))

    jsx_lines += [
        "      </div>",
        "    </div>",
        "  );",
        "};",
        "",
        "export default {};".format(component_name),
    ]

    return "\n".join(jsx_lines)

def generate_css_modules_for_react(layers, canvas_size, preserve_names=False, translator=None):
    """生成 React 组件的 CSS Modules"""
    if translator is None:
        translator = LayerNameTranslator()

    width, height = canvas_size
    css_lines = [
        ".page { min-height: 100%; display: flex; align-items: flex-start; justify-content: center; padding: 24px; }",
        ".canvas {{ position: relative; width: {}px; height: {}px; background: white; }}".format(width, height),
        "",
    ]

    def render_layer_css(layer):
        lines = []
        class_name = ".{}".format(layer.get("class_name") or "layer")
        rx1, ry1, rx2, ry2 = layer["relative_bbox"]
        w = rx2 - rx1
        h = ry2 - ry1
        kind = layer.get("kind", "pixel")
        name = layer.get("name", "")
        children = layer.get("children", [])

        raw_comment = translator.format_comment(name, kind=kind)
        css_comment = ""
        if raw_comment:
            content = raw_comment[4:-3] if raw_comment.startswith("<!--") and raw_comment.endswith("-->") else raw_comment
            css_comment = "/* {} */".format(content)

        if children:
            if css_comment:
                lines.append(css_comment)
            lines.append("{} {{".format(class_name))
            for k, v in layer.get("layout_css_rules", {}).items():
                lines.append("  {}: {};".format(k, v))
            lines.append("}")
            lines.append("")
            for child in children:
                lines.extend(render_layer_css(child))
            return lines

        image_path = layer.get("image")
        if image_path:
            if css_comment:
                lines.append(css_comment)
            file_name = Path(image_path).name
            lines.append("{} {{".format(class_name))
            for k, v in layer.get("layout_css_rules", {}).items():
                lines.append("  {}: {};".format(k, v))
            lines.append("  background-image: url('./images/{}');".format(file_name))
            lines.append("  background-size: 100% 100%;")
            lines.append("  background-repeat: no-repeat;")
            lines.append("}")
            return lines

        if css_comment:
            lines.append(css_comment)
        lines.append("{} {{".format(class_name))
        
        # 基础布局规则
        for k, v in layer.get("layout_css_rules", {}).items():
            lines.append("  {}: {};".format(k, v))
            
        # 文字特定样式
        text_info = layer.get("text_info") or {}
        text_rules = text_processor.get_text_style_rules(text_info)
        for k, v in text_rules.items():
            if k not in layer.get("layout_css_rules", {}):
                lines.append("  {}: {};".format(k, v))
        
        lines.append("}")
        
        # 文字 Runs 的 CSS
        run_counter = [0]
        run_css_blocks = text_processor.get_text_runs_css(text_info, class_name[1:], run_counter)
        for block in run_css_blocks:
            lines.append(".{} {{".format(block["class"]))
            for k, v in block["rules"].items():
                lines.append("  {}: {};".format(k, v))
            lines.append("}")
        return lines

    for layer in layers:
        css_lines.extend(render_layer_css(layer))

    return "\n".join(css_lines)

def generate_react_component(layers, canvas_size, react_out_dir, component_name, preserve_names=False, translator=None):
    """生成 React 组件目录"""
    react_dir = Path(react_out_dir)
    ensure_dir(react_dir)

    react_layers = _clone_layers_hierarchical(layers)
    # 不强制在这里调用 assign_bem_class_names 因为 main 里可能先生成了别的，但是为了安全再调用也行
    # 原逻辑里似乎依赖了 main.py 里 collect_layers_hierarchical 留下的 class_name
    # 所以直接用也是可以的，不用 _apply_react_class_names

    jsx_text = generate_jsx_from_layers(
        react_layers,
        component_name,
        preserve_names=preserve_names,
        translator=translator,
    )
    css_text = generate_css_modules_for_react(
        react_layers,
        canvas_size,
        preserve_names=preserve_names,
        translator=translator,
    )

    (react_dir / "index.jsx").write_text(jsx_text, encoding="utf-8")
    (react_dir / "index.module.css").write_text(css_text, encoding="utf-8")

    images_out_dir = react_dir / "images"
    ensure_dir(images_out_dir)
    from utils.shared_psd_utils import collect_all_images_hierarchical as collect_images
    all_images = collect_images(react_layers)
    copied = set()
    for img_path in all_images:
        src = Path(img_path)
        if src.name in copied:
            continue
        shutil.copy2(src, images_out_dir / src.name)
        copied.add(src.name)

    return react_dir
