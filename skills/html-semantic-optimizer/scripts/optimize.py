#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML 语义化优化脚本 - 兼容Python 2/3
"""

import argparse
import json
import sys
import os
import io

# 添加父目录到模块搜索路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PARENT_DIR)

from html_optimizer import RuleEngine, DOMTransformer


def load_rules(rules_path=None):
    """加载规则配置"""
    default_rules = {
        "rules": [
            {"name": "button", "keywords": ["btn", "button", "按钮"], "target_tag": "button", "priority": 10},
            {"name": "link", "keywords": ["link", "链接", "a-btn", "nav-link"], "target_tag": "a", "priority": 10},
            {"name": "navigation", "keywords": ["nav", "navbar", "导航", "menu"], "target_tag": "nav", "priority": 5},
            {"name": "header", "keywords": ["header", "头部", "top-bar", "page-header"], "target_tag": "header", "priority": 5},
            {"name": "footer", "keywords": ["footer", "底部", "bottom", "page-footer"], "target_tag": "footer", "priority": 5},
            {"name": "main", "keywords": ["main", "content", "主内容", "main-content"], "target_tag": "main", "priority": 5},
            {"name": "article", "keywords": ["article", "post", "blog"], "target_tag": "article", "priority": 4},
            {"name": "aside", "keywords": ["aside", "sidebar", "sidenav"], "target_tag": "aside", "priority": 4},
            {"name": "section", "keywords": ["section"], "target_tag": "section", "priority": 3}
        ]
    }
    
    if not rules_path:
        return default_rules
    
    try:
        with io.open(rules_path, 'r', encoding='utf-8') as f:
            custom_rules = json.load(f)
            merged = {"rules": list(default_rules["rules"])}
            existing = {r["name"]: i for i, r in enumerate(merged["rules"])}
            for custom in custom_rules.get("rules", []):
                name = custom.get("name")
                if name in existing:
                    merged["rules"][existing[name]] = custom
                else:
                    merged["rules"].append(custom)
            return merged
    except Exception as e:
        sys.stderr.write("警告: 加载自定义规则失败: " + str(e) + "，使用默认规则\n")
        return default_rules


def main():
    parser = argparse.ArgumentParser(
        description='HTML 语义化优化工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python optimize.py input.html -o output.html
  python optimize.py input.html --dry-run
  python optimize.py input.html --rules custom.json
        '''
    )
    
    parser.add_argument('input', help='输入HTML文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（默认覆盖原文件）')
    parser.add_argument('-r', '--rules', help='自定义规则JSON文件')
    parser.add_argument('-d', '--dry-run', action='store_true', help='试运行，不保存文件')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        sys.stderr.write("错误: 输入文件不存在: " + args.input + "\n")
        sys.exit(1)
    
    try:
        with io.open(args.input, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        sys.stderr.write("错误: 读取文件失败: " + str(e) + "\n")
        sys.exit(1)
    
    rules_config = load_rules(args.rules)
    engine = RuleEngine(rules_config["rules"])
    transformer = DOMTransformer(engine)
    
    try:
        result = transformer.transform(html_content)
        print("成功: HTML转换完成，处理了 " + str(len(html_content)) + " 字节")
    except Exception as e:
        sys.stderr.write("错误: 转换失败: " + str(e) + "\n")
        sys.exit(1)
    
    if args.dry_run:
        print("\n--- 转换结果预览 ---")
        preview = result[:2000] + "..." if len(result) > 2000 else result
        print(preview)
        print("\n(试运行模式，未保存文件)")
    else:
        output_path = args.output if args.output else args.input
        try:
            with io.open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            print("已保存到: " + output_path)
        except Exception as e:
            sys.stderr.write("错误: 保存文件失败: " + str(e) + "\n")
            sys.exit(1)


if __name__ == '__main__':
    main()
