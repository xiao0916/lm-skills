#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSD JSON to HTML/CSS Preview Generator
- Renders image layers with background-image CSS
- Renders text layers as divs with CSS styling
- Supports text info (font size, line height, color)
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

# 导入共享翻译模块和工具模块
_SHARED_DIR = str(Path(__file__).resolve().parent / "utils")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)
from layer_name_translator import LayerNameTranslator
from shared_psd_utils import (
    load_json, find_root_bbox, collect_layers_hierarchical,
    collect_all_images_hierarchical, ensure_dir,
    assign_bem_class_names, assign_preserve_names
)


IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

GENERIC_NAMES = {
    "<图像>", "<编组>", "<路径>", "<形状>",
    "<image>", "<group>", "<path>", "<shape>",
    "<图层>", "<layer>", "<矩形>", "<rectangle>"
}


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


def to_kebab_case(name):
    """将 PascalCase 转换为 kebab-case"""
    return re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()


def to_camel_case(name):
    """将连字符命名转换为驼峰命名"""
    parts = name.split("-")
    if not parts:
        return name
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def sanitize_component_name(name):
    """清理组件名称，移除非法字符，只保留字母、数字和下划线

    参数:
        name: 原始名称（可能包含中文、特殊字符等）

    返回:
        清理后的名称，只保留字母、数字和下划线
    """
    # 保留字母、数字、中文和下划线，其他字符移除
    cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', name)
    # 如果以数字开头，添加下划线前缀
    if cleaned and cleaned[0].isdigit():
        cleaned = '_' + cleaned
    return cleaned


def to_pascal_case(name):
    """将各种命名格式转换为 PascalCase

    支持的输入格式：
    - kebab-case (如 card-group)
    - snake_case (如 card_group)
    - camelCase (如 cardGroup)
    - 中文名称（如 卡片组）

    参数:
        name: 原始名称

    返回:
        PascalCase 格式的名称
    """
    if not name:
        return name

    # 先按连字符和下划线分割（kebab-case 和 snake_case）
    words = re.split(r'[-_]', name)
    words = [w for w in words if w]  # 过滤空字符串

    if not words:
        # 如果没有分割出单词，清理整个名称
        return sanitize_component_name(name).capitalize()

    # 处理每个单词：清理并处理 camelCase
    expanded_words = []
    for word in words:
        # 清理单词（移除特殊字符）
        clean_word = sanitize_component_name(word)
        if not clean_word:
            continue

        # 在 camelCase 转换处分割（如 cardGroup -> card Group）
        sub_words = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean_word).split()
        expanded_words.extend(sub_words)

    if not expanded_words:
        return name.capitalize()

    # 将每个单词首字母大写
    return ''.join(word.capitalize() for word in expanded_words)


def ensure_unique_names(names):
    """确保名称列表中的名称都是唯一的

    当遇到重复名称时，会自动添加数字后缀（如 header, header2, header3）

    参数:
        names: 名称列表

    返回:
        处理后的唯一名称列表
    """
    if not names:
        return []

    seen = {}  # 记录每个名称出现的次数
    result = []

    for name in names:
        if name in seen:
            seen[name] += 1
            new_name = "{}{}".format(name, seen[name])
            result.append(new_name)
        else:
            seen[name] = 1
            result.append(name)

    return result


def kebab_case(name):
    """将名称转换为 kebab-case（用于文件名）

    支持的输入格式：
    - PascalCase (如 CardGroup)
    - camelCase (如 cardGroup)
    - snake_case (如 card_group)

    参数:
        name: 原始名称

    返回:
        kebab-case 格式的小写名称
    """
    if not name:
        return name

    # 替换下划线和空格为连字符
    name = re.sub(r'[_\s]', '-', name)

    # 在大小写转换处插入连字符（如 CardGroup -> Card-Group）
    # 处理首字母大写后续字母小写的情况
    name = re.sub(r'(?<!^)(?<!-)(?=[A-Z])', '-', name)

    # 处理连续大写字母（如 HTTPRequest -> HTTP-Request）
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', '-', name)

    # 转换为小写并移除多余的连字符
    name = re.sub(r'-+', '-', name).lower()

    # 移除首尾连字符
    return name.strip('-')


