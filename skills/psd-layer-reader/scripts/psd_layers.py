#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
import sys
import traceback
from psd_tools import PSDImage

# 命名保护常量
MAX_NAME_ATTEMPTS = 10000  # 最大命名尝试次数
MAX_COUNTER = 9999  # 序号上限

# 预编译正则表达式以提高性能
_NAME_SUFFIX_PATTERN = re.compile(r'^(.*?)-(\d+)$')


def unwrap_value(value):
    if hasattr(value, "value"):
        return value.value
    return value


def rgba_to_array(color_obj):
    """Convert color object to [r, g, b, a] array with 0-255 ints."""
    try:
        if color_obj is None:
            return None

        color_obj = unwrap_value(color_obj)

        # Handle dict-like structures
        if isinstance(color_obj, dict) or hasattr(color_obj, 'get'):
            if "Values" in color_obj:
                values = color_obj["Values"]
                if hasattr(values, '__len__') and len(values) >= 3:
                    if len(values) == 4:
                        a, r, g, b = values
                    elif len(values) == 3:
                        r, g, b = values
                        a = 1
                    else:
                        return None
                else:
                    return None
            else:
                r = color_obj.get("R", color_obj.get("r"))
                g = color_obj.get("G", color_obj.get("g"))
                b = color_obj.get("B", color_obj.get("b"))
                a = color_obj.get("A", color_obj.get("a", 1))
                if r is None or g is None or b is None:
                    return None
        else:
            # Handle objects with attributes
            r = getattr(color_obj, "R", getattr(color_obj, "r", None))
            g = getattr(color_obj, "G", getattr(color_obj, "g", None))
            b = getattr(color_obj, "B", getattr(color_obj, "b", None))
            a = getattr(color_obj, "A", getattr(color_obj, "a", 1))
            if r is None or g is None or b is None:
                return None
        
        # Unwrap values
        r = unwrap_value(r)
        g = unwrap_value(g)
        b = unwrap_value(b)
        a = unwrap_value(a)

        # Scale 0-1 to 0-255 if needed
        r = int(r * 255) if 0 <= r <= 1 else int(r)
        g = int(g * 255) if 0 <= g <= 1 else int(g)
        b = int(b * 255) if 0 <= b <= 1 else int(b)
        a = int(a * 255) if 0 <= a <= 1 else int(a) if a is not None else 255

        return [r, g, b, a]
    except Exception:
        return None


