# -*- coding: utf-8 -*-
import html
import json
from pathlib import Path

def get_text_style_rules(text_info):
    """提取 textInfo 并返回 CSS 属性字典"""
    rules = {
        "position": "absolute",
        "display": "block",
        "padding": "0",
        "overflow": "hidden",
        "white-space": "pre-wrap",
    }

    font_size = text_info.get("fontSize")
    default_font_size = font_size if font_size is not None else 12
    rules["font-size"] = "{}px".format(default_font_size)

    font_name = text_info.get("fontName")
    if font_name:
        rules["font-family"] = "'{}', sans-serif".format(font_name)

    color = text_info.get("color")
    if isinstance(color, list) and len(color) == 4:
        r, g, b, a = color
        alpha = max(0, min(1, a / 255))
        rules["color"] = "rgba({}, {}, {}, {:.3f})".format(r, g, b, alpha)
    else:
        rules["color"] = "rgba(0, 0, 0, 1)"

    leading = text_info.get("leading")
    if leading is not None:
        rules["line-height"] = "{}px".format(leading)
    else:
        rules["line-height"] = "{}px".format(int(default_font_size * 1.5))

    tracking = text_info.get("tracking")
    if tracking is not None:
        rules["letter-spacing"] = "{}px".format(tracking)

    alignment = text_info.get("alignment")
    align_map = {0: "left", 1: "center", 2: "right", 3: "justify"}
    if alignment in align_map:
        rules["text-align"] = align_map[alignment]

    return rules

def get_run_style_rules(run):
    """提取单个 Run 的 CSS 属性词典"""
    rules = {}
    
    font_size = run.get("fontSize")
    if font_size is not None:
        rules["font-size"] = "{}px".format(font_size)
    
    color = run.get("color")
    if isinstance(color, list) and len(color) == 4:
        r, g, b, a = color
        alpha = max(0, min(1, a / 255))
        rules["color"] = "rgba({}, {}, {}, {:.3f})".format(r, g, b, alpha)
    
    leading = run.get("leading")
    if leading is not None:
        rules["line-height"] = "{}px".format(leading)
    
    tracking = run.get("tracking")
    if tracking is not None:
        rules["letter-spacing"] = "{}px".format(tracking)
    
    font_name = run.get("fontName")
    if font_name:
        rules["font-family"] = "'{}', sans-serif".format(font_name)
        
    return rules

def render_text_as_html(text_info, base_class, run_counter):
    """生成带有 <span> 的 HTML 字符串"""
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

def render_text_as_jsx(text_info, base_class, run_counter, styles_var="styles"):
    """生成适配 React 的 JSX 文本结构"""
    runs = text_info.get("runs", [])
    if not runs:
        raw_text = text_info.get("text", "")
        # React 中直接使用 { "text" } 即可，它会自动转义，但换行需要处理
        if "\n" in raw_text:
            parts = raw_text.split("\n")
            jsx_parts = []
            for i, p in enumerate(parts):
                if p: jsx_parts.append(json.dumps(p, ensure_ascii=False))
                if i < len(parts) - 1: jsx_parts.append("<br />")
            return "{" + " ".join(jsx_parts) + "}"
        return "{ " + json.dumps(raw_text, ensure_ascii=False) + " }"
    
    jsx_parts = []
    for run in runs:
        run_text = run.get("text", "")
        run_class = "{}_run_{}".format(base_class, run_counter[0])
        run_counter[0] += 1
        
        # 处理内部换行
        if "\n" in run_text:
            text_segments = run_text.split("\n")
            seg_jsx = []
            for i, seg in enumerate(text_segments):
                if seg: seg_jsx.append(json.dumps(seg, ensure_ascii=False))
                if i < len(text_segments) - 1: seg_jsx.append("<br />")
            content = " ".join(seg_jsx)
        else:
            content = json.dumps(run_text, ensure_ascii=False)
            
        jsx_parts.append('<span className={{{}["{}"]}}>{{{}}}</span>'.format(styles_var, run_class, content))
    
    return " ".join(jsx_parts)

def render_text_as_vue(text_info, base_class, run_counter):
    """生成适配 Vue Template 的文本结构"""
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

def get_text_runs_css(text_info, base_class, run_counter):
    """生成多样式文本段（Runs）对应的 CSS 规则列表（字典数组）"""
    runs = text_info.get("runs", [])
    css_blocks = []
    
    for run in runs:
        run_class = "{}_run_{}".format(base_class, run_counter[0])
        run_counter[0] += 1
        
        rules = get_run_style_rules(run)
        if rules:
            css_blocks.append({
                "class": run_class,
                "rules": rules
            })
            
    return css_blocks
