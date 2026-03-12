#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命名相关的辅助函数
"""

import re

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