def extract_text_info(layer):
    """Extract text information from text layers (kind == 'type')."""
    if layer.kind != "type":
        return None

    try:
        text = layer.text or ""
        text = text.replace("\r", "\n")

        text_info = {"text": text}

        text_type = getattr(layer, "text_type", None)
        if text_type is not None:
            text_info["textType"] = str(text_type)

        engine_dict = layer.engine_dict if hasattr(layer, "engine_dict") else None
        resource_dict = layer.resource_dict if hasattr(layer, "resource_dict") else None
        font_set = resource_dict.get("FontSet", []) if hasattr(resource_dict, 'get') else []
        # Some PSDs store fonts under engine_dict.DocumentResources.
        if not font_set and hasattr(engine_dict, 'get'):
            doc_res = engine_dict.get("DocumentResources")
            if hasattr(doc_res, 'get') and hasattr(doc_res.get("FontSet"), '__len__'):
                font_set = doc_res.get("FontSet") or []

        # Extract runs (style segments)
        runs = []
        run_length_array = []
        run_array = []
        if isinstance(engine_dict, dict) or hasattr(engine_dict, 'get'):
            style_run = engine_dict.get("StyleRun", {}) if engine_dict else {}
            if hasattr(style_run, 'get'):
                rla = style_run.get("RunLengthArray")
                ra = style_run.get("RunArray")
                if rla is not None:
                    run_length_array = rla
                if ra is not None:
                    run_array = ra

        if run_array and run_length_array:
            run_text = text
            if hasattr(engine_dict, 'get'):
                editor = engine_dict.get("Editor", {})
                if hasattr(editor, 'get') and "Text" in editor:
                    run_text = unwrap_value(editor.get("Text", text)) or text
                    run_text = run_text.replace("\r", "\n")

            text_index = 0
            for length, run_item in zip(run_length_array, run_array):
                run_data = {}
                length = int(length)
                run_data["text"] = run_text[text_index:text_index + length]
                text_index += length

                style_sheet_data = None
                if hasattr(run_item, 'get'):
                    if "StyleSheet" in run_item and hasattr(run_item["StyleSheet"], 'get'):
                        style_sheet_data = run_item["StyleSheet"].get("StyleSheetData")
                    if style_sheet_data is None and "StyleSheetData" in run_item:
                        style_sheet_data = run_item.get("StyleSheetData")

                if hasattr(style_sheet_data, 'get'):
                    font_idx = style_sheet_data.get("Font")
                    if isinstance(font_idx, int) and 0 <= font_idx < len(font_set):
                        font_entry = font_set[font_idx]
                        if hasattr(font_entry, 'get'):
                            run_data["fontName"] = font_entry.get("Name")

                    if "FontSize" in style_sheet_data:
                        font_size_val = style_sheet_data.get("FontSize")
                        run_data["fontSize"] = unwrap_value(font_size_val)

                    color_source = (
                        style_sheet_data.get("FgColor")
                        or style_sheet_data.get("FillColor")
                        or style_sheet_data.get("Color")
                    )
                    color_array = rgba_to_array(color_source)
                    if color_array:
                        run_data["color"] = color_array

                    alignment = style_sheet_data.get("Justification")
                    if alignment is None:
                        alignment = style_sheet_data.get("Alignment")
                    if alignment is not None:
                        run_data["alignment"] = unwrap_value(alignment)

                    for key in ["Leading", "Tracking", "BaselineShift", "AutoLeading"]:
                        if key in style_sheet_data:
                            val = style_sheet_data.get(key)
                            run_data[key[0].lower() + key[1:]] = unwrap_value(val)

                runs.append(run_data)

        # Fallback extraction when StyleRun is missing/empty.
        # Try paragraph settings and document defaults, then synthesize a single run
        # so existing "first_run" mapping continues to work.
        if not runs and isinstance(engine_dict, dict):
            STYLE_KEYS = {
                "Font",
                "FontSize",
                "FgColor",
                "FillColor",
                "Color",
                "Leading",
                "AutoLeading",
                "Tracking",
                "Justification",
                "Alignment",
            }

            def _as_number(value):
                value = unwrap_value(value)
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    try:
                        return float(value)
                    except Exception:
                        return None
                return None

            def _find_first_style_dict(node, max_depth=7):
                """Depth-limited search for a dict containing known style keys."""
                if max_depth <= 0:
                    return None
                node = unwrap_value(node)
                if isinstance(node, dict):
                    hits = sum(1 for k in STYLE_KEYS if k in node)
                    if hits >= 2:
                        return node
                    for v in node.values():
                        found = _find_first_style_dict(v, max_depth=max_depth - 1)
                        if found is not None:
                            return found
                elif isinstance(node, list):
                    for item in node:
                        found = _find_first_style_dict(item, max_depth=max_depth - 1)
                        if found is not None:
                            return found
                return None

            def _extract_defaults_from_style_dict(style_dict):
                """Extract a minimal run style dict from a style-like dict."""
                run_data = {}

                # fontSize
                font_size = None
                if isinstance(style_dict, dict):
                    if "FontSize" in style_dict:
                        font_size = _as_number(style_dict.get("FontSize"))
                    elif "fontSize" in style_dict:
                        font_size = _as_number(style_dict.get("fontSize"))
                if font_size is not None:
                    run_data["fontSize"] = font_size

                # fontName
                font_idx = None
                if isinstance(style_dict, dict):
                    if "Font" in style_dict:
                        v = _as_number(style_dict.get("Font"))
                        if v is not None:
                            font_idx = int(v)

                font_name = None
                if isinstance(font_idx, int) and 0 <= font_idx < len(font_set):
                    font_entry = font_set[font_idx]
                    if isinstance(font_entry, dict):
                        font_name = font_entry.get("Name")
                if not font_name and font_set:
                    font_entry0 = font_set[0]
                    if isinstance(font_entry0, dict):
                        font_name = font_entry0.get("Name")
                if font_name:
                    run_data["fontName"] = font_name

                # color
                if isinstance(style_dict, dict):
                    color_source = (
                        style_dict.get("FgColor")
                        or style_dict.get("FillColor")
                        or style_dict.get("Color")
                    )
                    color_array = rgba_to_array(color_source)
                    if color_array:
                        run_data["color"] = color_array

                # alignment (Justification)
                if isinstance(style_dict, dict):
                    alignment = style_dict.get("Justification")
                    if alignment is None:
                        alignment = style_dict.get("Alignment")
                    if alignment is not None:
                        run_data["alignment"] = unwrap_value(alignment)

                # leading / autoLeading (percent -> px)
                leading_val = None
                auto_leading_val = None
                if isinstance(style_dict, dict):
                    if "Leading" in style_dict:
                        leading_val = _as_number(style_dict.get("Leading"))
                    if "AutoLeading" in style_dict:
                        auto_leading_val = unwrap_value(style_dict.get("AutoLeading"))
                    elif "autoLeading" in style_dict:
                        auto_leading_val = unwrap_value(style_dict.get("autoLeading"))

                if leading_val is not None:
                    run_data["leading"] = leading_val

                # If autoLeading is a percent/multiplier and leading is missing or zero, compute leading.
                auto_percent = None
                if isinstance(auto_leading_val, (int, float)):
                    v = float(auto_leading_val)
                    # Heuristic: <=10 is likely multiplier (e.g., 1.2), otherwise percent (e.g., 120)
                    auto_percent = v * 100 if 0 < v <= 10 else v
                elif isinstance(auto_leading_val, str):
                    v = _as_number(auto_leading_val)
                    if v is not None:
                        auto_percent = v * 100 if 0 < v <= 10 else v

                if auto_percent is not None:
                    run_data["autoLeading"] = auto_percent
                    if (leading_val is None or leading_val == 0) and font_size is not None:
                        run_data["leading"] = font_size * (auto_percent / 100.0)

                # tracking (1/1000 em -> px)
                tracking_raw = None
                if isinstance(style_dict, dict):
                    if "Tracking" in style_dict:
                        tracking_raw = _as_number(style_dict.get("Tracking"))
                    elif "tracking" in style_dict:
                        tracking_raw = _as_number(style_dict.get("tracking"))

                if tracking_raw is not None:
                    if font_size is not None:
                        run_data["tracking"] = font_size * (tracking_raw / 1000.0)
                    else:
                        # If fontSize is missing, avoid outputting ambiguous units.
                        # (Callers can still use trackingRaw.)
                        pass

                return run_data

            # Candidate sources in priority order.
            candidates = []
            paragraph_run = engine_dict.get("ParagraphRun")
            if isinstance(paragraph_run, dict):
                pr_array = paragraph_run.get("RunArray")
                if isinstance(pr_array, list) and pr_array:
                    candidates.append(pr_array[0])

            editor = engine_dict.get("Editor")
            if isinstance(editor, dict):
                editor_text = editor.get("Text")
                # Some PSDs have structured Editor.Text instead of a plain string.
                if isinstance(editor_text, dict):
                    psr = editor_text.get("ParagraphStyleRange")
                    if isinstance(psr, list) and psr:
                        candidates.append(psr[0])

            doc_res = engine_dict.get("DocumentResources")
            if isinstance(doc_res, dict):
                candidates.append(doc_res)

            for cand in candidates:
                cand = unwrap_value(cand)
                style_dict = None
                if isinstance(cand, dict):
                    # Common nesting patterns.
                    ps = cand.get("ParagraphSheet")
                    if isinstance(ps, dict):
                        style_dict = (
                            ps.get("Properties")
                            or ps.get("ParagraphSheetData")
                            or ps.get("StyleSheetData")
                        )
                    if style_dict is None:
                        style_dict = (
                            cand.get("ParagraphSheetData")
                            or cand.get("Properties")
                            or cand.get("StyleSheetData")
                        )
                    if style_dict is None and isinstance(cand.get("StyleSheet"), dict):
                        style_dict = cand.get("StyleSheet", {}).get("StyleSheetData")

                if style_dict is None:
                    style_dict = _find_first_style_dict(cand)

                style_dict = unwrap_value(style_dict)
                if isinstance(style_dict, dict):
                    run_defaults = _extract_defaults_from_style_dict(style_dict)
                    if run_defaults:
                        runs = [{"text": text, **run_defaults}]
                        break

        if runs:
            text_info["runs"] = runs
            first_run = runs[0]
            for key in [
                "fontName",
                "fontSize",
                "color",
                "alignment",
                "leading",
                "tracking",
                "baselineShift",
                "autoLeading",
            ]:
                if key in first_run:
                    text_info[key] = first_run[key]

        return text_info if len(text_info) > 1 else None
    except Exception:
        return None


