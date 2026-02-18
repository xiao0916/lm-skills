#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
组件拆分 CLI 入口 - Suggestion Mode（建议模式）

功能：
- 分析 React 组件，识别可拆分的子组件
- 生成 Markdown 格式的拆分建议报告
- 支持 --dry-run 模式（只生成报告，不创建文件）

使用方法：
  # 生成拆分建议报告（输出到 stdout）
  py -3 scripts/split_component.py --input verify-flow/verify-030/react-component/ --dry-run
  
  # 生成报告并保存到文件
  py -3 scripts/split_component.py --input verify-flow/verify-030/react-component/ --dry-run --output report.md

作者：AI Assistant
创建日期：2026-02-13
"""

import sys
import os
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime

# 将 code-splitter/scripts 添加到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_SPLITTER_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), '.claude', 'skills', 'code-splitter', 'scripts')
sys.path.insert(0, CODE_SPLITTER_DIR)

try:
    from analyzer import analyze_component_dir, SplitAnalyzer
    from jsx_parser import parse_jsx_file
    from css_parser import parse_css
except ImportError as e:
    print("错误：无法导入 analyzer 模块。请确保 .claude/skills/code-splitter/scripts/ 目录存在。", file=sys.stderr)
    print("详细错误：{}".format(e), file=sys.stderr)
    sys.exit(1)


def get_confidence_level(score: float) -> tuple:
    """
    根据置信度返回等级和标记
    
    参数:
        score: 置信度分数 (0-1)
        
    返回:
        (等级字符串, 标记字符串)
    """
    if score >= 0.8:
        return ("HIGH", "[HIGH]")
    elif score >= 0.5:
        return ("MEDIUM", "[MEDIUM]")
    else:
        return ("LOW", "[LOW]")


def generate_markdown_report(result: Dict[str, Any], input_path: str) -> str:
    """
    生成 Markdown 格式的拆分建议报告
    
    参数:
        result: analyzer.analyze() 返回的结果字典
        input_path: 输入目录路径
        
    返回:
        Markdown 格式的报告字符串
    """
    summary = result.get('summary', {})
    candidates = result.get('candidates', [])
    
    # 计算平均置信度
    avg_confidence = 0.0
    if candidates:
        avg_confidence = sum(c['score'] for c in candidates) / len(candidates)
    
    # 获取源文件名
    source_file = "index.jsx"
    for fname in os.listdir(input_path) if os.path.isdir(input_path) else []:
        if fname.endswith('.jsx') or fname.endswith('.tsx'):
            source_file = fname
            break
    
    lines = []
    
    # 报告标题
    lines.append("# 组件拆分建议报告")
    lines.append("")
    lines.append("生成时间：{}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    lines.append("")
    
    # 分析摘要
    lines.append("## 分析摘要")
    lines.append("")
    lines.append("- **源文件**：{}".format(source_file))
    lines.append("- **元素数量**：{}".format(summary.get('total_elements', 0)))
    lines.append("- **候选拆分点**：{}".format(summary.get('candidates_count', 0)))
    lines.append("- **高置信度**：{}".format(summary.get('high_confidence', 0)))
    lines.append("- **平均置信度**：{:.2f}".format(avg_confidence))
    lines.append("")
    
    # 拆分建议
    lines.append("## 拆分建议")
    lines.append("")
    lines.append("按置信度排序，建议优先拆分高分组件：")
    lines.append("")
    
    if not candidates:
        lines.append("*未检测到高价值拆分点*")
        lines.append("")
    else:
        for i, cand in enumerate(candidates, 1):
            score = cand.get('score', 0)
            level, badge = get_confidence_level(score)
            suggested_name = cand.get('suggested_name', 'Component')
            class_name = cand.get('className', '')
            reason = cand.get('reason', '综合评分')
            child_count = cand.get('child_count', 0)
            
            lines.append("### {}. {} (confidence: {:.2f}) {}".format(i, suggested_name, score, badge))
            lines.append("")
            lines.append("- **建议名称**：{}".format(suggested_name))
            lines.append("- **原始类名**：`.{}`".format(class_name))
            lines.append("- **理由**：{}".format(reason))
            lines.append("- **子元素数**：{}".format(child_count))
            lines.append("- **风险等级**：{}".format(
                "低" if level == "HIGH" else ("中" if level == "MEDIUM" else "高")
            ))
            
            # 评分详情
            score_details = cand.get('score_details', {})
            if score_details:
                lines.append("- **评分详情**：")
                for key, val in score_details.items():
                    if val > 0:
                        lines.append("  - {}: {:.3f}".format(key, val))
            
            lines.append("")
    
    # 风险提示
    lines.append("## 风险提示")
    lines.append("")
    
    risks = []
    
    # 检测重复按钮
    button_count = sum(1 for c in candidates if 'btn' in c.get('className', '').lower())
    if button_count >= 3:
        risks.append("检测到 {} 个按钮元素，建议抽象为通用 Button 组件".format(button_count))
    
    # 检测低置信度建议
    low_confidence = [c for c in candidates if c.get('score', 0) < 0.5]
    if low_confidence:
        risks.append("有 {} 个低置信度建议，需要人工审核".format(len(low_confidence)))
    
    # 检测深层嵌套
    deep_nested = [c for c in candidates if c.get('depth', 0) >= 4]
    if deep_nested:
        risks.append("检测到 {} 个深层嵌套组件，拆分后可能需要传递多层 props".format(len(deep_nested)))
    
    if risks:
        for risk in risks:
            lines.append("- [WARNING] {}".format(risk))
    else:
        lines.append("- [OK] 未发现明显风险")
    
    lines.append("")
    
    # 检测到的模式
    patterns = summary.get('patterns_detected', [])
    if patterns:
        lines.append("## 检测到的模式")
        lines.append("")
        lines.append("发现以下语义模式（可用于组件命名参考）：")
        lines.append("")
        for pattern in patterns:
            lines.append("- `{}`".format(pattern))
        lines.append("")
    
    # 下一步操作建议
    lines.append("## 下一步")
    lines.append("")
    
    if candidates:
        high_count = summary.get('high_confidence', 0)
        lines.append("根据分析结果，建议：")
        lines.append("")
        if high_count > 0:
            lines.append("1. **优先拆分高置信度组件**（[HIGH]）：共 {} 个".format(high_count))
            lines.append("2. 运行以下命令生成实际组件文件：")
        else:
            lines.append("1. 没有高置信度建议，建议先优化代码结构")
            lines.append("2. 或手动指定组件名称运行：")
        lines.append("")
        lines.append("```bash")
        lines.append("# 生成组件到指定目录")
        lines.append("py -3 scripts/split_component.py \\")
        lines.append("  --input {} \\".format(input_path))
        lines.append("  --output ./split/")
        lines.append("```")
    else:
        lines.append("当前组件暂不适合自动拆分。建议：")
        lines.append("")
        lines.append("1. 检查组件结构是否过于简单")
        lines.append("2. 手动添加语义化 className 以提高识别度")
        lines.append("3. 使用 `--min-score` 降低置信度阈值重新分析")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*报告由组件拆分分析器自动生成*")
    
    return "\n".join(lines)


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description='组件拆分 CLI - 分析 React 组件并生成拆分建议',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # Suggestion Mode - 只生成报告（推荐先运行）
  py -3 scripts/split_component.py --input verify-flow/verify-030/react-component/ --dry-run
  
  # 生成报告并保存到文件
  py -3 scripts/split_component.py --input ./my-component/ --dry-run --output report.md
  
  # 显示详细信息
  py -3 scripts/split_component.py --input ./my-component/ --dry-run -v
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入组件目录路径（包含 index.jsx 和 index.module.css）'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='输出报告文件路径（默认输出到 stdout）'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='建议模式：只生成报告，不创建任何文件'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )
    
    parser.add_argument(
        '--min-score',
        type=float,
        default=0.3,
        help='最小置信度阈值（默认 0.3）'
    )
    
    args = parser.parse_args()
    
    # 验证输入路径
    if not os.path.exists(args.input):
        print("错误：输入路径不存在 - {}".format(args.input), file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(args.input):
        print("错误：输入路径必须是目录 - {}".format(args.input), file=sys.stderr)
        sys.exit(1)
    
    try:
        # 执行分析
        if args.verbose:
            print("正在分析目录：{}".format(args.input), file=sys.stderr)
        
        result = analyze_component_dir(args.input)
        
        # 过滤低分候选
        if args.min_score > 0.3:
            result['candidates'] = [
                c for c in result['candidates'] 
                if c['score'] >= args.min_score
            ]
            result['summary']['candidates_count'] = len(result['candidates'])
        
        # 生成 Markdown 报告
        report = generate_markdown_report(result, args.input)
        
        # 输出报告
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print("[OK] 报告已保存到：{}".format(args.output))
        else:
            print(report)
        
        # 如果是 dry-run 模式，给出提示
        if args.dry_run:
            if args.output:
                print("\n[INFO] 这是一个建议报告（--dry-run 模式），未生成任何组件文件。", file=sys.stderr)
                print("   查看报告后，运行以下命令生成实际组件：", file=sys.stderr)
                print("   py -3 scripts/split_component.py --input {} --output ./split/".format(args.input), file=sys.stderr)
        
        # 返回统计信息
        summary = result['summary']
        if args.verbose:
            print("\n[分析完成]", file=sys.stderr)
            print("  元素总数：{}".format(summary['total_elements']), file=sys.stderr)
            print("  候选组件：{}".format(summary['candidates_count']), file=sys.stderr)
            print("  高置信度：{}".format(summary['high_confidence']), file=sys.stderr)
    
    except FileNotFoundError as e:
        print("错误：{}".format(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("错误：{}".format(e), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