def collect_all_images_hierarchical(layers, result = None):
    """递归收集所有图片路径"""
    if result is None:
        result = []
    
    for layer in layers:
        if layer.get("image"):
            result.append(Path(layer["image"]))
        if layer.get("children"):
            collect_all_images_hierarchical(layer["children"], result)
    
    return result



def write_html_hierarchical(out_dir, layers, translator = None):
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
    
    def render_layer(layer, indent = 8):
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
            lines.append('{}<div class="{}" role="img" aria-label="{}"></div>'.format(indent_str, class_name, alt_text or name))
        else:
            # 文字图层
            text_info = layer.get("text_info") or {}
            text_html = html.escape(text_info.get("text", "")).replace("\n", "<br />")
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
        ".canvas {{ position: relative; width: {width}px; height: {height}px; background: white; }}".format(width=width, height=height),
        "",
    ]

    def render_layer_css(layer, is_root = False):
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
            lines.append("  position: absolute;")
            lines.append("  display: block;")
            lines.append("  left: {}px;".format(rx1))
            lines.append("  top: {}px;".format(ry1))
            lines.append("  width: {}px;".format(w))
            lines.append("  height: {}px;".format(h))
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
                lines.append(
                    "{} {{ ".format(class_name) +
                    "position: absolute; display: block; " +
                    "left: {}px; top: {}px; width: {}px; height: {}px; ".format(rx1, ry1, w, h) +
                    "background-image: url('./images/{}'); ".format(file_name) +
                    "background-size: 100% 100%; background-repeat: no-repeat; " +
                    "}"
                )
            else:
                # 文字图层
                if css_comment:
                    lines.append(css_comment)
                lines.append(
                    "{} {{ ".format(class_name) +
                    "position: absolute; display: block; " +
                    "left: {}px; top: {}px; width: {}px; height: {}px; ".format(rx1, ry1, w, h) +
                    "}"
                )
        
        return lines
    
    for layer in layers:
        css_lines.extend(render_layer_css(layer, True))
    
    (out_dir / "styles.css").write_text("\n".join(css_lines), encoding="utf-8")