def node_from_layer_with_sanitize(layer, used_names):
    """
    处理图层节点，并规范化名称。
    - name: 规范化后的合法名称
    - originalName: 保留原始名称
    - layerId: 图层的唯一标识（从 PSD 中读取）
    - used_names: 用于保证名称唯一性的集合
    """
    # 异常捕获：处理 PSD 损坏时 layer.name 和 layer.bbox 可能为 None
    try:
        layer_name = layer.name if hasattr(layer, 'name') and layer.name else "unnamed"
        bbox = layer.bbox if hasattr(layer, 'bbox') else None
        # 新增：获取 layer_id（PSD 内部唯一标识）
        layer_id = layer.layer_id if hasattr(layer, 'layer_id') else None
    except Exception:
        layer_name = "unnamed"
        bbox = None
        layer_id = None

    # 规范化名称
    layer_kind = layer.kind if hasattr(layer, 'kind') and layer.kind == 'group' else 'layer'
    sanitized_name = sanitize_name(layer_name, used_names, layer_kind)
    used_names.add(sanitized_name)

    node = {
        "name": sanitized_name,
        "originalName": layer_name,
        "layerId": layer_id,
        "kind": layer.kind if hasattr(layer, 'kind') else "unknown",
        "visible": bool(layer.visible) if hasattr(layer, 'visible') else True,
        "bbox": [bbox[0], bbox[1], bbox[2], bbox[3]] if bbox is not None else None,
        "children": [],
    }

    # 处理子图层（图层组）
    if layer.is_group() if hasattr(layer, 'is_group') else False:
        try:
            node["children"] = [node_from_layer_with_sanitize(child, used_names) for child in layer]
        except Exception:
            node["children"] = []

    # 添加文本层信息
    if layer.kind == 'type' if hasattr(layer, 'kind') else False:
        try:
            text_info = extract_text_info(layer)
            if text_info:
                node['textInfo'] = text_info
        except Exception:
            pass

    return node


