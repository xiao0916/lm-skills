#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 HTML 预览相关的逻辑
"""

import html
import sys
from pathlib import Path

_SHARED_DIR = str(Path(__file__).resolve().parent.parent)
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

# 从 utils 导入
from utils.layer_name_translator import LayerNameTranslator
from . import text_processor

def render_text_with_runs(text_info, base_class, run_counter):
    """Render text with runs as HTML spans"""
    runs = text_info.get("runs", [])
    if not runs:
        raw_text = text_info.get("text", "")
        return html.escape(raw_text).replace("\n", "<br />")
    
    html_parts = []
    for run in runs:
        run_text = run.get("text", "")
        safe_text = html.escape(run_text).replace("\n", "<br />")
        run_class = "{}_run_{}".format(base_class, run_counter[0])
        run_counter[0] += 1
        html_parts.append('<span class="{}">{}</span>'.format(run_class, safe_text))
    
    return "".join(html_parts)

def write_html_hierarchical(out_dir, layers, translator=None):
    """生成嵌套结构的 HTML"""
    if translator is None:
        translator = LayerNameTranslator()
    
    html_lines = [
        "<!doctype html>",
        "<html lang=\"zh-CN\">",
        "  <head>",
        "    <meta charset=\"UTF-8\" />",
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />",
        "    <title>PSD Preview (嵌套结构)</title>",
        "    <link rel=\"stylesheet\" href=\"./styles.css\" />",
        "  </head>",
        "  <body>",
        "    <div class=\"page\">",
        "      <div class=\"canvas\">",
    ]
    
    def render_layer(layer, indent=8):
        lines = []
        indent_str = " " * indent
        
        name = layer.get("name", "layer")
        kind = layer.get("kind", "pixel")
        class_name = layer["class_name"]
        children = layer.get("children", [])
        
        comment = translator.format_comment(name, kind=kind)
        
        if children:
            # 分组容器
            if comment:
                lines.append('{}{}'.format(indent_str, comment))
            lines.append('{}<div class="{}">'.format(indent_str, class_name))
            for child in children:
                lines.extend(render_layer(child, indent + 2))
            lines.append('{}</div>'.format(indent_str))
        elif layer.get("image"):
            # 图片图层
            if comment:
                lines.append('{}{}'.format(indent_str, comment))
            alt_text = translator.translate_for_alt(name)
            lines.append('{}<div class="{}" aria-label="{}"></div>'.format(indent_str, class_name, alt_text or name))
        else:
            # 文字图层
            text_info = layer.get("text_info") or {}
            run_counter = [0]
            text_html = text_processor.render_text_as_html(text_info, class_name, run_counter)
            if comment:
                lines.append('{}{}'.format(indent_str, comment))
            lines.append('{}<div class="{}">{}</div>'.format(indent_str, class_name, text_html))
        
        return lines
    
    for layer in layers:
        html_lines.extend(render_layer(layer))
    
    html_lines += [
        "      </div>",
        "    </div>",
        "  </body>",
        "</html>",
    ]
    
    (out_dir / "index.html").write_text("\n".join(html_lines), encoding="utf-8")

def write_css_hierarchical(out_dir, canvas_size, layers, translator=None):
    """Generate CSS file with hierarchical structure"""
    if translator is None:
        translator = LayerNameTranslator()

    width, height = canvas_size
    css_lines = [
        "* { box-sizing: border-box; }",
        "html, body { height: 100%; margin: 0; }",
        "body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f5f5; }",
        ".page { min-height: 100%; display: flex; align-items: flex-start; justify-content: center; padding: 24px; }",
        ".canvas {{ position: relative; width: {}px; height: {}px; background: white; }}".format(width, height),
        "",
    ]

    def render_layer_css(layer, is_root=False):
        lines = []
        class_name = ".{}".format(layer['class_name'])
        rx1, ry1, rx2, ry2 = layer["relative_bbox"]
        w = rx2 - rx1
        h = ry2 - ry1
        kind = layer.get("kind", "pixel")
        name = layer.get("name", "")
        children = layer.get("children", [])

        # 使用 translator 生成注释
        raw_comment = translator.format_comment(name, kind=kind)
        css_comment = ""
        if raw_comment:
            content = raw_comment[4:-3] if raw_comment.startswith("<!--") and raw_comment.endswith("-->") else raw_comment
            css_comment = "/* {} */".format(content)

        if children:
            # 分组容器样式
            if css_comment:
                lines.append(css_comment)
            lines.append("{} {{".format(class_name))
            for k, v in layer.get("layout_css_rules", {}).items():
                lines.append("  {}: {};".format(k, v))
            lines.append("}")
            lines.append("")
            
            # 递归处理子元素
            for child in children:
                lines.extend(render_layer_css(child, False))
        else:
            # 叶子节点样式
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
            else:
                # 文字图层
                if css_comment:
                    lines.append(css_comment)
                lines.append("{} {{".format(class_name))
                
                # 基础对齐/定位/大小
                for k, v in layer.get("layout_css_rules", {}).items():
                    lines.append("  {}: {};".format(k, v))
                
                # 文字样式规则
                text_info = layer.get("text_info") or {}
                text_rules = text_processor.get_text_style_rules(text_info)
                for k, v in text_rules.items():
                    # 避免重复 position 等
                    if k not in layer.get("layout_css_rules", {}):
                        lines.append("  {}: {};".format(k, v))
                
                lines.append("}")
                
                # 处理 Runs 的 CSS
                run_counter = [0]
                run_css_blocks = text_processor.get_text_runs_css(text_info, layer["class_name"], run_counter)
                for block in run_css_blocks:
                    lines.append(".{} {{".format(block["class"]))
                    for k, v in block["rules"].items():
                        lines.append("  {}: {};".format(k, v))
                    lines.append("}")
        
        return lines
    
    for layer in layers:
        css_lines.extend(render_layer_css(layer, True))
    
    (out_dir / "styles.css").write_text("\n".join(css_lines), encoding="utf-8")


def write_html(out_dir, layers, translator=None):
    """Generate HTML file (向后兼容非嵌套版本)"""
    if translator is None:
        translator = LayerNameTranslator()
    
    html_lines = [
        "<!doctype html>",
        "<html lang=\"zh-CN\">",
        "  <head>",
        "    <meta charset=\"UTF-8\" />",
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />",
        "    <title>PSD Preview</title>",
        "    <link rel=\"stylesheet\" href=\"./styles.css\" />",
        "  </head>",
        "  <body>",
        "    <div class=\"page\">",
        "      <div class=\"canvas\">",
    ]

    children_by_parent = {}
    for layer in layers:
        parent = layer.get("parent_name")
        if parent:
            children_by_parent.setdefault(parent, []).append(layer)

    run_counter = [0]

    for layer in layers:
        if layer.get("image"):
            class_name = layer["class_name"]
            original = layer.get("original_name", layer["name"])
            layer_name = layer["name"]
            comment = translator.format_comment(layer_name, kind="pixel")
            alt_text = translator.translate_for_alt(layer_name)
            children = children_by_parent.get(layer["name"], [])
            if children:
                if comment:
                    html_lines.append("        {}".format(comment))
                html_lines.append(
                    '        <div class="{}" aria-label="{}">'.format(class_name, alt_text or original)
                )
                for child in children:
                    child_class = child["class_name"]
                    text_info = child.get("text_info") or {}
                    text_html = render_text_with_runs(text_info, child_class, run_counter)
                    html_lines.append('          <div class="{}">{}</div>'.format(child_class, text_html))
                html_lines.append("        </div>")
            else:
                if comment:
                    html_lines.append("        {}".format(comment))
                html_lines.append(
                    '        <div class="{}" aria-label="{}"></div>'.format(class_name, alt_text or original)
                )
        else:
            if layer.get("parent_name"):
                continue
            class_name = layer["class_name"]
            layer_name = layer["name"]
            comment = translator.format_comment(layer_name, kind="type")
            text_info = layer.get("text_info") or {}
            text_html = render_text_with_runs(text_info, class_name, run_counter)
            if comment:
                html_lines.append("        {}".format(comment))
            html_lines.append('        <div class="{}">{}</div>'.format(class_name, text_html))

    html_lines += [
        "      </div>",
        "    </div>",
        "  </body>",
        "</html>",
    ]

    (out_dir / "index.html").write_text("\n".join(html_lines), encoding="utf-8")


def write_css(out_dir, canvas_size, layers):
    """Generate CSS file (向后兼容非嵌套版本)"""
    width, height = canvas_size
    css_lines = [
        "* { box-sizing: border-box; }",
        "html, body { height: 100%; margin: 0; }",
        "body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f5f5; }",
        ".page { min-height: 100%; display: flex; align-items: flex-start; justify-content: center; padding: 24px; }",
        ".canvas {{ position: relative; width: {}px; height: {}px; background: white; }}".format(width, height),
    ]
    
    images_by_name = {layer["name"]: layer for layer in layers if layer.get("image")}
    run_counter = [0]

    for layer in layers:
        class_name = ".{}".format(layer['class_name'])
        x1, y1, x2, y2 = layer["bbox"]
        w = x2 - x1
        h = y2 - y1
        
        image_path = layer.get("image")
        if image_path:
            file_name = Path(image_path).name
            css_lines.append(
                "{} {{ ".format(class_name) +
                "position: absolute; display: block; " +
                "left: {}px; top: {}px; width: {}px; height: {}px; ".format(x1, y1, w, h) +
                "background-image: url('./images/{}'); ".format(file_name) +
                "background-size: 100% 100%; background-repeat: no-repeat; " +
                "}"
            )
        else:
            parent = layer.get("parent_name")
            if parent and parent in images_by_name:
                parent_bbox = images_by_name[parent]["bbox"]
                x1 -= parent_bbox[0]
                y1 -= parent_bbox[1]
            text_info = layer.get("text_info") or {}
            style_parts = [
                "position: absolute",
                "display: block",
                "left: {}px".format(x1),
                "top: {}px".format(y1),
                "width: {}px".format(w),
                "height: {}px".format(h),
                "padding: 0",
                "overflow: hidden",
                "white-space: pre-wrap",
            ]

            font_size = text_info.get("fontSize")
            default_font_size = font_size if font_size is not None else 12
            if font_size is not None:
                style_parts.append("font-size: {}px".format(font_size))
            else:
                style_parts.append("font-size: {}px".format(default_font_size))

            font_name = text_info.get("fontName")
            if font_name:
                style_parts.append("font-family: '{}', sans-serif".format(font_name))

            color = text_info.get("color")
            if isinstance(color, list) and len(color) == 4:
                r, g, b, a = color
                alpha = max(0, min(1, a / 255))
                style_parts.append("color: rgba({}, {}, {}, {:.3f})".format(r, g, b, alpha))
            else:
                style_parts.append("color: rgba(0, 0, 0, 1)")

            leading = text_info.get("leading")
            if leading is not None:
                style_parts.append("line-height: {}px".format(leading))
            else:
                style_parts.append("line-height: {}px".format(int(default_font_size * 1.5)))

            tracking = text_info.get("tracking")
            if tracking is not None:
                style_parts.append("letter-spacing: {}px".format(tracking))

            alignment = text_info.get("alignment")
            align_map = {0: "left", 1: "center", 2: "right", 3: "justify"}
            if alignment in align_map:
                style_parts.append("text-align: {}".format(align_map[alignment]))

            css_lines.append("{} {{ {}; }}".format(class_name, "; ".join(style_parts)))
            
            # Generate CSS for each run
            runs = text_info.get("runs", [])
            if runs:
                for run in runs:
                    run_class = ".{}_run_{}".format(layer['class_name'], run_counter[0])
                    run_counter[0] += 1
                    run_styles = []
                    
                    run_font_size = run.get("fontSize")
                    if run_font_size is not None:
                        run_styles.append("font-size: {}px".format(run_font_size))
                    
                    run_color = run.get("color")
                    if isinstance(run_color, list) and len(run_color) == 4:
                        r, g, b, a = run_color
                        alpha = max(0, min(1, a / 255))
                        run_styles.append("color: rgba({}, {}, {}, {:.3f})".format(r, g, b, alpha))
                    
                    run_leading = run.get("leading")
                    if run_leading is not None:
                        run_styles.append("line-height: {}px".format(run_leading))
                    
                    run_tracking = run.get("tracking")
                    if run_tracking is not None:
                        run_styles.append("letter-spacing: {}px".format(run_tracking))
                    
                    run_font_name = run.get("fontName")
                    if run_font_name:
                        run_styles.append("font-family: '{}', sans-serif".format(run_font_name))
                    
                    if run_styles:
                        css_lines.append("{} {{ {}; }}".format(run_class, "; ".join(run_styles)))
    
    (out_dir / "styles.css").write_text("\n".join(css_lines), encoding="utf-8")
