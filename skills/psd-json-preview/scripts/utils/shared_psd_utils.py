# -*- coding: utf-8 -*-
"""
PSD 处理共享工具模块
包含所有 PSD 相关脚本通用的工具函数
"""

import json
import re
from pathlib import Path

IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

GENERIC_NAMES = {
    "<图像>", "<编组>", "<路径>", "<形状>",
    "<image>", "<group>", "<path>", "<shape>",
    "<图层>", "<layer>", "<矩形>", "<rectangle>"
}


def load_json(path):
    """加载 JSON 文件"""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_root_bbox(data):
    """查找根节点的边界框"""
    if isinstance(data, dict) and data.get("bbox"):
        return tuple(data["bbox"])
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("bbox"):
                return tuple(item["bbox"])
    return None


def normalize_name(name):
    """
    将不合法的名称转换为合法名称。
    处理规则：
    1. 空格 → 连字符
    2. 特殊字符 (@, #, $, %, &, *, +, =, ?, !, <, >, (, ), [, ], {, }, /, \\, |, :, ;, ', ", `, ~) → 移除或替换
    3. 连续分隔符 → 合并为一个连字符
    4. 数字开头 → 添加 'n' 前缀
    5. 中文字符 → 保留或移除（如果完全由中文组成）
    6. 首尾的连字符 → 移除
    7. 连续连字符 → 合并为一个
    """
    if not name or not isinstance(name, str):
        return "unnamed"
    
    # 1. 将下划线、空格替换为连字符
    normalized = name.replace('_', '-').replace(' ', '-')
    
    # 2. 替换或移除特殊字符
    # 移除这些字符：@ # $ % & * + = ? ! < > ( ) [ ] { } / \ | : ; ' " ` ~ , .
    chars_to_remove = r'@#$%&*+=?!<>()[]{}\/|:;\'"`~,.！。，？：；（）【】「」『』〔〕［］｛｝＠＃＄％＆＊＋＝／｜\\'
    for char in chars_to_remove:
        normalized = normalized.replace(char, '')
    
    # 3. 处理中文字符
    # 如果名称包含中文，替换为非中文字符的逻辑比较复杂，先保留
    # 移除连续连字符
    while '--' in normalized:
        normalized = normalized.replace('--', '-')
    
    # 4. 移除首尾的连字符
    normalized = normalized.strip('-')
    
    # 5. 如果空字符串，使用 "unnamed"
    if not normalized:
        return "unnamed"
    
    # 6. 如果首字符是数字，添加 'n' 前缀
    if normalized[0].isdigit():
        normalized = 'n' + normalized
    
    # 7. 如果只剩数字，添加前缀
    if normalized.isdigit():
        normalized = 'num-' + normalized
    
    # 8. 检查是否还有非法字符
    # 只保留 ASCII 字母、数字和连字符（移除中文和其他 Unicode 字符）
    result = []
    for char in normalized:
        if ('a' <= char <= 'z') or ('A' <= char <= 'Z') or ('0' <= char <= '9') or char == '-':
            result.append(char)
    normalized = ''.join(result)
    
    # 9. 再次清理首尾连字符和连续连字符
    while '--' in normalized:
        normalized = normalized.replace('--', '-')
    normalized = normalized.strip('-')
    
    # 10. 最终检查
    if not normalized:
        return "unnamed"
    
    if normalized[0].isdigit():
        normalized = 'n' + normalized
    
    return normalized


def sanitize_class_name(name):
    """Sanitize class name to ASCII letters/numbers/underscore only, ensure starts with letter or underscore"""
    if not name:
        return ""
    sanitized = []
    for ch in name:
        if "A" <= ch <= "Z" or "a" <= ch <= "z" or "0" <= ch <= "9" or ch == "_":
            sanitized.append(ch)
        elif ch == "-":
            sanitized.append("_")
        else:
            sanitized.append("_")
    collapsed = "".join(sanitized)
    while "__" in collapsed:
        collapsed = collapsed.replace("__", "_")
    collapsed = collapsed.strip("_")
    # Ensure class name doesn't start with a number
    if collapsed and collapsed[0].isdigit():
        collapsed = "n" + collapsed
    return collapsed