def node_from_layer(layer, used_names=None):
    """
    处理 PSD 图层，返回节点信息。
    自动规范化图层名称为合法格式。
    
    Args:
        layer: PSD 图层对象
        used_names: 已使用的名称集合（用于全局唯一性检查）
                   如果为 None，则创建新的集合（向后兼容）
    
    Returns:
        dict: 包含图层信息的字典节点
    """
    if used_names is None:
        used_names = set()
    return node_from_layer_with_sanitize(layer, used_names)


def is_valid_name(name):
    """
    检查名称是否合法。
    合法规则：
    - 必须以字母或下划线开头
    - 可以包含字母、数字、下划线、连字符（-）
    - 不能以连字符结尾
    - 不能包含连续连字符
    """
    if not name or not isinstance(name, str):
        return False
    if not name[0].isalpha() and name[0] != '_':
        return False
    if name.endswith('-'):
        return False
    import re
    # 检查是否有连续连字符
    if '--' in name:
        return False
    # 允许字母、数字、下划线、连字符，但不能以连字符结尾
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*[a-zA-Z0-9_]$', name)) or bool(re.match(r'^[a-zA-Z_]$', name))


def generate_random_name(prefix, used_names):
    """生成随机名称，确保不与已使用名称重复。"""
    import random
    import string
    import uuid
    suffix_len = 6
    chars = string.ascii_lowercase + string.digits
    attempts = 0
    max_attempts = 1000
    
    while attempts < max_attempts:
        suffix = ''.join(random.choices(chars, k=suffix_len))
        new_name = "{}-{}".format(prefix, suffix)
        if new_name not in used_names:
            used_names.add(new_name)
            return new_name
        attempts += 1
    
    # 兜底：使用 UUID
    new_name = "{}-{}".format(prefix, str(uuid.uuid4())[:8])
    used_names.add(new_name)
    return new_name


