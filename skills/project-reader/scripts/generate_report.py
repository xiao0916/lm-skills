#!/usr/bin/env python3
"""
报告生成脚本
整合 detect_framework.py、analyze_structure.py、analyze_dependencies.py 的输出，生成 Markdown 报告
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def run_script(script_name: str, project_path: str) -> Dict[str, Any]:
    """运行子脚本并返回 JSON 输出"""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        raise FileNotFoundError(f"脚本不存在: {script_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), project_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return {"error": f"脚本执行失败: {result.stderr}"}
        
        return json.loads(result.stdout)
    
    except subprocess.TimeoutExpired:
        return {"error": "脚本执行超时"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败: {e}"}
    except Exception as e:
        return {"error": f"执行错误: {e}"}


def format_directory_tree(tree: Dict[str, Any], indent: int = 0) -> str:
    """格式化目录树为 Markdown"""
    lines = []
    prefix = "  " * indent
    
    if tree.get("type") == "directory":
        lines.append(f"{prefix}- **{tree.get('name', 'root')}/**")
        
        children = tree.get("children", [])
        for child in children:
            if child.get("type") == "directory":
                if child.get("truncated"):
                    lines.append(f"{prefix}  - {child.get('name', '')}/ (截断)")
                else:
                    lines.extend(format_directory_tree(child, indent + 1).split('\n'))
            else:
                file_type = child.get("file_type", "")
                lines.append(f"{prefix}  - {child.get('name', '')} ({file_type})")
    
    return '\n'.join(lines)


def generate_overview(framework_data: Dict[str, Any], structure_data: Dict[str, Any]) -> str:
    """生成项目概述"""
    lines = []
    lines.append("## 项目概述\n")
    
    # 项目名称
    project_name = structure_data.get("project_name", "未知项目")
    lines.append(f"- **项目名称**: {project_name}")
    
    # 项目路径
    project_path = structure_data.get("project_path", "")
    lines.append(f"- **项目路径**: `{project_path}`")
    
    # 版本
    version = framework_data.get("project_version")
    if version:
        lines.append(f"- **版本**: {version}")
    
    # 描述
    description = framework_data.get("project_description")
    if description:
        lines.append(f"- **描述**: {description}")
    
    # 文件统计
    summary = structure_data.get("summary", {})
    lines.append(f"- **文件类型数**: {summary.get('total_file_types', 0)}")
    lines.append(f"- **关键目录数**: {summary.get('total_key_directories', 0)}")
    lines.append(f"- **配置文件数**: {summary.get('total_config_files', 0)}")
    
    # 依赖数量
    deps_count = len(framework_data.get("dependencies", []))
    lines.append(f"- **依赖数量**: {deps_count}")
    
    return '\n'.join(lines)


def generate_framework_info(framework_data: Dict[str, Any]) -> str:
    """生成框架信息"""
    lines = []
    lines.append("## 框架信息\n")
    
    # 框架
    framework = framework_data.get("framework")
    lines.append(f"- **框架**: {framework if framework else '未检测到'}")
    
    # UI 库
    ui_library = framework_data.get("ui_library")
    lines.append(f"- **UI 库**: {ui_library if ui_library else '未检测到'}")
    
    # 构建工具
    build_tool = framework_data.get("build_tool")
    lines.append(f"- **构建工具**: {build_tool if build_tool else '未检测到'}")
    
    # 包管理器
    package_manager = framework_data.get("package_manager")
    lines.append(f"- **包管理器**: {package_manager if package_manager else '未检测到'}")
    
    # 入口文件
    entry_points = framework_data.get("entry_points", [])
    if entry_points:
        lines.append("\n### 入口文件\n")
        for entry in entry_points:
            lines.append(f"- `{entry}`")
    
    # 脚本命令
    scripts = framework_data.get("scripts", {})
    if scripts:
        lines.append("\n### 可用脚本\n")
        for name, cmd in scripts.items():
            lines.append(f"- `{name}`: {cmd}")
    
    # 依赖列表（只显示前 20 个）
    all_deps = framework_data.get("dependencies", [])
    if all_deps:
        lines.append(f"\n### 依赖列表 (共 {len(all_deps)} 个)\n")
        display_deps = all_deps[:20]
        lines.append("```")
        for dep in display_deps:
            lines.append(f"  {dep}")
        if len(all_deps) > 20:
            lines.append(f"  ... 还有 {len(all_deps) - 20} 个依赖")
        lines.append("```")
    
    return '\n'.join(lines)


def generate_structure_info(structure_data: Dict[str, Any]) -> str:
    """生成目录结构"""
    lines = []
    lines.append("## 目录结构\n")
    
    # 目录树
    directory_tree = structure_data.get("directory_tree", {})
    tree_str = format_directory_tree(directory_tree)
    lines.append("```\n" + tree_str + "\n```")
    
    # 文件类型统计
    file_types = structure_data.get("file_types", {})
    if file_types:
        lines.append("\n### 文件类型分布\n")
        lines.append("| 类型 | 数量 |")
        lines.append("|------|------|")
        for file_type, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {file_type} | {count} |")
    
    # 关键目录
    key_dirs = structure_data.get("key_directories", {})
    if key_dirs:
        lines.append("\n### 关键目录\n")
        lines.append("| 目录 | 状态 |")
        lines.append("|------|------|")
        for name, info in sorted(key_dirs.items()):
            status = "✓ 存在" if info.get("exists") else "✗ 不存在"
            nested = " (嵌套)" if info.get("nested") else ""
            lines.append(f"| `{name}` | {status}{nested} |")
    
    # 配置文件
    config_files = structure_data.get("config_files", [])
    if config_files:
        lines.append("\n### 配置文件\n")
        for cfg in config_files:
            lines.append(f"- `{cfg}`")
    
    return '\n'.join(lines)


def generate_dependency_analysis(deps_data: Dict[str, Any]) -> str:
    """生成依赖分析"""
    lines = []
    lines.append("## 依赖分析\n")
    
    # 统计信息
    lines.append(f"- **扫描文件数**: {deps_data.get('total_files', 0)}")
    lines.append(f"- **模块总数**: {deps_data.get('total_modules', 0)}")
    lines.append(f"- **循环依赖数**: {deps_data.get('circular_deps_count', 0)}")
    
    # 核心模块
    core_modules = deps_data.get("core_modules", [])
    if core_modules:
        lines.append("\n### 核心模块 (按使用频率)\n")
        lines.append("| 模块 | 引用次数 |")
        lines.append("|------|----------|")
        for module in core_modules:
            lines.append(f"| `{module.get('module', '')}` | {module.get('dependents', 0)} |")
    
    # 循环依赖
    circular_deps = deps_data.get("circular_dependencies", [])
    if circular_deps:
        lines.append("\n### 循环依赖\n")
        for cycle in circular_deps[:10]:  # 最多显示 10 个
            cycle_str = " → ".join(cycle[:5])
            if len(cycle) > 5:
                cycle_str += " → ..."
            lines.append(f"- {cycle_str}")
        if len(circular_deps) > 10:
            lines.append(f"- ... 还有 {len(circular_deps) - 10} 个循环依赖")
    
    # 模块列表（部分）
    all_modules = deps_data.get("modules", [])
    if all_modules:
        lines.append(f"\n### 模块列表 (共 {len(all_modules)} 个)\n")
        display_modules = all_modules[:30]
        lines.append("```")
        for module in display_modules:
            lines.append(f"  {module}")
        if len(all_modules) > 30:
            lines.append(f"  ... 还有 {len(all_modules) - 30} 个模块")
        lines.append("```")
    
    return '\n'.join(lines)


def generate_report(project_path: str) -> str:
    """生成完整的 Markdown 报告"""
    lines = []
    
    # 标题
    project_name = Path(project_path).name
    lines.append(f"# 项目分析报告: {project_name}\n")
    lines.append(f"生成时间: {Path(project_path).resolve()}\n")
    lines.append("---\n")
    
    # 运行各个分析脚本
    print("正在运行框架检测...")
    framework_data = run_script("detect_framework.py", project_path)
    
    print("正在分析目录结构...")
    structure_data = run_script("analyze_structure.py", project_path)
    
    print("正在分析依赖关系...")
    deps_data = run_script("analyze_dependencies.py", project_path)
    
    # 检查错误
    errors = []
    if "error" in framework_data:
        errors.append(f"框架检测: {framework_data['error']}")
    if "error" in structure_data:
        errors.append(f"目录结构: {structure_data['error']}")
    if "error" in deps_data:
        errors.append(f"依赖分析: {deps_data['error']}")
    
    if errors:
        lines.append("## 错误信息\n")
        for error in errors:
            lines.append(f"- {error}")
        lines.append("\n---\n")
    
    # 生成各个部分
    lines.append(generate_overview(framework_data, structure_data))
    lines.append("\n\n")
    
    lines.append(generate_framework_info(framework_data))
    lines.append("\n\n")
    
    lines.append(generate_structure_info(structure_data))
    lines.append("\n\n")
    
    lines.append(generate_dependency_analysis(deps_data))
    lines.append("\n\n")
    
    lines.append("---\n")
    lines.append("*报告由 project-reader 技能自动生成*")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="生成项目分析报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_report.py /path/to/project
  python generate_report.py /path/to/project -o report.md
  python generate_report.py /path/to/project --output report.md
        """
    )
    
    parser.add_argument(
        "project_path",
        help="要分析的项目路径"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径 (默认: 输出到标准输出)",
        default=None
    )
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    
    if not project_path.exists():
        print(f"错误: 项目路径不存在: {project_path}", file=sys.stderr)
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"错误: 路径不是目录: {project_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"开始分析项目: {project_path}")
    
    try:
        report = generate_report(str(project_path))
        
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report, encoding="utf-8")
            print(f"\n报告已保存到: {output_path}")
        else:
            print("\n" + report)
    
    except Exception as e:
        print(f"生成报告时出错: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