def has_non_ascii(name):
    return any(ord(ch) > 127 for ch in name)


def is_generic_name(name):
    """检查是否为通用名称"""
    return name.strip() in GENERIC_NAMES


def find_image(images_dir, layer_or_name):
    """
    根据图层信息查找对应的切片图片。
    优先使用 name 进行匹配（因为 psd-slicer 导出的图片使用 name 字段命名）。
    
    Args:
        images_dir: 图片目录路径
        layer_or_name: 图层字典或名称字符串
    
    Returns:
        Path: 找到的图片路径，或 None
    """
    # 提取名称列表（优先 name，因为导出的图片使用 name 命名）
    names_to_try = []
    
    if isinstance(layer_or_name, dict):
        # 如果是图层字典，优先使用 name（与 psd-slicer 导出逻辑一致）
        if layer_or_name.get("name"):
            names_to_try.append(layer_or_name["name"])
        if layer_or_name.get("originalName"):
            names_to_try.append(layer_or_name["originalName"])
    else:
        # 如果是字符串，直接使用
        names_to_try.append(layer_or_name)
    
    # 如果没有名称可尝试，返回 None
    if not names_to_try:
        return None
    
    # 生成所有可能的文件名变体（保持顺序，确保 name 在 originalName 之前）
    possible_names = []
    for name in names_to_try:
        if name:
            norm = normalize_name(name)
            norm_lower = normalize_name(name.lower())
            if norm not in possible_names:
                possible_names.append(norm)
            if norm_lower not in possible_names:
                possible_names.append(norm_lower)
    
    # 添加可能的序号后缀（处理 slicer 添加的序号）
    extended_names = list(possible_names)
    for suffix in ["-1", "-2", "-3", "-001", "-002", "-003"]:
        for name in possible_names:
            if not name.endswith(suffix):
                extended_names.append(name + suffix)
    
    # 尝试查找图片
    for ext in IMAGE_EXTS:
        # 先尝试直接匹配
        for base_name in extended_names:
            candidate = images_dir / "{}{}".format(base_name, ext)
            if candidate.exists():
                return candidate
        
        # 再尝试 glob 匹配
        for img_file in images_dir.glob("*{}".format(ext)):
            file_stem = img_file.stem.lower()
            for base_name in extended_names:
                if file_stem == base_name.lower():
                    return img_file
    
    return None


def to_kebab_case(name):
    """将 PascalCase 转换为 kebab-case"""
    return re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()


def to_camel_case(name):
    """将连字符命名转换为驼峰命名"""
    parts = name.split("-")
    if not parts:
        return name
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def assign_bem_class_names(layers, component_name, prefix=""):
    """
    为图层分配 BEM 风格的类名
    component_name: 组件名称（如 RsList）
    prefix: 父级前缀（递归时使用）
    """
    # 将 PascalCase 转换为 kebab-case
    component_slug = to_kebab_case(component_name)

    for layer in layers:
        name = layer.get("name", "").strip()
        kind = layer.get("kind", "pixel")

        # 规范化名称
        safe_name = sanitize_class_name(normalize_name(name)) if name else "layer"

        # 生成 BEM 类名
        if prefix:
            bem_class = "{}__{}-{}".format(component_slug, prefix, safe_name)
        else:
            bem_class = "{}__{}".format(component_slug, safe_name)

        layer["bem_class"] = bem_class

        # 递归处理子元素
        children = layer.get("children", [])
        if children:
            new_prefix = "{}-{}".format(prefix, safe_name) if prefix else safe_name
            assign_bem_class_names(children, component_name, new_prefix)


def generate_random_class_name(used_names, prefix="layer"):
    """生成唯一的随机类名"""
    import random
    import string

    while True:
        # 生成 6 位随机字母数字组合
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        candidate = "{}_{}".format(prefix, random_suffix)
        if candidate not in used_names:
            return candidate


