#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
组件分析器 CLI 入口

分析 React/Vue 组件目录，生成依赖图、检测重复模式并提供拆分建议。

用法示例:
    py -3 analyze_components.py --input react-split/ --framework react --output report.json --format json
    py -3 analyze_components.py --input vue-split/ --framework vue --format markdown

兼容 Python 2.7+ 和 Python 3.x
"""

from __future__ import print_function
import argparse
import os
import sys
import json

# Python 2/3 兼容性
PY2 = sys.version_info[0] == 2

if PY2:
    import io
    open = io.open
    text_type = unicode
else:
    text_type = str

# 确保可以导入同级模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 导入分析模块
try:
    from react_ast_parser import parse_react_file
    from dependency_graph import analyze_directory
    from pattern_detector import detect_patterns
    from split_suggester import generate_suggestions, format_output
except ImportError as e:
    print("[错误] 无法导入必要的模块: {0}".format(e), file=sys.stderr)
    print("请确保以下模块文件存在于同一目录:", file=sys.stderr)
    print("  - react_ast_parser.py", file=sys.stderr)
    print("  - dependency_graph.py", file=sys.stderr)
    print("  - pattern_detector.py", file=sys.stderr)
    print("  - split_suggester.py", file=sys.stderr)
    sys.exit(1)


def create_parser():
    """
    创建命令行参数解析器
    
    返回:
        ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog='analyze_components',
        description='''
组件分析器 - 分析 React/Vue 组件并提供优化建议

本工具可以:
  1. 扫描组件目录，构建组件间依赖关系图
  2. 检测重复的 JSX 结构和相似的组件模式
  3. 识别循环依赖和过深的组件层级
  4. 生成具体的拆分、合并和重构建议

输出格式支持 JSON（便于程序处理）和 Markdown（便于人工阅读）。
        '''.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基本用法 - 分析 React 组件并输出到文件
  py -3 %(prog)s --input ./src/components --framework react --output report.json

  # 输出 Markdown 格式到控制台
  py -3 %(prog)s --input ./src/components --format markdown

  # 分析 Vue 组件
  py -3 %(prog)s --input ./src --framework vue --output vue-report.json

  # 使用完整参数
  py -3 %(prog)s --input ./components --framework react --output analysis.json --format json

