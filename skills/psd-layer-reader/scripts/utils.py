# -*- coding: utf-8 -*-
import re

# 预编译正则表达式
_VALID_NAME_RE = re.compile(r'^[a-zA-Z_](?:[a-zA-Z0-9_]|(?<!-)-(?!-))*[a-zA-Z0-9_]$|^[a-zA-Z_]$')


def unwrap_value(value):
    """解包 psd-tools 的特殊值对象。"""
    if hasattr(value, "value"):
        return value.value
    return value


def rgba_to_array(color_obj):
    """将颜色对象转换为 [r, g, b, a] 数组（0-255 整数）。"""
    try:
        if color_obj is None:
            return None

        color_obj = unwrap_value(color_obj)

        # 字典/类字典结构
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
            # 对象属性
            r = getattr(color_obj, "R", getattr(color_obj, "r", None))
            g = getattr(color_obj, "G", getattr(color_obj, "g", None))
            b = getattr(color_obj, "B", getattr(color_obj, "b", None))
            a = getattr(color_obj, "A", getattr(color_obj, "a", 1))
            if r is None or g is None or b is None:
                return None

        # 解包值
        r, g, b, a = unwrap_value(r), unwrap_value(g), unwrap_value(b), unwrap_value(a)

        # 0-1 范围自动缩放到 0-255
        r = int(r * 255) if 0 <= r <= 1 else int(r)
        g = int(g * 255) if 0 <= g <= 1 else int(g)
        b = int(b * 255) if 0 <= b <= 1 else int(b)
        a = int(a * 255) if 0 <= a <= 1 else int(a) if a is not None else 255

        return [r, g, b, a]
    except Exception:
        return None


def is_valid_name(name):
    """
    检查名称是否合法。
    规则：以字母/下划线开头，可包含字母、数字、下划线、连字符，
    不能以连字符结尾，不能包含连续连字符。
    """
    if not name or not isinstance(name, str):
        return False
    return bool(_VALID_NAME_RE.match(name))


def normalize_name(name):
    """规范化名称：空格/下划线转连字符，数字开头加前缀。"""
    if not name:
        return ''
    normalized = name.replace('_', '-').replace(' ', '-')
    # 合并连续连字符
    while '--' in normalized:
        normalized = normalized.replace('--', '-')
    normalized = normalized.strip('-')
    if normalized and normalized[0].isdigit():
        normalized = 'n' + normalized
    return normalized


def make_name_unique(name, used_names, layer_id=None):
    """确保名称唯一，使用 layer_id 后缀消歧。"""
    if name not in used_names:
        used_names.add(name)
        return name

    # 使用 layer_id 后缀消歧（PSD 内 layer_id 唯一）
    if layer_id is not None:
        new_name = "{}-{}".format(name, layer_id)
        used_names.add(new_name)
        return new_name

    # 无 layer_id 时直接返回原名（理论上不应发生）
    used_names.add(name)
    return name


def sanitize_name(name, used_names, kind='layer', layer_id=None):
    """
    规范化图层名称：
    1. 合法名称 → 直接确保唯一性
    2. 可规范化 → 规范化后确保唯一性
    3. 无法规范化 → 用 kind-layerId 生成名称
    """
    name_stripped = name.strip() if name else ''

    # 已合法
    if name_stripped and is_valid_name(name_stripped):
        return make_name_unique(name_stripped, used_names, layer_id)

    # 尝试规范化
    normalized = normalize_name(name_stripped)
    if normalized and is_valid_name(normalized):
        return make_name_unique(normalized, used_names, layer_id)

    # 无法规范化，用 kind + layer_id 生成
    prefix = 'group' if kind == 'group' else 'layer'
    fallback = "{}-{}".format(prefix, layer_id) if layer_id is not None else prefix
    return make_name_unique(fallback, used_names, layer_id)
