#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代码拆分分析器 - 智能分析算法

功能：
- 基于多维度分析识别可拆分的组件
- 语义类名分析（btn-* → button, card-* → card 等）
- DOM 结构分析（包裹多个子元素的容器）
- 重复模式检测（相似结构）
- 位置分析（top → Header, bottom → Footer）
- 返回候选拆分点列表，包含 score、reason、suggested_name

作者：AI Assistant
创建日期：2026-02-13
"""

import re
import json
import sys
import os
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

# 导入解析器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsx_parser import parse_jsx_file, JSXParser
from css_parser import parse_css


# ==================== 语义类名模式定义 ====================

SEMANTIC_PATTERNS = {
    # 按钮类
    r'^btn[-_]': {'type': 'button', 'score': 0.9, 'prefix': 'Btn'},
    r'^button[-_]?' : {'type': 'button', 'score': 0.9, 'prefix': 'Button'},
    # 图标类
    r'^icon[-_]' : {'type': 'icon', 'score': 0.7, 'prefix': 'Icon'},
    # 卡片/容器类
    r'^card[-_]?' : {'type': 'card', 'score': 0.95, 'prefix': 'Card'},
    r'^container[-_]?' : {'type': 'container', 'score': 0.8, 'prefix': 'Container'},
    # 文本类
    r'^text[-_]' : {'type': 'text', 'score': 0.6, 'prefix': 'Text'},
    r'^title[-_]?' : {'type': 'title', 'score': 0.7, 'prefix': 'Title'},
    # 头部/底部
    r'^header[-_]?' : {'type': 'header', 'score': 0.9, 'prefix': 'Header'},
    r'^footer[-_]?' : {'type': 'footer', 'score': 0.9, 'prefix': 'Footer'},
    r'^nav[-_]?' : {'type': 'navigation', 'score': 0.85, 'prefix': 'Nav'},
    # 框架/布局
    r'^frame[-_]' : {'type': 'frame', 'score': 0.75, 'prefix': 'Frame'},
    r'^layout[-_]?' : {'type': 'layout', 'score': 0.8, 'prefix': 'Layout'},
    # 列表/项
    r'^list[-_]?' : {'type': 'list', 'score': 0.75, 'prefix': 'List'},
    r'^item[-_]?' : {'type': 'item', 'score': 0.6, 'prefix': 'Item'},
    # 表单相关
    r'^form[-_]?' : {'type': 'form', 'score': 0.85, 'prefix': 'Form'},
    r'^input[-_]?' : {'type': 'input', 'score': 0.7, 'prefix': 'Input'},
    # 模态/弹窗
    r'^modal[-_]?' : {'type': 'modal', 'score': 0.9, 'prefix': 'Modal'},
    r'^dialog[-_]?' : {'type': 'dialog', 'score': 0.9, 'prefix': 'Dialog'},
    # 特殊业务组件
    r'^rs[-_]' : {'type': 'rare_beast', 'score': 0.8, 'prefix': 'Rs'},  # 瑞兽相关
    r'^daily[-_]' : {'type': 'daily', 'score': 0.7, 'prefix': 'Daily'},
    r'^date[-_]' : {'type': 'date', 'score': 0.65, 'prefix': 'Date'},
}

# 位置推断模式
POSITION_PATTERNS = {
    'header': {'keywords': ['header', 'top', 'nav', 'logo'], 'score': 0.3},
    'footer': {'keywords': ['footer', 'bottom'], 'score': 0.3},
    'sidebar': {'keywords': ['sidebar', 'side', 'left', 'right'], 'score': 0.25},
}


# ==================== 核心分析类 ====================

class SplitAnalyzer:
    """组件拆分分析器"""
    
    def __init__(self, element_tree: List[Dict], css_map: Dict[str, Any]):
        """
        初始化分析器
        
        参数:
            element_tree: JSX 解析后的元素树
            css_map: CSS 解析后的样式映射
        """
        self.element_tree = element_tree
        self.css_map = css_map
        self.candidates = []
        self.flat_elements = []  # 扁平化的元素列表
        
        # 扁平化元素树，便于分析
        self._flatten_elements(element_tree)
    
    def _flatten_elements(self, elements: List[Dict], depth: int = 0, parent: Optional[Dict] = None):
        """
        扁平化元素树，记录深度和父子关系
        
        参数:
            elements: 元素列表
            depth: 当前深度
            parent: 父元素
        """
        for elem in elements:
            if not elem.get('tag'):  # 跳过注释
                continue
            
            elem['_depth'] = depth
            elem['_parent'] = parent
            elem['_child_count'] = len(elem.get('children', []))
            
            self.flat_elements.append(elem)
            
            # 递归处理子元素
            if elem.get('children'):
                self._flatten_elements(elem['children'], depth + 1, elem)
    
    # ==================== 维度 1：语义类名分析 ====================
    
    def analyze_semantic_classname(self, className: str) -> Tuple[float, str, str]:
        """
        分析类名的语义特征

        参数:
            className: CSS 类名

        返回:
            (得分, 组件类型, 建议组件名前缀)
        """
        if not className:
            return 0.0, 'unknown', ''

        best_score = 0.0
        best_type = 'unknown'
        best_prefix = ''

        # 特殊规则: 以 -card 或 _card 结尾的类名优先识别为 card 类型
        if re.search(r'[-_]card$', className, re.IGNORECASE):
            best_score = 0.95
            best_type = 'card'
            best_prefix = 'Card'

        for pattern, info in SEMANTIC_PATTERNS.items():
            if re.match(pattern, className, re.IGNORECASE):
                score = info['score']
                # 根据匹配质量调整分数
                if score > best_score:
                    best_score = score
                    best_type = info['type']
                    best_prefix = info['prefix']

        return best_score, best_type, best_prefix
    
    def generate_component_name(self, className: str, prefix: str, semantic_type: str) -> str:
        """
        生成 PascalCase 组件名

        参数:
            className: CSS 类名
            prefix: 建议前缀
            semantic_type: 语义类型

        返回:
            PascalCase 格式的组件名
        """
        if not className:
            return 'Component'

        # 移除常见前缀和后缀，避免重复
        clean_name = className
        for pattern in SEMANTIC_PATTERNS.keys():
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)

        # 移除与语义类型重复的后缀（如 card 类型名称中已包含 Card）
        if semantic_type == 'card':
            clean_name = re.sub(r'[-_]?card$', '', clean_name, flags=re.IGNORECASE)
        elif semantic_type == 'button':
            clean_name = re.sub(r'[-_]?btn$', '', clean_name, flags=re.IGNORECASE)

        # 转换为 PascalCase
        parts = re.split(r'[-_]', clean_name)
        pascal_parts = [p.capitalize() for p in parts if p]

        # 组合前缀和名称，避免重复前缀
        if prefix and pascal_parts:
            combined = prefix + ''.join(pascal_parts)
            # 检查是否重复（如 CardCard）
            if combined == prefix + prefix:
                return prefix
            return combined
        elif prefix:
            return prefix
        elif pascal_parts:
            return ''.join(pascal_parts)
        else:
            return prefix if prefix else 'Component'
    
    # ==================== 维度 2：DOM 结构分析 ====================
    
    def analyze_dom_structure(self, element: Dict) -> Tuple[float, str]:
        """
        分析 DOM 结构特征
        
        参数:
            element: 元素字典
            
        返回:
            (得分, 原因描述)
        """
        score = 0.0
        reasons = []
        
        children = element.get('children', [])
        child_count = len([c for c in children if c.get('tag')])  # 只计算实际元素
        
        # 规则 1：包裹多个子元素的容器（容器类组件高价值）
        if child_count >= 6:
            score += 0.5  # 高分值奖励大容器
            reasons.append("包裹{}个子元素".format(child_count))
        elif child_count >= 4:
            score += 0.35
            reasons.append("包裹{}个子元素".format(child_count))
        elif child_count >= 3:
            score += 0.25
            reasons.append("包裹{}个子元素".format(child_count))
        
        # 规则 2：嵌套深度
        depth = element.get('_depth', 0)
        if depth >= 2:
            score += 0.05
            reasons.append("嵌套深度{}".format(depth))
        
        # 规则 3：包含多种类型子元素
        child_types = set()
        for child in children:
            if child.get('className'):
                _, child_type, _ = self.analyze_semantic_classname(child['className'])
                child_types.add(child_type)
        
        if len(child_types) >= 3:
            score += 0.15
            reasons.append("包含{}种语义类型".format(len(child_types)))
        
        reason = "、".join(reasons) if reasons else "无特殊结构"
        return min(score, 0.6), reason  # 提高上限，大容器组件值得高分
    
    # ==================== 维度 3：重复模式检测 ====================
    
    def detect_duplicate_patterns(self) -> Dict[str, List[Dict]]:
        """
        检测重复的模式（相似类名前缀的元素组）
        
        返回:
            模式分组字典
        """
        patterns = defaultdict(list)
        
        for elem in self.flat_elements:
            className = elem.get('className', '')
            if not className:
                continue
            
            # 提取前缀
            for pattern in SEMANTIC_PATTERNS.keys():
                match = re.match(pattern, className, re.IGNORECASE)
                if match:
                    prefix = match.group(0).rstrip('-_')
                    patterns[prefix].append(elem)
                    break
        
        return dict(patterns)
    
    def analyze_duplicates(self, element: Dict, patterns: Dict[str, List[Dict]]) -> Tuple[float, str]:
        """
        分析元素的重复模式得分
        
        参数:
            element: 当前元素
            patterns: 重复模式字典
            
        返回:
            (得分, 原因)
        """
        className = element.get('className', '')
        if not className:
            return 0.0, ""
        
        # 检查是否属于某个重复模式
        for prefix, elems in patterns.items():
            if len(elems) >= 2:
                for elem in elems:
                    if elem.get('className') == className:
                        # 如果该类名属于一个重复模式组
                        if len(elems) >= 5:
                            return 0.2, "属于高重复模式 '{}' ({}个)".format(prefix, len(elems))
                        elif len(elems) >= 3:
                            return 0.15, "属于重复模式 '{}' ({}个)".format(prefix, len(elems))
                        else:
                            return 0.1, "属于相似模式 '{}'".format(prefix)
        
        return 0.0, ""
    
    # ==================== 维度 4：位置分析 ====================
    
    def analyze_position(self, className: str) -> Tuple[float, str]:
        """
        基于 CSS 位置推断组件位置（Header/Footer等）
        
        参数:
            className: CSS 类名
            
        返回:
            (得分, 位置描述)
        """
        if not className or className not in self.css_map:
            return 0.0, ""
        
        css_props = self.css_map[className].get('properties', {})
        
        # 获取位置信息
        top = css_props.get('top', '')
        bottom = css_props.get('bottom', '')
        left = css_props.get('left', '')
        
        score = 0.0
        position_desc = ""
        
        # 解析数值
        def parse_px(value):
            if not value:
                return None
            match = re.match(r'(\d+(?:\.\d+)?)', str(value))
            return float(match.group(1)) if match else None
        
        top_val = parse_px(top)
        bottom_val = parse_px(bottom)
        
        # Header 检测：top 较小
        if top_val is not None and top_val < 100:
            score = 0.15
            position_desc = "顶部区域 (top: {}px)".format(int(top_val))
            
            # 检查是否已在类名中体现
            if any(kw in className.lower() for kw in ['header', 'top', 'nav']):
                score = 0.0  # 已经通过语义类名计分，不重复计
                position_desc = ""
        
        # Footer 检测：或者没有 top 但有 bottom
        elif bottom_val is not None:
            score = 0.15
            position_desc = "底部区域 (bottom: {}px)".format(int(bottom_val))
            
            if 'footer' in className.lower() or 'bottom' in className.lower():
                score = 0.0
                position_desc = ""
        
        return score, position_desc
    
    # ==================== 综合评分算法 ====================
    
    def calculate_score(self, element: Dict) -> Tuple[float, Dict[str, Any]]:
        """
        计算元素的综合拆分评分
        
        参数:
            element: 元素字典
            
        返回:
            (总得分, 详细评分信息)
        """
        className = element.get('className', '')
        
        # 维度 1：语义类名（权重 50%）- 最重要
        semantic_score, semantic_type, prefix = self.analyze_semantic_classname(className)
        weighted_semantic = semantic_score * 0.5
        
        # 维度 2：DOM 结构（权重 35%）- 容器类组件很重要
        structure_score, structure_reason = self.analyze_dom_structure(element)
        weighted_structure = structure_score * 0.35
        
        # 维度 3：重复模式（权重 10%）- 辅助参考
        patterns = self.detect_duplicate_patterns()
        duplicate_score, duplicate_reason = self.analyze_duplicates(element, patterns)
        weighted_duplicate = duplicate_score * 0.1
        
        # 维度 4：位置分析（权重 5%）- 轻微影响
        position_score, position_desc = self.analyze_position(className)
        weighted_position = position_score * 0.05
        
        # 计算总分
        total_score = weighted_semantic + weighted_structure + weighted_duplicate + weighted_position

        # 额外奖励：语义明确的容器组件（如 card 且有多个子元素）
        child_count = len([c for c in element.get('children', []) if c.get('tag')])
        if semantic_type in ['card', 'modal', 'dialog', 'form'] and child_count >= 4:
            total_score += 0.15  # 高价值容器奖励

        total_score = min(total_score, 1.0)
        
        # 构建评分详情
        score_details = {
            'semantic': {
                'raw': semantic_score,
                'weighted': weighted_semantic,
                'type': semantic_type,
                'prefix': prefix
            },
            'structure': {
                'raw': structure_score,
                'weighted': weighted_structure,
                'reason': structure_reason
            },
            'duplicate': {
                'raw': duplicate_score,
                'weighted': weighted_duplicate,
                'reason': duplicate_reason
            },
            'position': {
                'raw': position_score,
                'weighted': weighted_position,
                'desc': position_desc
            }
        }
        
        return total_score, score_details
    
    # ==================== 主分析函数 ====================
    
    def analyze(self) -> Dict[str, Any]:
        """
        执行完整的组件拆分分析
        
        返回:
            分析结果字典
        """
        candidates = []
        
        for elem in self.flat_elements:
            className = elem.get('className', '')
            if not className:
                continue
            
            # 计算评分
            score, details = self.calculate_score(elem)
            
            # 只保留有价值的候选（score > 0.3）
            if score < 0.3:
                continue
            
            # 生成建议名称
            suggested_name = self.generate_component_name(
                className,
                details['semantic']['prefix'],
                details['semantic']['type']
            )
            
            # 构建原因描述
            reasons = []
            if details['semantic']['raw'] > 0:
                reasons.append("语义类名 ({})".format(details['semantic']['type']))
            if details['structure']['raw'] > 0:
                reasons.append(details['structure']['reason'])
            if details['duplicate']['raw'] > 0:
                reasons.append(details['duplicate']['reason'])
            if details['position']['raw'] > 0:
                reasons.append(details['position']['desc'])
            
            # 查找行号范围
            line_start, line_end = self._find_element_lines(elem)
            
            candidate = {
                'className': className,
                'suggested_name': suggested_name,
                'score': round(score, 2),
                'score_details': {
                    'semantic': round(details['semantic']['weighted'], 3),
                    'structure': round(details['structure']['weighted'], 3),
                    'duplicate': round(details['duplicate']['weighted'], 3),
                    'position': round(details['position']['weighted'], 3)
                },
                'reason': " + ".join(reasons) if reasons else "综合评分",
                'line_start': line_start,
                'line_end': line_end,
                'child_count': elem.get('_child_count', 0),
                'depth': elem.get('_depth', 0)
            }
            
            candidates.append(candidate)
        
        # 按得分降序排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # 去重：相同 suggested_name 只保留得分最高的
        seen_names = set()
        unique_candidates = []
        for cand in candidates:
            if cand['suggested_name'] not in seen_names:
                seen_names.add(cand['suggested_name'])
                unique_candidates.append(cand)
        
        # 计算汇总统计
        high_confidence = len([c for c in unique_candidates if c['score'] >= 0.8])
        medium_confidence = len([c for c in unique_candidates if 0.5 <= c['score'] < 0.8])
        
        self.candidates = unique_candidates
        
        return {
            'candidates': unique_candidates,
            'summary': {
                'total_elements': len(self.flat_elements),
                'candidates_count': len(unique_candidates),
                'high_confidence': high_confidence,
                'medium_confidence': medium_confidence,
                'patterns_detected': list(self.detect_duplicate_patterns().keys())
            }
        }
    
    def _find_element_lines(self, element: Dict) -> Tuple[int, int]:
        """
        估算元素在源代码中的行号范围
        
        这是一个简化实现，实际应该用 AST 或更复杂的匹配
        
        返回:
            (开始行号, 结束行号)
        """
        # 由于我们没有原始源代码映射，使用深度估算
        depth = element.get('_depth', 0)
        child_count = element.get('_child_count', 0)
        
        # 简化估算：基础行号 + 深度偏移
        base_line = 6 + depth * 2  # 从第6行开始（跳过 import）
        
        if child_count > 0:
            end_line = base_line + child_count + 2
        else:
            end_line = base_line + 1
        
        return base_line, end_line


# ==================== 便捷函数 ====================

def analyze(element_tree: List[Dict], css_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析元素树，返回候选拆分点
    
    参数:
        element_tree: JSX 解析后的元素树
        css_map: CSS 解析后的样式映射
        
    返回:
        分析结果字典
        
    示例:
        >>> result = analyze(element_tree, css_map)
        >>> print(json.dumps(result, indent=2, ensure_ascii=False))
    """
    analyzer = SplitAnalyzer(element_tree, css_map)
    return analyzer.analyze()


