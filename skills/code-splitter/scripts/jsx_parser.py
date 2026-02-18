#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSX 解析器 - 使用正则表达式解析 JSX 代码

功能：
- 解析 JSX 元素树结构
- 提取 className={styles["class-name"]} 格式
- 识别自闭合标签
- 提取注释信息
- 返回 JSON 格式的元素树

作者：AI Assistant
创建日期：2026-02-13
"""

import re
import json
import sys
import os
from typing import Dict, List, Any, Optional, Tuple


class JSXElement:
    """JSX 元素节点"""
    
    def __init__(self, tag: str = "", className: str = "", attributes: Optional[Dict[str, str]] = None,
                 selfClosing: bool = False, comment: str = ""):
        self.tag = tag
        self.className = className
        self.attributes = attributes if attributes is not None else {}
        self.selfClosing = selfClosing
        self.comment = comment
        self.children: List['JSXElement'] = []
        self.text = ""  # 文本内容
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "tag": self.tag,
            "className": self.className,
            "attributes": self.attributes,
            "selfClosing": self.selfClosing,
            "children": [child.to_dict() for child in self.children]
        }
        if self.text:
            result["text"] = self.text
        if self.comment:
            result["comment"] = self.comment
        return result
    
    def __repr__(self) -> str:
        return f"<JSXElement {self.tag} className={self.className}>"


class JSXParser:
    """JSX 解析器 - 基于正则表达式"""
    
    def __init__(self):
        # 正则表达式模式
        self.patterns = {
            # 注释: {/* comment */}
            'comment': re.compile(r'\{/\*\s*(.+?)\s*\*/\}'),
            
            # 自闭合标签: <div className={styles["name"]} />
            'selfClosing': re.compile(r'<(\w+)\s*([^>]*)/>'),
            
            # 开始标签: <div className={styles["name"]}>
            'openTag': re.compile(r'<(\w+)\s*([^>]*)>'),
            
            # 结束标签: </div>
            'closeTag': re.compile(r'</(\w+)>'),
            
            # 文本内容
            'text': re.compile(r'>([^<]+)<'),
            
            # className: className={styles["name"]} 或 className="name"
            'className': re.compile(r'className=\{styles\["([^"]+)"\]\}'),
            'classNameSimple': re.compile(r'className="([^"]+)"'),
            
            # 其他属性: role="img" aria-label="背景"
            'attribute': re.compile(r'(\w+)=\s*"([^"]*)"'),
            
            # JSX 表达式（简单处理，仅提取表达式内容）
            'expression': re.compile(r'\{([^}]+)\}'),
        }
    
    def parse_classname(self, attrs_str: str) -> Tuple[str, str]:
        """
        解析 className 属性
        
        支持格式：
        - className={styles["name"]}
        - className="name"
        
        返回: (className值, 剩余属性字符串)
        """
        # 先尝试匹配 styles["name"] 格式
        match = self.patterns['className'].search(attrs_str)
        if match:
            class_name = match.group(1)
            # 移除 className 部分，保留其他属性
            remaining = attrs_str[:match.start()] + attrs_str[match.end():]
            return class_name, remaining.strip()
        
        # 尝试匹配简单字符串格式
        match = self.patterns['classNameSimple'].search(attrs_str)
        if match:
            class_name = match.group(1)
            remaining = attrs_str[:match.start()] + attrs_str[match.end():]
            return class_name, remaining.strip()
        
        return "", attrs_str
    
    def parse_attributes(self, attrs_str: str) -> Dict[str, str]:
        """
        解析其他属性（排除 className）
        
        支持格式：
        - role="img"
        - aria-label="背景"
        - data-custom="value"
        """
        attributes = {}
        
        for match in self.patterns['attribute'].finditer(attrs_str):
            attr_name = match.group(1)
            attr_value = match.group(2)
            # 跳过 className（已在单独处理）
            if attr_name != 'className':
                attributes[attr_name] = attr_value
        
        return attributes
    
    def parse_open_tag(self, tag_str: str) -> Tuple[str, str, Dict[str, str], bool]:
        """
        解析开始标签
        
        返回: (标签名, className, 属性字典, 是否自闭合)
        """
        # 检查是否自闭合
        self_closing = tag_str.strip().endswith('/>')
        
        # 提取标签内容
        if self_closing:
            match = self.patterns['selfClosing'].match(tag_str)
        else:
            match = self.patterns['openTag'].match(tag_str)
        
        if not match:
            return "", "", {}, False
        
        tag_name = match.group(1)
        attrs_str = match.group(2).strip()
        
        # 解析 className
        class_name, remaining_attrs = self.parse_classname(attrs_str)
        
        # 解析其他属性
        attributes = self.parse_attributes(remaining_attrs)
        
        return tag_name, class_name, attributes, self_closing
    
    def parse(self, source: str) -> List[JSXElement]:
        """
        解析 JSX 源代码
        
        返回顶层元素列表
        """
        # 移除前后空白
        source = source.strip()
        
        # 清理多余的空白字符
        source = re.sub(r'\n\s*\n', '\n', source)
        
        # 解析入口
        elements = self._parse_jsx_recursive(source, 0)
        
        return elements
    
    def _parse_jsx_recursive(self, source: str, start_pos: int) -> List[JSXElement]:
        """
        递归解析 JSX 元素
        
        参数:
            source: 源代码
            start_pos: 开始解析的位置
            
        返回:
            解析出的元素列表和结束位置
        """
        elements = []
        pos = start_pos
        
        while pos < len(source):
            # 跳过空白字符
            while pos < len(source) and source[pos].isspace():
                pos += 1
            
            if pos >= len(source):
                break
            
            # 检查是否是注释
            if source[pos:pos+2] == '{/':
                match = self.patterns['comment'].match(source[pos:])
                if match:
                    # 注释作为独立元素处理
                    comment_elem = JSXElement(comment=match.group(1).strip())
                    elements.append(comment_elem)
                    pos += match.end()
                    continue
            
            # 检查是否是结束标签
            if source[pos:pos+2] == '</':
                match = self.patterns['closeTag'].match(source[pos:])
                if match:
                    # 结束标签 - 返回当前元素列表
                    break
            
            # 检查是否是自闭合标签
            self_closing_match = self.patterns['selfClosing'].match(source[pos:])
            if self_closing_match:
                tag_str = self_closing_match.group(0)
                tag_name, class_name, attributes, _ = self.parse_open_tag(tag_str)
                
                elem = JSXElement(
                    tag=tag_name,
                    className=class_name,
                    attributes=attributes,
                    selfClosing=True
                )
                elements.append(elem)
                pos += self_closing_match.end()
                continue
            
            # 检查是否是开始标签
            open_match = self.patterns['openTag'].match(source[pos:])
            if open_match:
                tag_str = open_match.group(0)
                tag_name, class_name, attributes, _ = self.parse_open_tag(tag_str)
                
                elem = JSXElement(
                    tag=tag_name,
                    className=class_name,
                    attributes=attributes,
                    selfClosing=False
                )
                
                # 移动到标签内容开始
                pos += open_match.end()
                
                # 递归解析子元素
                children = self._parse_jsx_recursive(source, pos)
                elem.children = children
                
                # 查找对应的结束标签
                # 简单的字符串匹配，找到对应的 </tag_name>
                end_tag = f'</{tag_name}>'
                end_pos = source.find(end_tag, pos)
                if end_pos != -1:
                    # 提取文本内容（如果有）
                    text_content = source[pos:end_pos].strip()
                    # 移除子元素标签后的纯文本
                    if text_content and not text_content.startswith('<'):
                        elem.text = re.sub(r'<[^>]+>', '', text_content).strip()
                    pos = end_pos + len(end_tag)
                else:
                    # 未找到结束标签，可能是解析错误
                    pos = len(source)
                
                elements.append(elem)
                continue
            
            # 无法识别的内容，跳过
            pos += 1
        
        return elements


def parse_jsx(source_code: str) -> List[Dict[str, Any]]:
    """
    解析 JSX 源代码的主函数
    
    参数:
        source_code: JSX 源代码字符串
        
    返回:
        元素树的 JSON 表示（字典列表）
        
    示例:
        >>> jsx = '<div className={styles["test"]}><span>Hello</span></div>'
        >>> result = parse_jsx(jsx)
        >>> print(json.dumps(result, indent=2, ensure_ascii=False))
    """
    parser = JSXParser()
    elements = parser.parse(source_code)
    return [elem.to_dict() for elem in elements]


def parse_jsx_file(file_path: str) -> List[Dict[str, Any]]:
    """
    从文件解析 JSX
    
    参数:
        file_path: JSX 文件路径
        
    返回:
        元素树的 JSON 表示
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    return parse_jsx(source)


