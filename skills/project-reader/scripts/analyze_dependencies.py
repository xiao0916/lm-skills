#!/usr/bin/env python3
"""
依赖分析脚本
分析项目中的 import/require 语句，生成模块依赖关系图
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Any


SUPPORTED_EXTENSIONS = {'.js', '.ts', '.jsx', '.tsx', '.vue', '.py'}

IMPORT_PATTERN = re.compile(
    r"^import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+)?['\"]([^'\"]+)['\"]"
)
REQUIRE_PATTERN = re.compile(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
PYTHON_IMPORT_PATTERN = re.compile(r"^(?:from\s+(\S+)\s+import|(?:import\s+)([\w.]+))", re.MULTILINE)
PYTHON_FROM_PATTERN = re.compile(r"^from\s+([\w.]+)\s+import", re.MULTILINE)


def is_supported_file(file_path: Path) -> bool:
    return file_path.suffix in SUPPORTED_EXTENSIONS


def get_module_name(import_path: str, current_file: Path) -> str:
    if import_path.startswith('.'):
        base_dir = current_file.parent
        if import_path.startswith('./'):
            import_path = import_path[2:]
        elif import_path.startswith('../'):
            parts = import_path.split('/')
            up_count = 0
            for i, part in enumerate(parts):
                if part == '..':
                    up_count += 1
                else:
                    break
            target_parts = base_dir.parts
            if up_count < len(target_parts):
                target_parts = target_parts[:-up_count]
            remaining = '/'.join(parts[up_count:])
            if remaining:
                return remaining
            return target_parts[-1] if target_parts else ''
        return import_path.split('/')[0] if '/' in import_path else import_path
    
    return import_path.split('/')[0] if '/' in import_path else import_path


def extract_dependencies(content: str, file_path: Path) -> List[str]:
    dependencies = []
    
    if file_path.suffix == '.py':
        for match in PYTHON_FROM_PATTERN.finditer(content):
            module = match.group(1)
            if module and not module.startswith('_'):
                dependencies.append(module)
        
        for match in PYTHON_IMPORT_PATTERN.finditer(content):
            module = match.group(1) or match.group(2)
            if module and not module.startswith('_'):
                dependencies.append(module)
    else:
        for match in IMPORT_PATTERN.finditer(content):
            import_path = match.group(1)
            if import_path:
                module_name = get_module_name(import_path, file_path)
                if module_name:
                    dependencies.append(module_name)
        
        for match in REQUIRE_PATTERN.finditer(content):
            import_path = match.group(1)
            if import_path:
                module_name = get_module_name(import_path, file_path)
                if module_name:
                    dependencies.append(module_name)
    
    return dependencies


def scan_project(project_path: Path) -> Dict[str, List[str]]:
    dependencies = {}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in 
                   {'node_modules', '__pycache__', '.git', 'dist', 'build', '.venv', 'venv'}]
        
        for file in files:
            file_path = Path(root) / file
            
            if not is_supported_file(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                rel_path = file_path.relative_to(project_path)
                module_key = str(rel_path)
                
                deps = extract_dependencies(content, file_path)
                dependencies[module_key] = deps
                
            except Exception:
                pass
    
    return dependencies


def find_circular_dependencies(dependencies: Dict[str, List[str]]) -> List[List[str]]:
    circular_deps = []
    visited = set()
    rec_stack = set()
    
    def dfs(node: str, path: List[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in dependencies.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor, path.copy()):
                    return True
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                if cycle not in circular_deps:
                    circular_deps.append(cycle)
                return True
        
        rec_stack.remove(node)
        return False
    
    for node in dependencies:
        if node not in visited:
            dfs(node, [])
    
    return circular_deps


def find_core_modules(dependencies: Dict[str, List[str]], top_n: int = 10) -> List[Dict[str, Any]]:
    usage_count: Dict[str, int] = {}
    
    for module, deps in dependencies.items():
        for dep in deps:
            usage_count[dep] = usage_count.get(dep, 0) + 1
    
    sorted_modules = sorted(usage_count.items(), key=lambda x: x[1], reverse=True)
    
    return [
        {"module": module, "dependents": count}
        for module, count in sorted_modules[:top_n]
    ]


def analyze_project(project_path_input: str) -> Dict[str, Any]:
    project_path = Path(project_path_input).resolve()
    
    if not project_path.exists():
        raise ValueError(f"项目路径不存在: {project_path}")
    
    if not project_path.is_dir():
        raise ValueError(f"路径不是目录: {project_path}")
    
    raw_dependencies = scan_project(project_path)
    
    circular_deps = find_circular_dependencies(raw_dependencies)
    
    core_modules = find_core_modules(raw_dependencies)
    
    all_modules = set()
    for module, deps in raw_dependencies.items():
        all_modules.add(module)
        all_modules.update(deps)
    
    result = {
        "project_path": str(project_path),
        "total_files": len(raw_dependencies),
        "total_modules": len(all_modules),
        "dependencies": raw_dependencies,
        "modules": sorted(list(all_modules)),
        "core_modules": core_modules,
        "circular_dependencies": circular_deps,
        "circular_deps_count": len(circular_deps)
    }
    
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_dependencies.py <项目路径>")
        print("示例: python analyze_dependencies.py /path/to/project")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    try:
        result = analyze_project(project_path)
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "project_path": project_path
        }, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