def assign_preserve_names(layers, used_names=None):
    """
    保留PSD原始图层名作为类名，确保唯一性
    如果sanitize后为空，则生成随机合法类名
    """
    if used_names is None:
        used_names = set()

    for layer in layers:
        name = layer.get("name", "").strip()

        # 直接使用原始名称，但进行安全处理
        safe_name = sanitize_class_name(name) if name else ""

        if not safe_name:
            # 如果sanitize后为空（例如纯中文），生成随机类名
            base_name = generate_random_class_name(used_names, "layer")
        else:
            # 确保类名唯一
            base_name = safe_name
            suffix = 2
            while base_name in used_names:
                base_name = "{}_{}".format(safe_name, suffix)
                suffix += 1

        used_names.add(base_name)
        layer["bem_class"] = base_name

        # 递归处理子元素
        children = layer.get("children", [])
        if children:
            assign_preserve_names(children, used_names)


def collect_layers_hierarchical(
    node,
    images_dir,
    include_text,
    parent_bbox=None,
    used_class_names=None
):
    """
    递归收集图层，保留分组嵌套结构
    返回的每个节点包含：
    - name, kind, bbox, class_name
    - image (如果是图片图层)
    - children (如果是分组)
    - relative_bbox (相对于父容器的坐标)
    """
    if used_class_names is None:
        used_class_names = set()

    result = []

    if isinstance(node, list):
        for item in node:
            result.extend(
                collect_layers_hierarchical(item, images_dir, include_text, parent_bbox, used_class_names)
            )
        return result

    if not isinstance(node, dict):
        return result

    if not node.get("visible", True):
        return result

    bbox = node.get("bbox")
    if not bbox or len(bbox) != 4:
        return result

    name = node.get("name", "").strip()
    original_name = node.get("originalName", name)
    layout_tag = node.get("layoutTag")
    kind = node.get("kind", "group")
    children_nodes = node.get("children", [])

    # 计算相对坐标
    x1, y1, x2, y2 = bbox
    if parent_bbox:
        px1, py1, _, _ = parent_bbox
        relative_bbox = (x1 - px1, y1 - py1, x2 - px1, y2 - py1)
    else:
        relative_bbox = bbox

    # 直接使用 JSON 中的 name 字段作为 class name
    # psd-layer-reader 已经对 name 字段做了合法性校验
    # 只做空值检查和重名处理
    base_name = name if name else "layer"
    class_name = base_name

    # 处理重名情况，添加数字后缀
    suffix = 2
    while class_name in used_class_names:
        class_name = "{}_{}".format(base_name, suffix)
        suffix += 1
    used_class_names.add(class_name)

    layer_data = {
        "name": name,
        "originalName": original_name,
        "layoutTag": layout_tag,
        "kind": kind,
        "bbox": bbox,
        "relative_bbox": relative_bbox,
        "class_name": class_name,
    }

    # 处理分组
    # 处理分组和画板
    if kind in ("group", "artboard") and children_nodes:
        children = []
        for child in children_nodes:
            children.extend(
                collect_layers_hierarchical(child, images_dir, include_text, bbox, used_class_names)
            )

        if children:
            layer_data["children"] = children
            # 分组本身如果有对应图片也添加
            img_path = find_image(images_dir, node) if name and not is_generic_name(name) else None
            if img_path:
                layer_data["image"] = img_path
            result.append(layer_data)
        else:
            # 没有子元素的分组，尝试渲染为图片
            img_path = find_image(images_dir, node) if name and not is_generic_name(name) else None
            if img_path:
                layer_data["image"] = img_path
                result.append(layer_data)
    else:
        # 叶子节点
        img_path = find_image(images_dir, node) if name and not is_generic_name(name) else None
        if img_path:
            layer_data["image"] = img_path
            result.append(layer_data)
        elif include_text and kind == "type":
            text_info = node.get("textInfo")
            layer_data["text_info"] = text_info
            result.append(layer_data)

    return result


def collect_all_images_hierarchical(layers, result=None):
    """递归收集所有图片路径"""
    if result is None:
        result = []

    for layer in layers:
        if layer.get("image"):
            result.append(Path(layer["image"]))
        if layer.get("children"):
            collect_all_images_hierarchical(layer["children"], result)

    return result


def ensure_dir(path):
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)