def normalize_name_simple(name):
    """简化规范化：只处理空格和下划线"""
    if not name:
        return ''
    # 空格和下划线转连字符
    normalized = name.replace('_', '-').replace(' ', '-')
    # 合并连续连字符
    while '--' in normalized:
        normalized = normalized.replace('--', '-')
    # 移除首尾连字符
    normalized = normalized.strip('-')
    # 数字开头添加前缀
    if normalized and normalized[0].isdigit():
        normalized = 'n' + normalized
    return normalized


def make_name_unique(name, used_names):
    """确保名称唯一，使用随机值避免冲突。"""
    if name not in used_names:
        used_names.add(name)
        return name
    
    base = name
    
    # 尝试提取已有后缀（如 name-1 中的 name）
    match = _NAME_SUFFIX_PATTERN.match(name)
    if match:
        base = match.group(1)
    
    # 使用随机值生成唯一名称
    return generate_random_name(base, used_names)


def sanitize_name(name, used_names, kind='layer'):
    """
    简化命名逻辑：
    1. 检查名称是否已经是合法的
    2. 如果合法，确保唯一性后返回
    3. 如果不合法，根据 kind 生成随机名称
    """
    name_stripped = name.strip() if name else ''
    
    # 检查是否已经是合法名称
    if name_stripped and is_valid_name(name_stripped):
        return make_name_unique(name_stripped, used_names)
    
    # 尝试规范化（处理空格、下划线等简单情况）
    normalized = normalize_name_simple(name_stripped)
    if normalized and is_valid_name(normalized):
        return make_name_unique(normalized, used_names)
    
    # 不合法或为空，生成随机名
    prefix = 'group' if kind == 'group' else 'layer'
    return generate_random_name(prefix, used_names)


def match_name(name, target, mode):
    if mode == "exact":
        return name == target
    if mode == "contains":
        return target in name
    return False


def filter_tree(node, target, mode):
    matched = match_name(node["name"], target, mode)
    if matched:
        return node
    filtered_children = [
        child_filtered
        for child in node["children"]
        for child_filtered in [filter_tree(child, target, mode)]
        if child_filtered is not None
    ]
    if filtered_children:
        return {**node, "children": filtered_children}
    return None


def main():
    parser = argparse.ArgumentParser(description="Export PSD layer tree to JSON.")
    parser.add_argument("--psd", help="Path to .psd file")
    parser.add_argument("--output", "-o", default="psd_layers.json", help="Output JSON path")
    parser.add_argument("--name", help="Filter by layer name")
    parser.add_argument("--match", choices=["exact", "contains"], default="exact", help="Match mode")
    args = parser.parse_args()

    psd = PSDImage.open(args.psd)
    
    # Bug 修复：创建全局共享的命名集合
    # 之前每个顶层图层有自己的命名空间，导致跨顶层图层重名未检测
    global_used_names = set()
    tree = [node_from_layer(layer, global_used_names) for layer in psd]

    if args.name:
        filtered = []
        for node in tree:
            filtered_node = filter_tree(node, args.name, args.match)
            if filtered_node is not None:
                filtered.append(filtered_node)
        tree = filtered

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
