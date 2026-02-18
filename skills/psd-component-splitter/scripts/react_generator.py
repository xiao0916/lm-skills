# -*- coding: utf-8 -*-
"""
React 组件生成器模块

从 PSD 图层结构生成 React 组件（JSX + CSS Modules）。
支持生成分组子组件和主入口组件 App.jsx。

主要功能：
- generate_react_split_component: 为第一级分组生成独立的 React 组件
- generate_react_main_entry: 生成 React 主入口组件 App.jsx

兼容性：支持 Python 2.7+ 和 Python 3.x
"""

from __future__ import print_function
import html
import json
import sys
from pathlib import Path

# 导入本地命名工具模块
try:
    from naming_utils import (
        sanitize_component_name,
        to_pascal_case,
        kebab_case,
        ensure_unique_names,
    )
except ImportError:
    # 相对导入失败时，尝试绝对导入（用于直接运行脚本）
    import re

    def sanitize_component_name(name):
        """清理组件名称，移除非法字符"""
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', name)
        if cleaned and cleaned[0].isdigit():
            cleaned = '_' + cleaned
        return cleaned

    def to_pascal_case(name):
        """将各种命名格式转换为 PascalCase"""
        if not name:
            return name
        words = re.split(r'[-_\s]', name)
        words = [w for w in words if w]
        if not words:
            return name.capitalize()
        return ''.join(word.capitalize() for word in words)

    def kebab_case(name):
        """将名称转换为 kebab-case（用于文件名）"""
        if not name:
            return name
        name = re.sub(r'[_\s]', '-', name)
        name = re.sub(r'(?<!^)(?<!-)(?=[A-Z])', '-', name)
        name = re.sub(r'-+', '-', name).lower()
        return name.strip('-')

    def ensure_unique_names(names):
        """确保名称列表中的名称都是唯一的"""
        if not names:
            return []
        seen = {}
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


def ensure_dir(path):
    """确保目录存在，如果不存在则创建"""
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path


def assign_bem_class_names(layers, component_name):
    """为图层分配 BEM 命名规范的类名"""
    block = kebab_case(component_name)
    counters = {"element": 0}

    def walk(items, prefix=None):
        for item in items:
            counters["element"] += 1
            element_name = "{}__elem{}".format(block, counters["element"])
            if prefix:
                element_name = "{}-{}".format(prefix, counters["element"])
            item["bem_class"] = element_name
            children = item.get("children")
            if children:
                walk(children, element_name)

    walk(layers)


def assign_preserve_names(layers, used_names=None):
    """保留原始名称作为类名（与 psd-json-preview 保持一致）"""
    if used_names is None:
        used_names = set()
    
    for layer in layers:
        name = layer.get("name", "").strip()
        
        # 直接使用原始名称，只处理非法字符（保留连字符）
        # CSS 类名允许：字母、数字、连字符、下划线，但不能以数字开头
        import re
        base_name = name if name else "layer"
        # 只移除真正非法的字符（保留连字符和下划线）
        clean_name = re.sub(r'[^\w\-]', '', base_name)
        
        # 确保不以数字开头
        if clean_name and clean_name[0].isdigit():
            clean_name = 'n' + clean_name
        
        if not clean_name:
            clean_name = "layer"
        
        # 处理重名
        class_name = clean_name
        suffix = 2
        while class_name in used_names:
            class_name = "{}_{}".format(clean_name, suffix)
            suffix += 1
        used_names.add(class_name)
        
        layer["bem_class"] = class_name
        layer["class_name"] = class_name  # 同时设置 class_name 供主入口使用
        
        # 递归处理子元素
        children = layer.get("children")
        if children:
            assign_preserve_names(children, used_names)


def _clone_layers_hierarchical(layers):
    """浅拷贝图层树（保留 Path 等对象），避免影响原始数据"""
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