def format_output(elements: List[Dict[str, Any]], indent: int = 2) -> str:
    """
    格式化输出 JSON
    
    参数:
        elements: 元素列表
        indent: 缩进空格数
        
    返回:
        格式化的 JSON 字符串
    """
    return json.dumps(elements, indent=indent, ensure_ascii=False)


def print_tree(elements: List[Dict[str, Any]], indent: int = 0):
    """
    打印元素树（树形结构）
    
    参数:
        elements: 元素列表
        indent: 当前缩进级别
    """
    for elem in elements:
        prefix = "  " * indent
        
        # 注释
        if elem.get('comment') and not elem.get('tag'):
            print(f"{prefix}<!-- {elem['comment']} -->")
            continue
        
        # 元素
        tag = elem.get('tag', '')
        className = elem.get('className', '')
        selfClosing = elem.get('selfClosing', False)
        comment = elem.get('comment', '')
        
        if not tag:
            continue
        
        # 构建属性字符串
        attrs = []
        if className:
            attrs.append(f'className="{className}"')
        for key, value in elem.get('attributes', {}).items():
            attrs.append(f'{key}="{value}"')
        
        attr_str = ' '.join(attrs)
        
        # 输出
        if selfClosing:
            if attr_str:
                print(f"{prefix}<{tag} {attr_str} />")
            else:
                print(f"{prefix}<{tag} />")
        else:
            if attr_str:
                print(f"{prefix}<{tag} {attr_str}>")
            else:
                print(f"{prefix}<{tag}>")
        
        # 输出注释
        if comment:
            print(f"{prefix}  <!-- {comment} -->")
        
        # 递归输出子元素
        children = elem.get('children', [])
        if children:
            print_tree(children, indent + 1)
        
        # 输出结束标签（非自闭合）
        if not selfClosing:
            print(f"{prefix}</{tag}>")


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='JSX 解析器 - 使用正则表达式解析 JSX 代码',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s file.jsx                          # 解析文件
  %(prog)s file.jsx --json                   # 输出 JSON 格式
  %(prog)s file.jsx --tree                   # 输出树形结构
  echo '<div />' | %(prog)s                  # 从管道读取
        """
    )
    
    parser.add_argument('input', nargs='?', help='JSX 文件路径（可选，默认从 stdin 读取）')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式（默认）')
    parser.add_argument('--tree', action='store_true', help='输出树形结构')
    parser.add_argument('--compact', action='store_true', help='输出紧凑 JSON')
    
    args = parser.parse_args()
    
    # 读取输入
    if args.input:
        try:
            result = parse_jsx_file(args.input)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"解析错误: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 从 stdin 读取
        source = sys.stdin.read()
        if not source.strip():
            print("错误: 未提供输入", file=sys.stderr)
            sys.exit(1)
        result = parse_jsx(source)
    
    # 输出
    if args.tree:
        print_tree(result)
    elif args.compact:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(format_output(result))


if __name__ == '__main__':
    main()
