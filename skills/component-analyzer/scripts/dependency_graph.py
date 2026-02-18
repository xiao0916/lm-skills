# -*- coding: utf-8 -*-
"""
依赖图构建器模块

用于扫描目录收集组件，构建组件间依赖关系图
"""

import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any


def collect_components(directory: str) -> List[Dict[str, Any]]:
    """
    扫描目录收集所有 .jsx 文件
    
    Args:
        directory: 要扫描的目录路径
        
    Returns:
        组件列表，每个组件包含 id、file、type 等信息
    """
    components = []
    component_id_map = {}  # 用于快速查找组件名到文件的映射
    
    # 递归扫描所有 .jsx 文件
    for root, dirs, files in os.walk(directory):
        # 跳过 node_modules 和隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
        
        for file in files:
            if file.endswith('.jsx'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)
                
                # 从文件名提取组件名（去除扩展名）
                component_name = os.path.splitext(file)[0]
                # 处理 index.jsx 情况，使用父目录名
                if component_name == 'index':
                    parent_dir = os.path.basename(os.path.dirname(file_path))
                    component_name = parent_dir
                
                component_info = {
                    'id': component_name,
                    'file': relative_path,
                    'type': 'component',  # 默认类型，后续会根据依赖关系调整
                    'absolute_path': file_path
                }
                components.append(component_info)
                component_id_map[component_name] = relative_path
    
    # 重新遍历确定组件类型（需要完整的 component_id_map）
    for component in components:
        component['type'] = get_component_type(component['absolute_path'], components)
    
    return components


def extract_imports(file_path: str) -> List[str]:
    """
    从 JSX 文件中提取 import 的组件名称
    
    Args:
        file_path: JSX 文件路径
        
    Returns:
        导入的组件名称列表
    """
    imports = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return imports
    
    # 匹配 ES6 import 语句: import Component from './path'
    # 匹配命名导入: import { Component1, Component2 } from './path'
    import_patterns = [
        # import Component from './path'
        r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
        # import { Component1, Component2 } from './path'
        r'import\s*{([^}]+)}\s*from\s*[\'"]([^\'"]+)[\'"]',
        # import * as Name from './path'
        r'import\s*\*\s+as\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
    ]
    
    # 处理默认导入
    for match in re.finditer(import_patterns[0], content):
        component_name = match.group(1)
        import_path = match.group(2)
        # 只处理相对路径导入（本地组件）
        if import_path.startswith('.') and not component_name.startswith('_'):
            imports.append(component_name)
    
    # 处理命名导入
    for match in re.finditer(import_patterns[1], content):
        named_imports = match.group(1)
        import_path = match.group(2)
        if import_path.startswith('.'):
            # 解析命名导入列表
            for name in re.finditer(r'(\w+)(?:\s+as\s+\w+)?', named_imports):
                component_name = name.group(1)
                if not component_name.startswith('_'):
                    imports.append(component_name)
    
    return imports