def generate_react_split_component(
    group_layer, canvas_bbox, component_dir, preserve_names=False
):
    """为第一级分组生成独立的 React 组件

    参数:
        group_layer: 分组图层数据（包含 children）
        canvas_bbox: 画布边界框 (x1, y1, x2, y2)
        component_dir: 组件输出目录（如 react-component/components/header/）
        preserve_names: 是否保留原始名称

    返回:
        生成的组件目录路径
    """
    # 克隆图层树，避免污染原始数据
    cloned_group = dict(group_layer)
    children = group_layer.get("children", [])
    if children:
        cloned_group["children"] = _clone_layers_hierarchical(children)

    # 获取分组名称并转换为 PascalCase（用于组件名）
    group_name = group_layer.get("name", "Group")
    component_name = to_pascal_case(group_name)

    # 创建组件目录
    react_dir = Path(component_dir)
    ensure_dir(react_dir)

    # 分配类名
    _apply_react_class_names([cloned_group], component_name, preserve_names)

    # 收集该组件需要的图片
    def collect_images(layer):
        images = []
        if layer.get("image"):
            images.append(layer["image"])
        for child in layer.get("children", []):
            images.extend(collect_images(child))
        return images

    needed_images = collect_images(cloned_group)

    # 计算分组相对于画布的边界框
    x1, y1, x2, y2 = group_layer.get("bbox", canvas_bbox)
    cx1, cy1, cx2, cy2 = canvas_bbox
    group_width = x2 - x1
    group_height = y2 - y1

    # 生成分组的 CSS Modules（相对坐标）
    def generate_group_css_modules(group, group_bbox):
        """为分组生成 CSS Modules，使用相对于分组的坐标"""
        css_lines = []

        def render_layer_css(layer, parent_offset=(0, 0)):
            lines = []
            class_name = ".{}".format(layer.get("class_name") or "layer")

            # 获取相对边界框
            if "relative_bbox" in layer:
                rx1, ry1, rx2, ry2 = layer["relative_bbox"]
            else:
                lx1, ly1, lx2, ly2 = layer.get("bbox", (0, 0, 0, 0))
                gx1, gy1, gx2, gy2 = group_bbox
                rx1, ry1 = lx1 - gx1, ly1 - gy1
                rx2, ry2 = lx2 - gx1, ly2 - gy1

            w = rx2 - rx1
            h = ry2 - ry1

            kind = layer.get("kind", "pixel")
            name = layer.get("name", "")
            layer_children = layer.get("children", [])

            # 生成注释（简单注释，不使用翻译器）
            css_comment = "/* {}: {} */".format(kind, name) if name else ""

            if layer_children:
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
                for child in layer_children:
                    lines.extend(render_layer_css(child))
            else:
                # 叶子节点样式
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
                else:
                    # 文字图层
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

        # 处理分组的根元素
        css_lines.append("/* 组件根容器 - 相对于父容器定位 */")
        css_lines.append(".root {")
        css_lines.append("  position: absolute;")
        css_lines.append("  display: block;")
        css_lines.append("  left: {}px;".format(x1 - cx1))
        css_lines.append("  top: {}px;".format(y1 - cy1))
        css_lines.append("  width: {}px;".format(group_width))
        css_lines.append("  height: {}px;".format(group_height))
        css_lines.append("}")
        css_lines.append("")

        # 处理子图层
        for child in group.get("children", []):
            css_lines.extend(render_layer_css(child))

        return "\n".join(css_lines)

    # 生成分组的 JSX
    def generate_group_jsx(group, comp_name):
        """为分组生成 JSX 代码"""

        def class_attr(class_name):
            return 'className={styles["' + str(class_name) + '"]}'

        def render_layer(layer, indent=8):
            indent_str = " " * indent
            class_name = layer.get("class_name") or "layer"
            children = layer.get("children", [])
            name = layer.get("name", "")
            kind = layer.get("kind", "pixel")

            # 生成注释（简单注释，不使用翻译器）
            jsx_comment = "{{/* {}: {} */}}".format(kind, name) if name else ""

            if children:
                # 分组容器
                lines = []
                if jsx_comment:
                    lines.append("{}{}".format(indent_str, jsx_comment))
                lines.append("{}<div {}>".format(indent_str, class_attr(class_name)))
                for child in children:
                    lines.extend(render_layer(child, indent + 2))
                lines.append("{}</div>".format(indent_str))
                return lines

            if layer.get("image"):
                # 图片图层
                aria = name or "图层"
                lines = []
                if jsx_comment:
                    lines.append("{}{}".format(indent_str, jsx_comment))
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
                lines.append("{}{}".format(indent_str, jsx_comment))
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
            "/**",
            " * {} 组件".format(comp_name),
            " * 自动生成自 PSD 图层组: {}".format(group.get("name", "")),
            " */",
            "const {} = ({{".format(comp_name),
            "  className = '',",
            "  style = {},",
            "  onClick,",
            "  ...rest",
            "}) => {",
            "  return (",
            "    <div",
            '      className={`${styles["root"]} ${className}`}',
            "      style={style}",
            "      onClick={onClick}",
            "      {...rest}",
            "    >",
        ]

        for child in group.get("children", []):
            jsx_lines.extend(render_layer(child, indent=6))

        jsx_lines += [
            "    </div>",
            "  );",
            "};",
            "",
            "export default {};".format(comp_name),
        ]

        return "\n".join(jsx_lines)

    # 始终递归处理子图层，确保子元素被渲染
    jsx_text = generate_group_jsx(cloned_group, component_name)
    css_text = generate_group_css_modules(cloned_group, (x1, y1, x2, y2))

    # 写入文件
    (react_dir / "index.jsx").write_text(jsx_text, encoding="utf-8")
    (react_dir / "index.module.css").write_text(css_text, encoding="utf-8")

    return react_dir, needed_images


