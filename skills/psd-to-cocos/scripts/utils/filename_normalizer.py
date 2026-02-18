"""
PSD 文件名规范化模块

将 PSD 文件名转换为合法的目录名/文件名，支持：
1. 提取文件名（不含扩展名）
2. 中文转拼音
3. 非法字符处理
4. 长度限制（50字符）
"""

import re
import hashlib
import time
from typing import Optional
from pypinyin import pinyin, Style


def chinese_to_pinyin(text: str) -> str:
    """
    将中文字符串转换为拼音（小写，无分隔符）
    
    Args:
        text: 中文字符串
        
    Returns:
        拼音字符串
        
    Example:
        >>> chinese_to_pinyin("首页")
        'shouye'
        >>> chinese_to_pinyin("UI-首页")
        'ui-shouye'
    """
    result = []
    for char in text:
        # 如果是中文字符，转换为拼音
        if '\u4e00' <= char <= '\u9fff':
            py = pinyin(char, style=Style.NORMAL, errors='ignore')
            if py:
                result.append(py[0][0])
        # 保留允许的字符
        elif char.isalnum() or char in '-_':
            result.append(char)
        # 其他字符（包括空格）转为连字符
        else:
            # 避免连续的连字符
            if result and result[-1] != '-':
                result.append('-')
    
    # 清理连续的连字符和首尾连字符
    pinyin_str = ''.join(result)
    pinyin_str = re.sub(r'-+', '-', pinyin_str)
    pinyin_str = pinyin_str.strip('-')
    
    return pinyin_str.lower()


def has_illegal_chars(text: str) -> bool:
    """
    检查是否包含非法字符
    
    Args:
        text: 要检查的字符串
        
    Returns:
        True 如果包含非法字符
    """
    # 允许的字符：字母、数字、连字符、下划线
    allowed_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    # 检查每个字符
    for char in text:
        if not allowed_pattern.match(char):
            return True
    return False


def generate_fallback_name(original_name: str, max_length: int = 50) -> str:
    """
    为非法文件名生成备用名称
    
    Args:
        original_name: 原始文件名
        max_length: 最大长度
        
    Returns:
        psd-{timestamp}-{hash} 格式的名称
    """
    timestamp = int(time.time())
    # 使用原始名的哈希来保持唯一性
    name_hash = hashlib.md5(original_name.encode('utf-8')).hexdigest()[:8]
    fallback = f"psd-{timestamp}-{name_hash}"
    
    return fallback[:max_length]


def normalize_psd_filename(filename: Optional[str], max_length: int = 50) -> str:
    """
    将 PSD 文件名规范化为合法的目录名
    
    Args:
        filename: PSD 文件名（如 "首页.psd"）
        max_length: 最大长度限制（默认50字符）
        
    Returns:
        规范化后的名称（如 "shouye"）
        
    Example:
        >>> normalize_psd_filename("design.psd")
        'design'
        >>> normalize_psd_filename("首页.psd")
        'shouye'
        >>> normalize_psd_filename("UI-首页-新版.psd")
        'ui-shouye-xinban'
        >>> normalize_psd_filename("@#$%.psd")
        'psd-{timestamp}-{random}'
    """
    if not filename or not isinstance(filename, str):
        return generate_fallback_name("invalid", max_length)
    
    # 1. 去除扩展名
    name = filename
    if filename.lower().endswith('.psd'):
        name = filename[:-4]
    
    if not name:
        return generate_fallback_name("empty", max_length)
    
    # 2. 检查是否包含中文
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', name))
    
    # 3. 处理中文转拼音
    if has_chinese:
        normalized = chinese_to_pinyin(name)
    else:
        # 对非中文也进行标准化处理（处理空格等特殊字符）
        normalized = chinese_to_pinyin(name)
    
    # 4. 如果转换后为空或只有非法字符，生成备用名
    if not normalized or normalized.strip('-_') == '':
        return generate_fallback_name(filename, max_length)
    
    # 5. 再次检查是否还有非法字符
    if has_illegal_chars(normalized):
        return generate_fallback_name(filename, max_length)
    
    # 6. 处理长度限制
    if len(normalized) > max_length:
        # 计算哈希后缀
        name_hash = hashlib.md5(normalized.encode('utf-8')).hexdigest()[:6]
        # 保留前半部分，添加连字符和哈希
        available_length = max_length - len(name_hash) - 1
        if available_length > 0:
            truncated = normalized[:available_length].rstrip('-_')
            normalized = f"{truncated}-{name_hash}"
        else:
            # 极端情况：直接截断
            normalized = normalized[:max_length]
    
    return normalized


# 向后兼容的别名
sanitize_filename = normalize_psd_filename


if __name__ == "__main__":
    # 简单测试
    test_cases = [
        "design.psd",
        "首页.psd",
        "UI-首页-新版.psd",
        "我的游戏界面.psd",
        "test_file_001.psd",
        "@#$%.psd",
        "超长中文文件名用于测试这是一个非常长的文件名可能会超过限制.psd",
    ]
    
    print("PSD 文件名规范化测试：")
    print("-" * 60)
    for test in test_cases:
        result = normalize_psd_filename(test)
        print(f"{test:30} → {result}")
        print(f"  长度: {len(result)} 字符")
        print()