def _clone_layers_hierarchical(layers):
    """浅拷贝图层树（保留 Path 等对象），避免影响 HTML 预览的 class_name"""
    cloned = []
    for layer in layers:
        new_layer = dict(layer)
        children = layer.get("children")
        if children:
            new_layer["children"] = _clone_layers_hierarchical(children)
        cloned.append(new_layer)
    return cloned


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
        # 使用字符串拼接避免 format 方法与花括号冲突
        return 'className={styles["' + str(class_name) + '"]}'

    def render_layer(layer, indent=8):
        indent_str = " " * indent
        class_name = layer.get("class_name") or "layer"
        children = layer.get("children", [])
        name = layer.get("name", "")
        kind = layer.get("kind", "pixel")

        # 生成注释（与 HTML 预览一致）
        # format_comment 返回 "<!-- comment -->"，需要转换为 JSX 格式 "{/* comment */}"
        raw_comment = translator.format_comment(name, kind=kind)
        jsx_comment = ""
        if raw_comment:
            # 提取 HTML 注释内容并转换为 JSX 格式
            content = raw_comment[4:-3] if raw_comment.startswith("<!--") and raw_comment.endswith("-->") else raw_comment
            jsx_comment = '{/* ' + content + ' */}'

        if children:
            # 分组容器
            lines = []
            if jsx_comment:
                lines.append('{}{}'.format(indent_str, jsx_comment))
            lines.append("{}<div {}>".format(indent_str, class_attr(class_name)))
            for child in children:
                lines.extend(render_layer(child, indent + 2))
            lines.append("{}</div>".format(indent_str))
            return lines

        if layer.get("image"):
            # 图片图层
            alt_text = translator.translate_for_alt(name)
            aria = alt_text or name or "图层"
            lines = []
            if jsx_comment:
                lines.append('{}{}'.format(indent_str, jsx_comment))
            lines.append('{}<div {} role="img" aria-label="{}" />'.format(
                indent_str,
                class_attr(class_name),
                html.escape(aria, quote=True),
            ))
            return lines

        # 文字图层
        text_info = layer.get("text_info") or {}
        text = text_info.get("text", "")
        lines = []
        if jsx_comment:
            lines.append('{}{}'.format(indent_str, jsx_comment))
        lines.append("{}<div {}>{{{}}}</div>".format(
            indent_str,
            class_attr(class_name),
            json.dumps(text, ensure_ascii=False),
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
    """生成 React 组件的 CSS Modules（不包含 HTML reset，只保留预览必要结构与图层规则）"""
    if translator is None:
        translator = LayerNameTranslator()

    width, height = canvas_size
    css_lines = [
        ".page { min-height: 100%; display: flex; align-items: flex-start; justify-content: center; padding: 24px; }",
        ".canvas {{ position: relative; width: {width}px; height: {height}px; background: white; }}".format(
            width=width, height=height
        ),
        ".canvas > div { position: absolute; display: block; }",
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

        # 使用 translator 生成注释
        raw_comment = translator.format_comment(name, kind=kind)
        css_comment = ""
        if raw_comment:
            content = raw_comment[4:-3] if raw_comment.startswith("<!--") and raw_comment.endswith("-->") else raw_comment
            css_comment = "/* {} */".format(content)

        if children:
            if css_comment:
                lines.append(css_comment)
            lines.append("{} {{".format(class_name))
            lines.append("  position: absolute;")
            lines.append("  display: block;")
            lines.append("  left: {}px;".format(rx1))
            lines.append("  top: {}px;".format(ry1))
            lines.append("  width: {}px;".format(w))
            lines.append("  height: {}px;".format(h))
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
            lines.append(
                "{} {{ ".format(class_name)
                + "position: absolute; display: block; "
                + "left: {}px; top: {}px; width: {}px; height: {}px; ".format(rx1, ry1, w, h)
                + "background-image: url('./images/{}'); ".format(file_name)
                + "background-size: 100% 100%; background-repeat: no-repeat; "
                + "}"
            )
            return lines

        # 文字图层：保留换行
        if css_comment:
            lines.append(css_comment)
        lines.append(
            "{} {{ ".format(class_name)
            + "position: absolute; display: block; "
            + "left: {}px; top: {}px; width: {}px; height: {}px; ".format(rx1, ry1, w, h)
            + "white-space: pre-wrap; "
            + "}"
        )
        return lines

    for layer in layers:
        css_lines.extend(render_layer_css(layer))

    return "\n".join(css_lines)


def generate_react_component(layers, canvas_size, react_out_dir, component_name, preserve_names=False, translator=None):
    """生成 React 组件目录：index.jsx + index.module.css + images/"""
    react_dir = Path(react_out_dir)
    ensure_dir(react_dir)

    # 克隆图层树（不污染 HTML 预览）
    # 直接使用 collect_layers_hierarchical() 生成的 class_name
    react_layers = _clone_layers_hierarchical(layers)

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

    # 复制图片（仅复制用到的）
    images_out_dir = react_dir / "images"
    ensure_dir(images_out_dir)
    all_images = collect_all_images_hierarchical(react_layers)
    copied = set()
    for img_path in all_images:
        src = Path(img_path)
        if src.name in copied:
            continue
        shutil.copy2(src, images_out_dir / src.name)
        copied.add(src.name)

    return react_dir


def generate_vue_from_layers(layers, component_name, preserve_names=False, translator=None):
    """直接从图层树生成 Vue template（不依赖 HTML 解析）"""
    if translator is None:
        translator = LayerNameTranslator()

    def class_attr(class_name):
         # Vue 中使用普通 class 属性（配合 <style scoped>）
         return 'class="{}"'.format(str(class_name))

    def render_layer(layer, indent=8):
        indent_str = " " * indent
        class_name = layer.get("class_name") or "layer"
        children = layer.get("children", [])
        name = layer.get("name", "")
        kind = layer.get("kind", "pixel")

        # 生成注释（与 HTML 预览一致）
        # format_comment 返回 "<!-- comment -->"，Vue 直接使用
        comment = translator.format_comment(name, kind=kind)

        if children:
            # 分组容器
            lines = []
            if comment:
                lines.append('{}{}'.format(indent_str, comment))
            lines.append("{}<div {}>".format(indent_str, class_attr(class_name)))
            for child in children:
                lines.extend(render_layer(child, indent + 2))
            lines.append("{}</div>".format(indent_str))
            return lines

        if layer.get("image"):
            # 图片图层
            alt_text = translator.translate_for_alt(name)
            aria = alt_text or name or "图层"
            lines = []
            if comment:
                lines.append('{}{}'.format(indent_str, comment))
            lines.append('{}<div {} role="img" :aria-label="\'{}\'" />'.format(
                indent_str,
                class_attr(class_name),
                html.escape(aria, quote=True),
            ))
            return lines

        # 文字图层
        text_info = layer.get("text_info") or {}
        text = text_info.get("text", "")
        lines = []
        if comment:
            lines.append('{}{}'.format(indent_str, comment))
        lines.append("{}<div {}>{{}}</div>".format(
            indent_str,
            class_attr(class_name),
            json.dumps(text, ensure_ascii=False),
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
    """生成 Vue 组件的 scoped CSS（使用 $style 模块化）"""
    if translator is None:
        translator = LayerNameTranslator()

    width, height = canvas_size
    css_lines = [
        ".page { min-height: 100%; display: flex; align-items: flex-start; justify-content: center; padding: 24px; }",
        ".canvas {{ position: relative; width: {width}px; height: {height}px; background: white; }}".format(
            width=width, height=height
        ),
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

        # 使用 translator 生成注释
        raw_comment = translator.format_comment(name, kind=kind)
        css_comment = ""
        if raw_comment:
            content = raw_comment[4:-3] if raw_comment.startswith("<!--") and raw_comment.endswith("-->") else raw_comment
            css_comment = "/* {} */".format(content)

        if children:
            if css_comment:
                lines.append(css_comment)
            lines.append("{} {{".format(class_name))
            lines.append("  position: absolute;")
            lines.append("  display: block;")
            lines.append("  left: {}px;".format(rx1))
            lines.append("  top: {}px;".format(ry1))
            lines.append("  width: {}px;".format(w))
            lines.append("  height: {}px;".format(h))
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
            lines.append(
                "{} {{ ".format(class_name)
                + "position: absolute; display: block; "
                + "left: {}px; top: {}px; width: {}px; height: {}px; ".format(rx1, ry1, w, h)
                + "background-image: url('./images/{}'); ".format(file_name)
                + "background-size: 100% 100%; background-repeat: no-repeat; "
                + "}"
            )
            return lines

        # 文字图层：保留换行
        if css_comment:
            lines.append(css_comment)
        lines.append(
            "{} {{ ".format(class_name)
            + "position: absolute; display: block; "
            + "left: {}px; top: {}px; width: {}px; height: {}px; ".format(rx1, ry1, w, h)
            + "white-space: pre-wrap; "
            + "}"
        )
        return lines

    for layer in layers:
        css_lines.extend(render_layer_css(layer))

    return "\n".join(css_lines)


def generate_vue_component(layers, canvas_size, vue_out_dir, component_name, preserve_names=False, translator=None):
    """生成 Vue 组件目录：index.vue + images/"""
    vue_dir = Path(vue_out_dir)
    ensure_dir(vue_out_dir)

    # 克隆图层树（不污染 HTML 预览）
    # 直接使用 collect_layers_hierarchical() 生成的 class_name
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

    # 合并为单文件组件 (.vue)
    sfc_content = vue_text + "\n\n<style scoped>\n" + css_text + "\n</style>\n"
    (vue_dir / "index.vue").write_text(sfc_content, encoding="utf-8")

    # 复制图片（仅复制用到的）
    images_out_dir = vue_dir / "images"
    ensure_dir(images_out_dir)
    all_images = collect_all_images_hierarchical(vue_layers)
    copied = set()
    for img_path in all_images:
        src = Path(img_path)
        if src.name in copied:
            continue
        shutil.copy2(src, images_out_dir / src.name)
        copied.add(src.name)

    return vue_dir


def collect_all_images_hierarchical(layers, result = None):
    """递归收集所有图片路径"""
    if result is None:
        result = []

    for layer in layers:
        if layer.get("image"):
            result.append(Path(layer["image"]))
        if layer.get("children"):
            collect_all_images_hierarchical(layer["children"], result)

    return result


def write_html(out_dir, layers, translator = None):
    """Generate HTML file"""
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
                    '        <div class="{}" role="img" aria-label="{}">'.format(class_name, alt_text or original)
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
                    '        <div class="{}" role="img" aria-label="{}"></div>'.format(class_name, alt_text or original)
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
    """Generate CSS file"""
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


def copy_images(layers, out_images, copy_all, images_dir):
    """Copy images to output directory"""
    ensure_dir(out_images)
    
    if copy_all:
        for path in images_dir.iterdir():
            if path.suffix.lower() in IMAGE_EXTS and path.is_file():
                shutil.copy2(path, out_images / path.name)
        return
    
    copied = set()
    for layer in layers:
        if not layer.get("image"):
            continue
        src = Path(layer["image"])
        if src.name in copied:
            continue
        shutil.copy2(src, out_images / src.name)
        copied.add(src.name)


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
    parser.add_argument("--component-name", default="PsdComponent", help="React 组件名称（默认：PsdComponent）")
    parser.add_argument("--preserve-names", action="store_true", help="React 组件中保留 PSD 原始图层名作为类名")
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
    
    ensure_dir(out_dir)
    
    # 初始化翻译器
    translator = LayerNameTranslator(args.dict)
    
    if args.flatten:
        print("[错误] 平铺模式暂不支持，请移除 --flatten 参数")
        raise SystemExit(1)
    else:
        # 嵌套模式（新逻辑，默认）
        print("[模式] 保留分组嵌套结构（默认）")
        layers = collect_layers_hierarchical(data, images_dir, args.include_text)

        # 仅生成 React（不生成 HTML）
        if args.react_only:
            react_out_dir = out_dir.parent / "react-component"
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
        write_html_hierarchical(out_dir, layers, translator)
        write_css_hierarchical(out_dir, canvas_size, layers, translator)
        
        # 复制图片
        all_images = collect_all_images_hierarchical(layers)
        images_out_dir = out_dir / "images"
        ensure_dir(images_out_dir)
        
        if args.copy_all:
            for img_file in images_dir.glob("*"):
                if img_file.is_file() and img_file.suffix.lower() in IMAGE_EXTS:
                    shutil.copy2(img_file, images_out_dir / img_file.name)
        else:
            for img_path in all_images:
                shutil.copy2(img_path, images_out_dir / img_path.name)

        # 可选：同时生成 React 组件（输出到与 preview 同级的目录）
        if args.generate_react:
            react_out_dir = out_dir.parent / "react-component"

            # 单组件模式
            generate_react_component(
                layers,
                canvas_size,
                react_out_dir,
                args.component_name,
                preserve_names=args.preserve_names,
                translator=translator,
            )
        
        # 可选：同时生成 Vue 组件（输出到与 preview 同级的目录）
        if args.generate_vue:
            vue_out_dir = out_dir.parent / "vue-component"

            # 单组件模式
            generate_vue_component(
                layers,
                canvas_size,
                vue_out_dir,
                args.component_name,
                preserve_names=args.preserve_names,
                translator=translator,
            )
        
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
        
        total, groups, images = count_layers(layers)
        
        print("[OK] Preview generated: {}".format(out_dir))
        print("  Canvas size: {}x{} px".format(canvas_size[0], canvas_size[1]))
        print("  Total layers: {}".format(total))
        print("  Group layers: {}".format(groups))
        print("  Image layers: {}".format(images))


if __name__ == "__main__":
    main()