def build_dependency_graph(components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    构建组件间依赖关系图
    
    Args:
        components: 组件列表
        
    Returns:
        依赖图，包含 nodes 和 edges
    """
    # 构建组件名到组件信息的映射
    component_map = {comp['id']: comp for comp in components}
    
    nodes = []
    edges = []
    
    # 创建节点
    for component in components:
        node = {
            'id': component['id'],
            'file': component['file'],
            'type': component['type']
        }
        nodes.append(node)
    
    # 创建边（依赖关系）
    for component in components:
        absolute_path = component.get('absolute_path')
        if not absolute_path or not os.path.exists(absolute_path):
            continue
        
        # 提取该文件导入的所有组件
        imported_names = extract_imports(absolute_path)
        
        for imported_name in imported_names:
            # 检查导入的组件是否在已收集的组件列表中
            if imported_name in component_map:
                edge = {
                    'from': component['id'],
                    'to': imported_name,
                    'type': 'import'
                }
                edges.append(edge)
    
    return {
        'nodes': nodes,
        'edges': edges
    }


def detect_circular_dependencies(graph: Dict[str, Any]) -> List[List[str]]:
    """
    检测依赖图中的循环依赖
    
    Args:
        graph: 依赖图，包含 nodes 和 edges
        
    Returns:
        循环依赖列表，每个循环是一个组件 ID 列表
    """
    # 构建邻接表
    adjacency = {}
    for node in graph.get('nodes', []):
        adjacency[node['id']] = []
    
    for edge in graph.get('edges', []):
        from_node = edge.get('from')
        to_node = edge.get('to')
        if from_node in adjacency and to_node in adjacency:
            adjacency[from_node].append(to_node)
    
    # 使用 DFS 检测循环
    cycles = []
    visited = set()
    recursion_stack = set()
    path = []
    
    def dfs(node: str, path_stack: List[str]) -> None:
        visited.add(node)
        recursion_stack.add(node)
        path_stack.append(node)
        
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path_stack)
            elif neighbor in recursion_stack:
                # 发现循环
                cycle_start = path_stack.index(neighbor)
                cycle = path_stack[cycle_start:] + [neighbor]
                # 标准化循环（从最小元素开始）
                min_idx = cycle.index(min(cycle[:-1]))
                normalized_cycle = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
                if normalized_cycle not in cycles:
                    cycles.append(normalized_cycle)
        
        path_stack.pop()
        recursion_stack.remove(node)
    
    for node in adjacency:
        if node not in visited:
            dfs(node, [])
    
    return cycles


def get_component_type(file_path: str, components: List[Dict[str, Any]]) -> str:
    """
    判断组件类型（entry/component）
    
    Args:
        file_path: 文件路径
        components: 所有组件的列表
        
    Returns:
        组件类型：'entry' 或 'component'
    """
    # 构建组件名到文件的映射
    component_files = {comp['id']: comp['file'] for comp in components}
    
    # 检查该文件是否导入其他组件
    imported = extract_imports(file_path)
    
    # 检查导入的组件是否在已收集的组件中
    has_local_imports = any(
        imp in component_files for imp in imported
    )
    
    # 如果导入了其他本地组件，则为入口点
    if has_local_imports:
        return 'entry'
    
    # 检查文件名是否为常见的入口文件名
    file_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_name)[0]
    
    entry_names = {'App', 'Main', 'Index', 'app', 'main', 'index'}
    if base_name in entry_names:
        return 'entry'
    
    return 'component'


def find_entry_point(components: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    查找入口点（最顶层的组件）
    
    入口点特征：
    1. 导入其他组件
    2. 不被其他组件导入
    
    Args:
        components: 组件列表
        
    Returns:
        入口点组件信息，如果未找到则返回 None
    """
    if not components:
        return None
    
    # 构建依赖图
    graph = build_dependency_graph(components)
    
    # 统计每个组件被导入的次数
    imported_count = {comp['id']: 0 for comp in components}
    for edge in graph.get('edges', []):
        to_node = edge.get('to')
        if to_node in imported_count:
            imported_count[to_node] += 1
    
    # 查找不被导入但导入他人的组件（入口点）
    entry_candidates = []
    for component in components:
        comp_id = component['id']
        # 不被其他组件导入
        if imported_count[comp_id] == 0:
            # 检查是否导入其他组件
            imported = extract_imports(component.get('absolute_path', ''))
            component_ids = {c['id'] for c in components}
            has_imports = any(imp in component_ids for imp in imported)
            
            if has_imports or component.get('type') == 'entry':
                entry_candidates.append(component)
    
    # 返回第一个找到的入口点
    if entry_candidates:
        return entry_candidates[0]
    
    # 如果没有明确的入口点，返回类型为 entry 的第一个组件
    for component in components:
        if component.get('type') == 'entry':
            return component
    
    # 最后返回第一个组件
    return components[0] if components else None


def analyze_directory(directory: str) -> Dict[str, Any]:
    """
    分析目录，构建完整的依赖图
    
    Args:
        directory: 要分析的目录路径
        
    Returns:
        完整的分析结果，包括节点、边、循环依赖和入口点
    """
    # 收集组件
    components = collect_components(directory)
    
    if not components:
        return {
            'nodes': [],
            'edges': [],
            'cycles': [],
            'entry_point': None
        }
    
    # 构建依赖图
    graph = build_dependency_graph(components)
    
    # 检测循环依赖
    cycles = detect_circular_dependencies(graph)
    
    # 查找入口点
    entry_point = find_entry_point(components)
    
    return {
        'nodes': graph['nodes'],
        'edges': graph['edges'],
        'cycles': cycles,
        'entry_point': entry_point
    }


if __name__ == '__main__':
    import json
    
    # 测试代码
    test_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'test-skill')
    
    if os.path.exists(test_dir):
        result = analyze_directory(test_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"测试目录不存在: {test_dir}")
