# -*- coding: utf-8 -*-
"""
CSS Modules 解析器 - 使用正则表达式解析 .module.css 文件

功能:
- 解析 CSS Modules 文件中的类选择器
- 提取每个类的 CSS 属性和值
- 保留原始 CSS 文本
- 支持 CLI 运行

输出格式:
{
  "className": {
    "properties": {"prop": "value", ...},
    "raw": "原始CSS文本"
  }
}
"""

import re
import sys
import json
import argparse
from typing import Dict, Any, Optional


def remove_comments(css_text: str) -> str:
    """移除 CSS 中的注释"""
    # 移除 /* */ 格式的注释
    return re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)


def parse_css(file_path: str) -> Dict[str, Any]:
    """
    解析 CSS Modules 文件

    参数:
        file_path: CSS 文件路径

    返回:
        字典，键为类名，值为包含属性和原始文本的字典
    """
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        css_text = f.read()

    # 移除注释
    css_clean = remove_comments(css_text)

    result = {}

    # 正则表达式匹配 CSS 规则块
    # 匹配模式: .class-name { ... }
    # 支持多行、嵌套空格等
    rule_pattern = r'\s*\.([\w-]+)\s*\{([^}]*)\}'

    for match in re.finditer(rule_pattern, css_clean, re.DOTALL):
        class_name = match.group(1)
        declarations = match.group(2).strip()
        raw_text = match.group(0).strip()

        # 解析属性声明
        properties = {}
        # 匹配属性:值对（支持多行）
        # 格式: property: value; 或 property: value
        prop_pattern = r'([\w-]+)\s*:\s*([^;]+);?'

        for prop_match in re.finditer(prop_pattern, declarations):
            prop_name = prop_match.group(1).strip()
            prop_value = prop_match.group(2).strip()
            properties[prop_name] = prop_value

        result[class_name] = {
            "properties": properties,
            "raw": raw_text
        }

    return result


def parse_css_to_json(file_path: str, output_path: Optional[str] = None) -> str:
    """
    解析 CSS 并输出为 JSON 格式

    参数:
        file_path: CSS 文件路径
        output_path: 可选的输出 JSON 文件路径

    返回:
        JSON 字符串
    """
    parsed = parse_css(file_path)
    json_str = json.dumps(parsed, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"解析结果已保存到: {output_path}")

    return json_str


def print_parsed_css(parsed: Dict[str, Any], verbose: bool = False):
    """
    打印解析后的 CSS 结果

    参数:
        parsed: parse_css 返回的字典
        verbose: 是否显示详细信息
    """
    print(f"\n共解析到 {len(parsed)} 个 CSS 类:\n")

    for class_name, data in parsed.items():
        props = data['properties']
        print(f"类名: .{class_name}")
        print(f"  属性数量: {len(props)}")

        if verbose:
            print("  属性列表:")
            for prop, value in props.items():
                print(f"    {prop}: {value}")
            print(f"  原始文本:\n    {data['raw'][:100]}{'...' if len(data['raw']) > 100 else ''}")

        print()


def main():
    """CLI 入口点"""
    parser = argparse.ArgumentParser(
        description='解析 CSS Modules 文件，提取类选择器和属性',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 解析 CSS 文件并打印结果
  python css_parser.py styles.module.css

  # 解析并保存为 JSON
  python css_parser.py styles.module.css -o output.json

  # 显示详细信息
  python css_parser.py styles.module.css -v

  # 仅输出 JSON 到控制台
  python css_parser.py styles.module.css --json
        """
    )

    parser.add_argument(
        'file',
        help='要解析的 CSS 文件路径（支持 .module.css 或 .css）'
    )

    parser.add_argument(
        '-o', '--output',
        help='输出 JSON 文件路径（可选）'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='仅输出 JSON 格式的解析结果'
    )

    args = parser.parse_args()

    try:
        parsed = parse_css(args.file)

        if args.json:
            # 仅输出 JSON
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        elif args.output:
            # 保存到文件
            parse_css_to_json(args.file, args.output)
            if args.verbose:
                print_parsed_css(parsed, verbose=True)
        else:
            # 打印格式化结果
            print_parsed_css(parsed, verbose=args.verbose)

    except FileNotFoundError:
        print(f"错误: 文件不存在 - {args.file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