def analyze_component_dir(component_dir: str) -> Dict[str, Any]:
    """
    分析组件目录（包含 index.jsx 和 index.module.css）
    
    参数:
        component_dir: 组件目录路径
        
    返回:
        分析结果字典
    """
    # 查找 JSX 和 CSS 文件
    jsx_file = None
    css_file = None
    
    for fname in os.listdir(component_dir):
        if fname.endswith('.jsx') or fname.endswith('.tsx'):
            jsx_file = os.path.join(component_dir, fname)
        elif fname.endswith('.module.css') or fname.endswith('.module.scss'):
            css_file = os.path.join(component_dir, fname)
    
    if not jsx_file:
        raise FileNotFoundError("未找到 JSX/TSX 文件在: {}".format(component_dir))
    
    # 解析 JSX
    element_tree = parse_jsx_file(jsx_file)
    
    # 解析 CSS（如果存在）
    css_map = {}
    if css_file and os.path.exists(css_file):
        css_map = parse_css(css_file)
    
    # 执行分析
    return analyze(element_tree, css_map)


# ==================== CLI 接口 ====================

def print_analysis_result(result: Dict[str, Any], verbose: bool = False):
    """
    打印分析结果
    
    参数:
        result: 分析结果字典
        verbose: 是否显示详细信息
    """
    summary = result['summary']
    candidates = result['candidates']
    
    print("\n" + "=" * 60)
    print("代码拆分分析报告")
    print("=" * 60)
    
    # 汇总信息
    print("\n[汇总统计]")
    print("  总元素数: {}".format(summary['total_elements']))
    print("  候选拆分点: {}".format(summary['candidates_count']))
    print("  高置信度 (>=0.8): {}".format(summary['high_confidence']))
    print("  中等置信度 (0.5-0.8): {}".format(summary['medium_confidence']))
    
    if summary['patterns_detected']:
        print("\n  检测到的模式: {}".format(", ".join(summary['patterns_detected'])))
    
    # 候选列表
    if not candidates:
        print("\n[!] 未检测到高价值拆分点")
        return
    
    print("\n" + "-" * 60)
    print("候选拆分点（按置信度排序）")
    print("-" * 60)
    
    for i, cand in enumerate(candidates[:10], 1):  # 最多显示10个
        if cand['score'] >= 0.8:
            confidence = "[HIGH]"
        elif cand['score'] >= 0.5:
            confidence = "[MED]"
        else:
            confidence = "[LOW]"
        print("\n{}. {} {} -> {}".format(i, confidence, cand['className'], cand['suggested_name']))
        print("   置信度: {}".format(cand['score']))
        print("   原因: {}".format(cand['reason']))
        
        if verbose:
            print("   子元素数: {} | 嵌套深度: {}".format(cand['child_count'], cand['depth']))
            print("   评分详情:")
            for key, val in cand['score_details'].items():
                if val > 0:
                    print("     - {}: {}".format(key, val))
    
    print("\n" + "=" * 60)


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='代码拆分分析器 - 智能识别可拆分的组件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析组件目录
  python analyzer.py verify-flow/verify-030/react-component/
  
  # 显示详细信息
  python analyzer.py verify-flow/verify-030/react-component/ -v
  
  # 输出 JSON 格式
  python analyzer.py verify-flow/verify-030/react-component/ --json
  
  # 分别指定 JSX 和 CSS 文件
  python analyzer.py --jsx file.jsx --css file.module.css
        """
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        help='组件目录路径（包含 index.jsx 和 index.module.css）'
    )
    parser.add_argument(
        '--jsx',
        help='JSX 文件路径（与 --css 一起使用）'
    )
    parser.add_argument(
        '--css',
        help='CSS 文件路径（与 --jsx 一起使用）'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='输出 JSON 格式'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出结果到文件'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=0.3,
        help='最小置信度阈值（默认 0.3）'
    )
    
    args = parser.parse_args()
    
    try:
        # 确定输入方式
        if args.jsx and args.css:
            # 分别指定文件
            element_tree = parse_jsx_file(args.jsx)
            css_map = parse_css(args.css)
            result = analyze(element_tree, css_map)
        elif args.path:
            # 目录模式
            result = analyze_component_dir(args.path)
        else:
            parser.print_help()
            sys.exit(1)
        
        # 过滤低分候选
        if args.min_score > 0.3:
            result['candidates'] = [
                c for c in result['candidates'] 
                if c['score'] >= args.min_score
            ]
            result['summary']['candidates_count'] = len(result['candidates'])
        
        # 输出结果
        if args.json:
            output = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print("结果已保存到: {}".format(args.output))
            else:
                print(output)
        else:
            print_analysis_result(result, verbose=args.verbose)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print("\n结果已保存到: {}".format(args.output))
    
    except FileNotFoundError as e:
        print("错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("错误: {}".format(e), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