def generate_react_main_entry(
    ordered_items, canvas_size, out_dir
):
    """生成 React 主入口组件 App.jsx

    参数:
        ordered_items: 按顺序排列的元素列表 [(layer, index, component_info), ...]
                      component_info 为 None（非分组）或 (component_name, dir_name)
        canvas_size: 画布尺寸 (width, height)
        out_dir: 输出目录（react-component/）

    返回:
        生成的 App.jsx 路径
    """
    react_dir = Path(out_dir)
    ensure_dir(react_dir)

    width, height = canvas_size

    # 生成导入语句
    import_lines = ["import React from 'react';"]
    component_names = []

    for layer, idx, comp_info in ordered_items:
        if comp_info:  # 分组
            component_name, dir_name = comp_info
            import_lines.append(
                'import {} from "./components/{}/index.jsx";'.format(
                    component_name,
                    dir_name
                )
            )
            component_names.append(component_name)

    import_lines.append("import styles from './App.module.css';")
    import_lines.append("")

    # 处理根级非分组图层
    def render_non_group_layer(layer, indent=6):
        """渲染根级非分组图层"""
        indent_str = " " * indent
        class_name = layer.get("class_name") or "layer"
        name = layer.get("name", "")
        kind = layer.get("kind", "pixel")

        # 生成注释（简单注释，不使用翻译器）
        jsx_comment = "{{/* {}: {} */}}".format(kind, name) if name else ""

        if layer.get("image"):
            aria = name or "图层"
            lines = []
            if jsx_comment:
                lines.append("{}{}".format(indent_str, jsx_comment))
            lines.append('{}<div className={{styles["{}"]}} role="img" aria-label="{}" />'.format(
                indent_str,
                class_name,
                html.escape(aria, quote=True),
            ))
            return lines

        # 文字图层
        text_info = layer.get("text_info") or {}
        text = text_info.get("text", "")
        lines = []
        if jsx_comment:
            lines.append("{}{}".format(indent_str, jsx_comment))
        lines.append('{}<div className={{styles["{}"]}}>{{{}}}</div>'.format(
            indent_str,
            class_name,
            json.dumps(text, ensure_ascii=False),
        ))
        return lines

    # 生成 JSX
    jsx_lines = [
        "/**",
        " * App 主入口组件",
        " * 整合所有子组件并管理全局布局",
        " */",
        "const App = () => {",
        "  return (",
        "    <div className={styles['page']}>",
        "      <div className={styles['canvas']}>",
    ]

    # 按原始顺序渲染所有元素
    for layer, idx, comp_info in ordered_items:
        if comp_info is None:
            # 非分组图层
            jsx_lines.extend(render_non_group_layer(layer))
        else:
            # 分组组件
            component_name, dir_name = comp_info
            group_name = layer.get("name", "")
            jsx_comment = "{{/* 分组: {} */}}".format(group_name) if group_name else ""
            if jsx_comment:
                jsx_lines.append("        {}".format(jsx_comment))
            jsx_lines.append("        <{} />".format(component_name))

    jsx_lines += [
        "      </div>",
        "    </div>",
        "  );",
        "};",
        "",
        "export default App;",
    ]

    # 合并所有代码
    app_jsx = "\n".join(import_lines + jsx_lines)

    # 生成 App.module.css
    def generate_app_css():
        """生成 App 组件的 CSS"""
        css_lines = [
            "/* 页面容器 - 居中显示 */",
            ".page { min-height: 100%; display: flex; align-items: flex-start; justify-content: center; padding: 24px; }",
            "",
            "/* 画布容器 - 包含所有组件 */",
            ".canvas {{ position: relative; width: {}px; height: {}px; background: white; }}".format(width, height),
            "",
            "/* 画布内所有直接子元素使用绝对定位 */",
            ".canvas > div { position: absolute; display: block; }",
            "",
        ]

        # 为所有非分组图层生成样式
        for layer, idx, comp_info in ordered_items:
            if comp_info is None:  # 非分组图层
                class_name = ".{}".format(layer.get("class_name") or "layer")
                x1, y1, x2, y2 = layer.get("bbox", (0, 0, 0, 0))
                w = x2 - x1
                h = y2 - y1
                kind = layer.get("kind", "pixel")
                name = layer.get("name", "")

                # 生成注释（简单注释，不使用翻译器）
                css_comment = "/* {}: {} */".format(kind, name) if name else ""

                image_path = layer.get("image")
                if image_path:
                    if css_comment:
                        css_lines.append(css_comment)
                    file_name = Path(image_path).name
                    css_lines.append(
                        "{} {{ ".format(class_name)
                        + "position: absolute; display: block; "
                        + "left: {}px; top: {}px; width: {}px; height: {}px; ".format(x1, y1, w, h)
                        + "background-image: url('./images/{}'); ".format(file_name)
                        + "background-size: 100% 100%; background-repeat: no-repeat; "
                        + "}"
                    )
                else:
                    # 文字图层
                    if css_comment:
                        css_lines.append(css_comment)
                    css_lines.append(
                        "{} {{ ".format(class_name)
                        + "position: absolute; display: block; "
                        + "left: {}px; top: {}px; width: {}px; height: {}px; ".format(x1, y1, w, h)
                        + "white-space: pre-wrap; "
                        + "}"
                    )

        return "\n".join(css_lines)

    app_css = generate_app_css()

    # 写入文件
    (react_dir / "App.jsx").write_text(app_jsx, encoding="utf-8")
    (react_dir / "App.module.css").write_text(app_css, encoding="utf-8")

    return react_dir / "App.jsx"