注意事项:
  - 输入目录必须存在且包含 .jsx (React) 或 .vue (Vue) 文件
  - 程序会自动跳过 node_modules 和隐藏目录
  - 输出文件如果已存在将被覆盖
  - 若不指定 --output，结果将输出到 stdout
        '''.strip()
    )
    
    # 必需参数
    parser.add_argument(
        '--input', '-i',
        required=True,
        metavar='DIR',
        help='组件目录路径（必需）。包含 React (.jsx) 或 Vue (.vue) 文件的目录。'
    )
    
    parser.add_argument(
        '--framework', '-f',
        required=True,
        choices=['react', 'vue'],
        default='react',
        help='前端框架类型（必需）。可选值: react, vue。默认: react。'
    )
    
    # 可选参数
    parser.add_argument(
        '--output', '-o',
        metavar='FILE',
        default=None,
        help='输出文件路径（可选）。若不指定，结果将输出到 stdout。'
    )
    
    parser.add_argument(
        '--format', '-fmt',
        choices=['json', 'markdown', 'md'],
        default='json',
        help='输出格式（可选）。可选值: json, markdown/md。默认: json。'
    )
    
    # 高级选项
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=0.7,
        metavar='FLOAT',
        help='相似度阈值（可选）。用于检测相似组件，范围 0.0-1.0。默认: 0.7。'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细进度信息。'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def validate_input(directory, framework):
    """
    验证输入参数
    
    参数:
        directory: 输入目录路径
        framework: 框架类型
    
    返回:
        (bool, str) - (是否有效, 错误信息)
    """
    # 检查目录是否存在
    if not os.path.exists(directory):
        return False, "输入目录不存在: {0}".format(directory)
    
    # 检查是否为目录
    if not os.path.isdir(directory):
        return False, "输入路径不是目录: {0}".format(directory)
    
    # 检查目录是否可读
    if not os.access(directory, os.R_OK):
        return False, "无法读取输入目录（权限不足）: {0}".format(directory)
    
    # 检查阈值范围
    if framework not in ['react', 'vue']:
        return False, "不支持的框架类型: {0}。仅支持 react 或 vue。".format(framework)
    
    return True, None


def print_progress(message, verbose=True):
    """
    打印进度信息
    
    参数:
        message: 进度消息
        verbose: 是否显示详细输出
    """
    if verbose:
        timestamp = ""
        print("[{0}] {1}".format(timestamp, message))


def scan_components(directory, framework, verbose=False):
    """
    扫描目录收集组件信息
    
    参数:
        directory: 组件目录
        framework: 框架类型
        verbose: 是否显示详细输出
    
    返回:
        list: 组件信息列表
    """
    components = []
    
    if framework == 'react':
        file_ext = '.jsx'
        parser_func = parse_react_file
    elif framework == 'vue':
        # Vue 支持暂未实现，返回空列表
        file_ext = '.vue'
        parser_func = None
    else:
        return components
    
    print_progress("正在扫描目录: {0}".format(directory), verbose)
    
    file_count = 0
    for root, dirs, files in os.walk(directory):
        # 跳过 node_modules 和隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
        
        for file in files:
            if file.endswith(file_ext):
                file_path = os.path.join(root, file)
                file_count += 1
                
                if verbose and file_count % 10 == 0:
                    print_progress("已扫描 {0} 个文件...".format(file_count), verbose)
                
                if framework == 'react' and parser_func:
                    try:
                        parsed = parser_func(file_path)
                        if 'error' not in parsed and parsed.get('component_name'):
                            component_info = {
                                'name': parsed.get('component_name'),
                                'file': os.path.relpath(file_path, directory),
                                'props': parsed.get('props', []),
                                'jsx_elements': [elem.get('type', '') for elem in parsed.get('jsx_elements', [])],
                                'uses_css_module': bool(parsed.get('css_module_import')),
                                'absolute_path': file_path
                            }
                            components.append(component_info)
                    except Exception as e:
                        if verbose:
                            print_progress("解析文件失败 {0}: {1}".format(file_path, str(e)), verbose)
    
    print_progress("扫描完成，共发现 {0} 个组件文件，成功解析 {1} 个组件。".format(file_count, len(components)), verbose)
    
    return components


def main():
    """
    主函数 - CLI 入口
    """
    # 创建参数解析器
    parser = create_parser()
    
    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 会在 --help 或错误时调用 sys.exit()
        sys.exit(e.code)
    
    # 验证输入
    is_valid, error_msg = validate_input(args.input, args.framework)
    if not is_valid:
        print("[错误] {0}".format(error_msg), file=sys.stderr)
        sys.exit(1)
    
    verbose = args.verbose
    
    print_progress("=" * 60, verbose)
    print_progress("组件分析器 Component Analyzer v1.0.0", verbose)
    print_progress("=" * 60, verbose)
    print_progress("", verbose)
    print_progress("输入目录: {0}".format(args.input), verbose)
    print_progress("框架类型: {0}".format(args.framework), verbose)
    print_progress("输出格式: {0}".format(args.format), verbose)
    print_progress("相似度阈值: {0}".format(args.threshold), verbose)
    print_progress("", verbose)
    
    try:
        # 步骤 1: 构建依赖图
        print_progress("[步骤 1/4] 构建组件依赖图...", verbose)
        dependency_graph = analyze_directory(args.input)
        
        node_count = len(dependency_graph.get('nodes', []))
        edge_count = len(dependency_graph.get('edges', []))
        cycle_count = len(dependency_graph.get('cycles', []))
        
        print_progress("  - 发现 {0} 个组件节点".format(node_count), verbose)
        print_progress("  - 发现 {0} 条依赖边".format(edge_count), verbose)
        if cycle_count > 0:
            print_progress("  - [警告] 发现 {0} 个循环依赖！".format(cycle_count), verbose)
        else:
            print_progress("  - 未发现循环依赖", verbose)
        
        # 步骤 2: 扫描组件详细信息
        print_progress("[步骤 2/4] 扫描组件详细信息...", verbose)
        components = scan_components(args.input, args.framework, verbose)
        
        if not components and node_count == 0:
            print("[警告] 未在目录中发现任何组件文件。", file=sys.stderr)
            print("支持的文件类型: .jsx (React), .vue (Vue)", file=sys.stderr)
            sys.exit(1)
        
        # 步骤 3: 检测重复模式
        print_progress("[步骤 3/4] 检测重复模式...", verbose)
        
        # 构建 patterns 数据结构
        patterns = {}
        
        if components:
            # 使用 pattern_detector 检测模式
            detector_result = detect_patterns(components, threshold=args.threshold)
            
            # 转换数据结构以适配 split_suggester
            patterns['duplicated_jsx'] = []
            patterns['similar_components'] = []
            patterns['shared_props'] = []
            patterns['shared_styles'] = []
            
            # 处理检测到的模式
            for pattern in detector_result.get('patterns', []):
                pattern_type = pattern.get('type', '')
                
                if pattern_type == 'structure_similarity':
                    patterns['similar_components'].append({
                        'components': pattern.get('components', []),
                        'similarity_score': pattern.get('similarity', 0),
                        'common_props': [],
                        'differences': []
                    })
                elif pattern_type == 'props_similarity':
                    patterns['shared_props'].append({
                        'components': pattern.get('components', []),
                        'shared_props': list(pattern.get('signature', [])),
                        'props_variations': {}
                    })
        
        pattern_count = (
            len(patterns.get('duplicated_jsx', [])) +
            len(patterns.get('similar_components', [])) +
            len(patterns.get('shared_props', []))
        )
        print_progress("  - 发现 {0} 个重复模式".format(pattern_count), verbose)
        
        # 步骤 4: 生成拆分建议
        print_progress("[步骤 4/4] 生成拆分建议...", verbose)
        
        # 准备依赖图格式
        dep_graph_for_suggester = {
            'components': [node.get('id') for node in dependency_graph.get('nodes', [])],
            'dependencies': [
                {'source': edge.get('from'), 'target': edge.get('to')}
                for edge in dependency_graph.get('edges', [])
            ],
            'imports': {}
        }
        
        suggestions = generate_suggestions(dep_graph_for_suggester, patterns)
        
        suggestion_count = len(suggestions)
        print_progress("  - 生成 {0} 条优化建议".format(suggestion_count), verbose)
        
        # 格式化输出
        format_type = args.format
        if format_type == 'md':
            format_type = 'markdown'
        
        output_content = format_output(suggestions, format_type, dep_graph_for_suggester)
        
        # 输出结果
        if args.output:
            # 写入文件
            output_dir = os.path.dirname(args.output)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except OSError as e:
                    print("[错误] 无法创建输出目录: {0}".format(e), file=sys.stderr)
                    sys.exit(1)
            
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_content)
                print_progress("", verbose)
                print_progress("=" * 60, verbose)
                print_progress("分析完成！报告已保存到: {0}".format(args.output), verbose)
                print_progress("=" * 60, verbose)
                
                if not verbose:
                    # 非详细模式也输出保存路径
                    print(args.output)
            except IOError as e:
                print("[错误] 无法写入输出文件: {0}".format(e), file=sys.stderr)
                sys.exit(1)
        else:
            # 输出到 stdout
            print(output_content)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        print("[信息] 用户取消操作。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print("[错误] 分析过程中发生异常: {0}".format(str(e)), file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
