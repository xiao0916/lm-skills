#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Vue 组件及 Scoped CSS
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
from utils.shared_psd_utils import ensure_dir
from . import text_processor

# 从 generators/common 导入
from generators.common import _clone_layers_hierarchical

def generate_vue_from_layers(layers, component_name, preserve_names=False, translator=None):
    """直接从图层树生成 Vue template（不依赖 HTML 解析）"""
    if translator is None:
        translator = LayerNameTranslator()

    def class_attr(class_name):
         return 'class="{}"'.format(str(class_name))

    def render_layer(layer, indent=8):
        indent_str = " " * indent
        class_name = layer.get("class_name") or "layer"
        children = layer.get("children", [])
        name = layer.get("name", "")
        kind = layer.get("kind", "pixel")

        comment = translator.format_comment(name, kind=kind)

        if children:
            lines = []
            if comment:
                lines.append('{}{}'.format(indent_str, comment))
            lines.append("{}<div {}>".format(indent_str, class_attr(class_name)))
            for child in children:
                lines.extend(render_layer(child, indent + 2))
            lines.append("{}</div>".format(indent_str))
            return lines

        if layer.get("image"):
            alt_text = translator.translate_for_alt(name)
            aria = alt_text or name or "图层"
            lines = []
            if comment:
                lines.append('{}{}'.format(indent_str, comment))
            lines.append('{}<div {} :aria-label="\'{}\'" />'.format(
                indent_str,
                class_attr(class_name),
                html.escape(aria, quote=True),
            ))
            return lines

        text_info = layer.get("text_info") or {}
        run_counter = [0]
        text_vue = text_processor.render_text_as_vue(text_info, class_name, run_counter)
        lines = []
        if comment:
            lines.append('{}{}'.format(indent_str, comment))
        lines.append("{}<div {}>{}</div>".format(
            indent_str,
            class_attr(class_name),
            text_vue,
        ))
        return lines

    template_lines = [
         "<template>",
         "  <div class=\"page\">",
         "    <div class=\"canvas\">",
     ]

    for layer in layers:
        template_lines.extend(render_layer(layer, indent=6))

    template_lines += [
        "    </div>",
        "  </div>",
        "</template>",
    ]

    script_lines = [
        "",
        "<script setup>",
        "// Vue 3 组件 - {}".format(component_name),
        "</script>",
    ]

    return "\n".join(template_lines + script_lines)

def generate_scoped_css_for_vue(layers, canvas_size, preserve_names=False, translator=None):
    """生成 Vue 组件的 scoped CSS"""
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

def generate_vue_component(layers, canvas_size, vue_out_dir, component_name, preserve_names=False, translator=None):
    """生成 Vue 组件目录：index.vue + images/"""
    vue_dir = Path(vue_out_dir)
    ensure_dir(vue_out_dir)

    vue_layers = _clone_layers_hierarchical(layers)

    vue_text = generate_vue_from_layers(
        vue_layers,
        component_name,
        preserve_names=preserve_names,
        translator=translator,
    )
    css_text = generate_scoped_css_for_vue(
        vue_layers,
        canvas_size,
        preserve_names=preserve_names,
        translator=translator,
    )

    sfc_content = vue_text + "\n\n<style scoped>\n" + css_text + "\n</style>\n"
    (vue_dir / "index.vue").write_text(sfc_content, encoding="utf-8")

    images_out_dir = vue_dir / "images"
    ensure_dir(images_out_dir)
    from utils.shared_psd_utils import collect_all_images_hierarchical as collect_images
    all_images = collect_images(vue_layers)
    copied = set()
    for img_path in all_images:
        src = Path(img_path)
        if src.name in copied:
            continue
        shutil.copy2(src, images_out_dir / src.name)
        copied.add(src.name)

    return vue_dir