def _compute_margins_for_flow(flow_children, parent_layout):
    prev_bbox = None
    for c in flow_children:
        rx1, ry1, rx2, ry2 = c["relative_bbox"]
        
        if "layout_css_rules" not in c:
            c["layout_css_rules"] = {}
            
        c["layout_css_rules"]["position"] = "relative"
        
        if parent_layout == "flow-y":
            if prev_bbox:
                margin_top = ry1 - prev_bbox[3]
            else:
                margin_top = ry1
            
            c["layout_css_rules"]["margin-top"] = "{}px".format(margin_top)
            if rx1 != 0:
                c["layout_css_rules"]["margin-left"] = "{}px".format(rx1)
            
        elif parent_layout == "flow-x":
            if prev_bbox:
                margin_left = rx1 - prev_bbox[2]
            else:
                margin_left = rx1
                
            c["layout_css_rules"]["margin-left"] = "{}px".format(margin_left)
            if ry1 != 0:
                c["layout_css_rules"]["margin-top"] = "{}px".format(ry1)
            
        prev_bbox = (rx1, ry1, rx2, ry2)

def process_layout_rules(layers, root_bbox=None):
    """预计算图层树的 CSS 布局规则，并在需要时由于文档流将子元素排序。"""
    if root_bbox is None:
        root_bbox = find_root_bbox(layers)
        
    canvas_width = 1920
    if root_bbox and len(root_bbox) == 4:
        canvas_width = root_bbox[2] - root_bbox[0]
        
    for layer in layers:
        # Default positioning if not already processed by a parent flow
        if "layout_css_rules" not in layer:
            layer["layout_css_rules"] = {}
            rx1, ry1, _, _ = layer["relative_bbox"]
            tag = layer.get("layoutTag")
            if tag == "fixed":
                layer["layout_css_rules"]["position"] = "fixed"
                layer["layout_css_rules"]["z-index"] = "100"
                
                # --- Fixed 元素的视口响应式定位逻辑 ---
                # 1. 垂直方向:
                # 如果元素位置在设计稿第一屏以内 (如 < 900px)，按原样顶端定位；
                # 如果超出了第一屏，说明设计师可能只是将其与第二屏内容就近对比放置，此时真实意图往往是“垂直悬浮居中”。
                if ry1 > 900:
                    layer["layout_css_rules"]["top"] = "50%"
                    layer["layout_css_rules"]["transform"] = "translateY(-50%)"
                else:
                    layer["layout_css_rules"]["top"] = "{}px".format(ry1)
                
                # 2. 水平方向:
                # 为了防止随浏览器窗口缩放时 fixed 元素相对于内容区跑偏，通常让它相对于屏幕水平中线进行偏移。
                center_x = canvas_width / 2
                offset_x = rx1 - center_x
                layer["layout_css_rules"]["left"] = "50%"
                layer["layout_css_rules"]["margin-left"] = "{}px".format(int(offset_x))
            else:
                layer["layout_css_rules"]["position"] = "absolute"
                layer["layout_css_rules"]["left"] = "{}px".format(rx1)
                layer["layout_css_rules"]["top"] = "{}px".format(ry1)
        
        tag = layer.get("layoutTag")
        rx1, ry1, rx2, ry2 = layer["relative_bbox"]
        
        # sizing and display
        layer["layout_css_rules"]["width"] = "{}px".format(rx2 - rx1)
        layer["layout_css_rules"]["height"] = "{}px".format(ry2 - ry1)
        
        if tag in ("flow-y", "flow-x") and layer.get("children"):
            layer["layout_css_rules"]["display"] = "flex"
            layer["layout_css_rules"]["flex-direction"] = "column" if tag == "flow-y" else "row"
        else:
            layer["layout_css_rules"]["display"] = "block"
            
        children = layer.get("children", [])
        if not children:
            continue
            
        if tag in ("flow-y", "flow-x"):
            flow_children = [c for c in children if c.get("layoutTag") not in ("abs", "fixed")]
            abs_children = [c for c in children if c.get("layoutTag") in ("abs", "fixed")]
            
            if tag == "flow-y":
                flow_children.sort(key=lambda x: x["relative_bbox"][1])
            else:
                flow_children.sort(key=lambda x: x["relative_bbox"][0])
                
            _compute_margins_for_flow(flow_children, tag)
            layer["children"] = flow_children + abs_children
            
        process_layout_rules(children, root_bbox)