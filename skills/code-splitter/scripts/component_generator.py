#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
组件生成器 - 基于分析结果生成拆分后的 React 组件

功能：
- 根据分析结果生成独立的 React 组件文件
- 生成对应的 CSS Module 样式文件
- 生成入口 App 组件整合所有子组件
- 支持 CLI 调用

作者：AI Assistant
创建日期：2026-02-13
"""

import os
import re
import json
import shutil
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 导入解析器和分析器
try:
    from analyzer import analyze_component_dir, SplitAnalyzer, analyze
    from jsx_parser import parse_jsx_file, JSXParser
    from css_parser import parse_css
except ImportError:
    # 添加当前目录到路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from analyzer import analyze_component_dir, SplitAnalyzer, analyze
    from jsx_parser import parse_jsx_file, JSXParser
    from css_parser import parse_css


def to_pascal_case(name: str) -> str:
    """
    将类名转换为 PascalCase 格式
    
    参数:
        name: 原始类名（如 daily-card, btn-primary）
        
    返回:
        PascalCase 格式的名称（如 DailyCard, BtnPrimary）
    """
    # 移除常见前缀
    name = re.sub(r'^(rs|btn|card|icon|text|title|header|footer|nav|frame|layout|list|item|form|input|modal|dialog|daily|date)[-_]', '', name, flags=re.IGNORECASE)
    
    # 分割并转换
    parts = re.split(r'[-_]', name)
    return ''.join(part.capitalize() for part in parts if part)


def to_camel_case(name: str) -> str:
    """
    将类名转换为 camelCase 格式
    
    参数:
        name: 原始类名
        
    返回:
        camelCase 格式的名称
    """
    pascal = to_pascal_case(name)
    if pascal:
        return pascal[0].lower() + pascal[1:]
    return name


def extract_element_by_classname(element_tree: List[Dict], class_name: str) -> Optional[Dict]:
    """
    从元素树中提取指定 className 的元素
    
    参数:
        element_tree: 元素树列表
        class_name: 目标 className
        
    返回:
        匹配的元素字典，未找到返回 None
    """
    def search_recursive(elements: List[Dict]) -> Optional[Dict]:
        for elem in elements:
            if elem.get('className') == class_name:
                return elem
            if elem.get('children'):
                found = search_recursive(elem['children'])
                if found:
                    return found
        return None
    
    return search_recursive(element_tree)


def collect_class_names(element: Dict) -> List[str]:
    """
    递归收集元素及其子元素的所有 className
    
    参数:
        element: 元素字典
        
    返回:
        className 列表
    """
    class_names = []
    
    if element.get('className'):
        class_names.append(element['className'])
    
    for child in element.get('children', []):
        class_names.extend(collect_class_names(child))
    
    return class_names


def generate_jsx_element(element: Dict, indent: int = 2) -> str:
    """
    递归生成 JSX 元素字符串
    
    参数:
        element: 元素字典
        indent: 缩进级别
        
    返回:
        JSX 字符串
    """
    spaces = '  ' * indent
    
    # 注释节点
    if element.get('comment') and not element.get('tag'):
        return '{}{{/* {} */}}'.format(spaces, element['comment'])
    
    tag = element.get('tag', '')
    class_name = element.get('className', '')
    attributes = element.get('attributes', {})
    self_closing = element.get('selfClosing', False)
    children = element.get('children', [])
    text = element.get('text', '')
    
    if not tag:
        return ''
    
    # 构建属性字符串
    attrs = []
    if class_name:
        attrs.append('className={styles["' + class_name + '"]}')
    
    for key, value in attributes.items():
        if key == 'className':
            continue
        attrs.append('{}="{}"'.format(key, value))
    
    attr_str = ' '.join(attrs)
    
    # 自闭合标签
    if self_closing:
        if attr_str:
            return '{}<{} {} />'.format(spaces, tag, attr_str)
        else:
            return '{}<{} />'.format(spaces, tag)
    
    # 有内容的标签
    lines = []
    if attr_str:
        lines.append('{}<{} {}>'.format(spaces, tag, attr_str))
    else:
        lines.append('{}<{}>'.format(spaces, tag))
    
    # 处理子元素
    has_content = False
    for child in children:
        child_jsx = generate_jsx_element(child, indent + 1)
        if child_jsx:
            lines.append(child_jsx)
            has_content = True
    
    # 处理文本内容
    if text and not has_content:
        lines.append('{}{}'.format('  ' * (indent + 1), text))
    
    lines.append('{}</{}>'.format(spaces, tag))
    
    return '\n'.join(lines)


def copy_component_images(css_rules: Dict[str, Any], source_images_dir: str, component_dir: str) -> List[str]:
    """
    复制组件需要的图片资源
    
    参数:
        css_rules: CSS 规则字典
        source_images_dir: 源 images 目录路径
        component_dir: 目标组件目录
        
    返回:
        复制的图片文件列表
    """
    copied_files = []
    
    # 检查源 images 目录是否存在
    if not os.path.exists(source_images_dir) or not os.path.isdir(source_images_dir):
        return copied_files
    
    # 创建目标 images 目录
    target_images_dir = os.path.join(component_dir, 'images')
    os.makedirs(target_images_dir, exist_ok=True)
    
    # 从 CSS 规则中提取 url() 引用的图片
    image_files = set()
    url_pattern = re.compile(r"url\(['\"]?([^'\"()]+)['\"]?\)")
    
    for class_name, rule in css_rules.items():
        raw_css = rule.get('raw', '')
        matches = url_pattern.findall(raw_css)
        for match in matches:
            # 提取文件名
            if match.endswith('.png') or match.endswith('.jpg') or match.endswith('.jpeg') or match.endswith('.gif') or match.endswith('.svg'):
                filename = os.path.basename(match)
                image_files.add(filename)
    
    # 复制需要的图片
    for filename in image_files:
        source_path = os.path.join(source_images_dir, filename)
        target_path = os.path.join(target_images_dir, filename)
        
        if os.path.exists(source_path):
            try:
                shutil.copy2(source_path, target_path)
                copied_files.append(filename)
            except Exception as e:
                print("警告: 复制图片 {} 失败 - {}".format(filename, e), file=sys.stderr)
    
    return copied_files


def generate_component_props_interface(component_name: str, element: Dict) -> str:
    """
    生成组件 Props 接口定义
    
    参数:
        component_name: 组件名称
        element: 元素字典
        
    返回:
        TypeScript 接口定义字符串
    """
    lines = []
    lines.append('export interface {}Props {{'.format(component_name))
    
    # 基于元素属性推断 Props
    attributes = element.get('attributes', {})
    
    if 'onClick' in attributes or element.get('tag') in ['button', 'a']:
        lines.append('  onClick?: () => void;')
    
    if element.get('tag') in ['img']:
        lines.append('  src?: string;')
        lines.append('  alt?: string;')
    
    # 通用 props
    lines.append('  className?: string;')
    lines.append('  children?: React.ReactNode;')
    
    lines.append('}')
    
    return '\n'.join(lines)


def generate_component(element_data: Dict, css_rules: Dict[str, Any], output_dir: str, source_images_dir: str = None) -> str:
    """
    生成单个 React 组件
    
    参数:
        element_data: 元素数据字典，包含 className, suggested_name 等
        css_rules: CSS 规则字典
        output_dir: 输出目录
        source_images_dir: 源 images 目录路径（可选）
        
    返回:
        生成的组件文件路径
        
    示例:
        >>> element_data = {
        ...     'className': 'daily-card',
        ...     'suggested_name': 'DailyCard',
        ...     'element_tree': {...}
        ... }
        >>> path = generate_component(element_data, css_rules, './components/')
    """
    class_name = element_data.get('className', '')
    component_name = element_data.get('suggested_name', 'Component')
    element_tree = element_data.get('element_tree', [])
    
    if not class_name or not component_name:
        raise ValueError("element_data 必须包含 className 和 suggested_name")
    
    # 创建组件目录
    component_dir = os.path.join(output_dir, to_camel_case(component_name))
    os.makedirs(component_dir, exist_ok=True)
    
    # 复制图片资源
    if source_images_dir and os.path.exists(source_images_dir):
        copied = copy_component_images(css_rules, source_images_dir, component_dir)
        if copied:
            print("  复制了 {} 张图片到 {}".format(len(copied), component_dir))
    
    # 收集所有相关的 className
    if element_tree:
        if isinstance(element_tree, list) and len(element_tree) > 0:
            root_element = element_tree[0]
        else:
            root_element = element_tree
        all_class_names = collect_class_names(root_element)
    else:
        all_class_names = [class_name]
    
    # 生成 JSX 文件
    jsx_path = os.path.join(component_dir, 'index.jsx')
    
    jsx_lines = []
    jsx_lines.append('import React from "react";')
    jsx_lines.append('import styles from "./index.module.css";')
    jsx_lines.append('')
    
    # Props 接口（注释形式）
    jsx_lines.append('/**')
    jsx_lines.append(' * {} 组件'.format(component_name))
    jsx_lines.append(' * ')
    jsx_lines.append(' * Props:')
    jsx_lines.append(' *   - className?: string - 额外的 CSS 类名')
    jsx_lines.append(' *   - children?: React.ReactNode - 子元素')
    jsx_lines.append(' *   - onClick?: () => void - 点击事件处理')
    jsx_lines.append(' */')
    jsx_lines.append('')
    
    # 组件函数
    jsx_lines.append('export default function {}({{'.format(component_name))
    jsx_lines.append('  className = "",')
    jsx_lines.append('  children,')
    jsx_lines.append('  onClick,')
    jsx_lines.append('  ...props')
    jsx_lines.append('}) {')
    jsx_lines.append('  return (')
    
    # 生成 JSX 内容
    if element_tree:
        if isinstance(element_tree, list) and len(element_tree) > 0:
            root_elem = element_tree[0]
        else:
            root_elem = element_tree
        
        # 包装在带 onClick 的 div 中
        jsx_lines.append('    <div')
        jsx_lines.append('      className={`${styles["' + class_name + '"]} ${className}`}')
        jsx_lines.append('      onClick={onClick}')
        jsx_lines.append('      {...props}')
        jsx_lines.append('    >')
        
        # 添加子元素
        for child in root_elem.get('children', []):
            child_jsx = generate_jsx_element(child, 3)
            if child_jsx:
                jsx_lines.append(child_jsx)
        
        jsx_lines.append('    </div>')
    else:
        jsx_lines.append('    <div className={`${styles["' + class_name + '"]} ${className}`}>')
        jsx_lines.append('      {children}')
        jsx_lines.append('    </div>')
    
    jsx_lines.append('  );')
    jsx_lines.append('}')
    jsx_lines.append('')
    
    # 写入 JSX 文件
    with open(jsx_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(jsx_lines))
    
    # 生成 CSS Module 文件
    css_path = os.path.join(component_dir, 'index.module.css')
    
    css_lines = []
    css_lines.append('/* {} 组件样式 */'.format(component_name))
    css_lines.append('/* 生成时间: {} */'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    css_lines.append('')
    
    # 提取相关的 CSS 规则
    for cn in all_class_names:
        if cn in css_rules:
            css_lines.append(css_rules[cn].get('raw', ''))
            css_lines.append('')
    
    # 如果没有匹配的规则，添加基础样式
    if len(css_lines) <= 3:
        css_lines.append('.{} {{'.format(class_name))
        css_lines.append('  /* 基础样式 */')
        css_lines.append('  position: relative;')
        css_lines.append('}')
        css_lines.append('')
    
    # 写入 CSS 文件
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(css_lines))
    
    return component_dir


def generate_app(components: List[Dict], css_rules: Dict[str, Any], output_dir: str) -> str:
    """
    生成入口 App 组件，整合所有子组件
    
    参数:
        components: 组件数据列表
        css_rules: CSS 规则字典
        output_dir: 输出目录
        
    返回:
        生成的 App 组件目录路径
        
    示例:
        >>> components = [
        ...     {'suggested_name': 'DailyCard', 'className': 'daily-card'},
        ...     {'suggested_name': 'Header', 'className': 'header'}
        ... ]
        >>> path = generate_app(components, css_rules, './output/')
    """
    # 创建 App 目录
    app_dir = os.path.join(output_dir, 'app')
    os.makedirs(app_dir, exist_ok=True)
    
    # 生成 App.jsx
    jsx_path = os.path.join(app_dir, 'index.jsx')
    
    jsx_lines = []
    jsx_lines.append('import React from "react";')
    jsx_lines.append('import styles from "./index.module.css";')
    jsx_lines.append('')
    
    # 导入所有子组件
    for comp in components:
        comp_name = comp.get('suggested_name', 'Component')
        import_path = '../' + to_camel_case(comp_name)
        jsx_lines.append('import {} from "{}";'.format(comp_name, import_path))
    
    jsx_lines.append('')
    jsx_lines.append('/**')
    jsx_lines.append(' * App 组件')
    jsx_lines.append(' * ')
    jsx_lines.append(' * 整合所有拆分后的子组件')
    jsx_lines.append(' */')
    jsx_lines.append('')
    jsx_lines.append('export default function App() {')
    jsx_lines.append('  return (')
    jsx_lines.append('    <div className={styles.app}>')
    
    # 添加所有子组件
    for comp in components:
        comp_name = comp.get('suggested_name', 'Component')
        jsx_lines.append('      <{} />'.format(comp_name))
    
    jsx_lines.append('    </div>')
    jsx_lines.append('  );')
    jsx_lines.append('}')
    jsx_lines.append('')
    
    # 写入文件
    with open(jsx_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(jsx_lines))
    
    # 生成 App.module.css
    css_path = os.path.join(app_dir, 'index.module.css')
    
    css_lines = []
    css_lines.append('/* App 组件样式 */')
    css_lines.append('/* 生成时间: {} */'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    css_lines.append('')
    css_lines.append('.app {')
    css_lines.append('  width: 100%;')
    css_lines.append('  min-height: 100vh;')
    css_lines.append('  position: relative;')
    css_lines.append('}')
    css_lines.append('')
    
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(css_lines))
    
    return app_dir


def generate_main_entry(components: List[Dict], output_dir: str, source_jsx_path: str = None,
                        css_rules: Dict[str, Any] = None, source_images_dir: str = None) -> str:
    """
    生成主入口 index.jsx，整合所有子组件
    
    参数:
        components: 组件数据列表
        output_dir: 输出目录
        source_jsx_path: 源 JSX 文件路径（可选，用于保留原结构）
        css_rules: CSS 规则字典（用于提取主入口需要的图片）
        source_images_dir: 源 images 目录路径
        
    返回:
        生成的主入口文件路径
    """
    index_jsx_path = os.path.join(output_dir, 'index.jsx')
    
    # 如果有源文件，先读取保留原结构
    if source_jsx_path and os.path.exists(source_jsx_path):
        with open(source_jsx_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 在原有内容基础上添加导入和替换元素
        lines = original_content.split('\n')
        
        # 添加导入语句（在 import 语句后面）
        import_section_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') and 'from' in line:
                import_section_end = i
        
        # 准备导入语句
        imports_to_add = []
        for comp in components:
            comp_name = comp.get('name', 'Component')
            import_path = './components/' + to_camel_case(comp_name)
            imports_to_add.append('import {} from "{}";'.format(comp_name, import_path))
        
        # 插入导入语句
        new_lines = lines[:import_section_end + 1] + [''] + imports_to_add + [''] + lines[import_section_end + 1:]
        
        # 替换已拆分的元素为组件引用
        content = '\n'.join(new_lines)
        
        # 按 score 降序排列，先处理子元素，再处理父元素
        sorted_components = sorted(components, key=lambda x: x.get('score', 0), reverse=True)
        
        for comp in sorted_components:
            class_name = comp.get('className', '')
            comp_name = comp.get('name', 'Component')
            
            # 替换：<div className={styles["classname"]}...>...</div> 为 <CompName />
            # 或 <div className={styles["classname"]} role="img" ... /> 为 <CompName />
            
            # 匹配带内容的 div
            pattern_with_content = r'<div([^>]*className=\{styles\["' + re.escape(class_name) + r'"\]\}[^>]*>)[\s\S]*?</div>'
            replacement = '<' + comp_name + ' />'
            content = re.sub(pattern_with_content, replacement, content)
            
            # 匹配自闭合的 div
            pattern_self_closing = r'<div([^>]*className=\{styles\["' + re.escape(class_name) + r'"\]\}[^>]*)/?>'
            replacement = '<' + comp_name + ' />'
            content = re.sub(pattern_self_closing, replacement, content)
        
        with open(index_jsx_path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        # 没有源文件，创建新的主入口
        jsx_lines = []
        jsx_lines.append('import React from "react";')
        jsx_lines.append('import styles from "./index.module.css";')
        jsx_lines.append('')
        
        # 导入所有子组件
        for comp in components:
            comp_name = comp.get('suggested_name', 'Component')
            import_path = './components/' + to_camel_case(comp_name)
            jsx_lines.append('import {} from "{}";'.format(comp_name, import_path))
        
        jsx_lines.append('')
        jsx_lines.append('/**')
        jsx_lines.append(' * 主入口组件')
        jsx_lines.append(' * ')
        jsx_lines.append(' * 整合所有拆分后的子组件')
        jsx_lines.append(' */')
        jsx_lines.append('')
        jsx_lines.append('export default function Main() {')
        jsx_lines.append('  return (')
        jsx_lines.append('    <div className={styles.page}>')
        
        # 添加所有子组件
        for comp in components:
            comp_name = comp.get('suggested_name', 'Component')
            jsx_lines.append('      <{} />'.format(comp_name))
        
        jsx_lines.append('    </div>')
        jsx_lines.append('  );')
        jsx_lines.append('}')
        
        with open(index_jsx_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(jsx_lines))
    
    # 复制主入口所需的图片
    if css_rules and source_images_dir and os.path.exists(source_images_dir):
        # 从生成的 index.jsx 中提取所有 className
        with open(index_jsx_path, 'r', encoding='utf-8') as f:
            jsx_content = f.read()
        
        # 提取所有 className
        class_name_pattern = re.compile(r'className=\{styles\["([^"]+)"\]\}')
        class_names = set(class_name_pattern.findall(jsx_content))
        
        # 获取已拆分组件的 className（这些不需要复制到根目录）
        split_class_names = set(comp.get('className', '') for comp in components)
        
        # 找出未拆分的 className
        unsplit_class_names = class_names - split_class_names
        
        # 收集这些未拆分 className 所需的图片
        url_pattern = re.compile(r"url\(['\"]?([^'\"()]+)['\"]?\)")
        images_to_copy = set()
        
        for class_name in unsplit_class_names:
            if class_name in css_rules:
                raw_css = css_rules[class_name].get('raw', '')
                matches = url_pattern.findall(raw_css)
                for match in matches:
                    if match.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                        filename = os.path.basename(match)
                        images_to_copy.add(filename)
        
        # 复制图片到根目录的 images/ 文件夹
        if images_to_copy:
            main_images_dir = os.path.join(output_dir, 'images')
            os.makedirs(main_images_dir, exist_ok=True)
            
            copied_count = 0
            for filename in images_to_copy:
                source_path = os.path.join(source_images_dir, filename)
                target_path = os.path.join(main_images_dir, filename)
                
                if os.path.exists(source_path):
                    try:
                        shutil.copy2(source_path, target_path)
                        copied_count += 1
                    except Exception as e:
                        print("警告: 复制图片 {} 到主入口失败 - {}".format(filename, e), file=sys.stderr)
            
            if copied_count > 0:
                print("  复制了 {} 张图片到主入口 images/".format(copied_count))
    
    return index_jsx_path


def generate_all_components(analysis_result: Dict[str, Any], 
                           element_tree: List[Dict],
                           css_rules: Dict[str, Any],
                           output_dir: str,
                           min_score: float = 0.5,
                           source_images_dir: str = None,
                           input_dir: str = None) -> Dict[str, Any]:
    """
    根据分析结果生成所有组件
    
    参数:
        analysis_result: 分析结果字典
        element_tree: JSX 元素树
        css_rules: CSS 规则字典
        output_dir: 输出目录
        min_score: 最小置信度阈值（默认 0.5）
        source_images_dir: 源 images 目录路径
        input_dir: 输入目录（用于复制源文件）
        
    返回:
        生成结果统计
    """
    candidates = analysis_result.get('candidates', [])
    
    # 按置信度过滤
    candidates = [c for c in candidates if c.get('score', 0) >= min_score]
    
    if not candidates:
        return {
            'success': False,
            'message': '没有可拆分的组件（置信度 >= {}）'.format(min_score),
            'generated': []
        }
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建 components 子目录
    components_dir = os.path.join(output_dir, 'components')
    os.makedirs(components_dir, exist_ok=True)
    
    # 复制源文件到输出目录（如果提供 input_dir）
    if input_dir:
        source_jsx = os.path.join(input_dir, 'index.jsx')
        source_css = os.path.join(input_dir, 'index.module.css')
        
        if os.path.exists(source_jsx):
            shutil.copy2(source_jsx, os.path.join(output_dir, 'index.jsx'))
        if os.path.exists(source_css):
            shutil.copy2(source_css, os.path.join(output_dir, 'index.module.css'))
    
    generated_components = []
    
    print("\n[INFO] 正在拆分置信度 >= {} 的组件...".format(min_score))
    
    # 为每个候选生成组件
    for cand in candidates:
        class_name = cand.get('className', '')
        suggested_name = cand.get('suggested_name', '')
        
        # 查找对应的元素
        element = extract_element_by_classname(element_tree, class_name)
        
        if not element:
            continue
        
        # 准备组件数据
        component_data = {
            'className': class_name,
            'suggested_name': suggested_name,
            'element_tree': [element]
        }
        
        try:
            # 生成组件（传入 source_images_dir）
            component_dir = generate_component(component_data, css_rules, components_dir, source_images_dir)
            generated_components.append({
                'name': suggested_name,
                'className': class_name,
                'path': component_dir,
                'score': cand.get('score', 0)
            })
            print("  [OK] {} (score: {:.2f})".format(suggested_name, cand.get('score', 0)))
        except Exception as e:
            print("警告: 生成组件 {} 失败 - {}".format(suggested_name, e), file=sys.stderr)
    
    # 生成主入口 index.jsx
    if generated_components:
        try:
            # 修改原 index.jsx 使其引用子组件
            main_entry_path = generate_main_entry(
                generated_components,
                output_dir,
                os.path.join(input_dir, 'index.jsx') if input_dir else None,
                css_rules,
                source_images_dir
            )
            print("\n[OK] 主入口已生成: {}".format(main_entry_path))
        except Exception as e:
            print("警告: 生成主入口失败 - {}".format(e), file=sys.stderr)
    
    return {
        'success': True,
        'message': '成功生成 {} 个组件'.format(len(generated_components)),
        'generated': generated_components,
        'output_dir': os.path.abspath(output_dir)
    }


def print_generation_result(result: Dict[str, Any]):
    """
    打印生成结果
    
    参数:
        result: 生成结果字典
    """
    print("\n" + "=" * 60)
    print("组件生成结果")
    print("=" * 60)
    
    if not result.get('success'):
        print("\n[错误] {}".format(result.get('message', '未知错误')))
        return
    
    generated = result.get('generated', [])
    
    print("\n[成功] {}".format(result.get('message', '')))
    print("\n输出目录: {}".format(result.get('output_dir', 'N/A')))
    
    if generated:
        print("\n生成的组件列表:")
        print("-" * 60)
        
        for comp in generated:
            name = comp.get('name', 'Unknown')
            score = comp.get('score', 0)
            path = comp.get('path', '')
            
            # 显示相对路径
            rel_path = os.path.basename(path) if path else 'N/A'
            
            print("  - {} (confidence: {:.2f})".format(name, score))
            print("    路径: {}/".format(rel_path))
        
        print("-" * 60)
    
    print("\n使用方式:")
    print("  import App from './{}/app';".format(os.path.basename(result.get('output_dir', 'output'))))
    print("  // 或导入单个组件")
    
    if len(generated) > 1:
        first_comp = generated[0]
        print("  import {} from './{}/{}';".format(
            first_comp.get('name', 'Component'),
            os.path.basename(result.get('output_dir', 'output')),
            os.path.basename(first_comp.get('path', ''))
        ))
    
    print("\n" + "=" * 60)


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='组件生成器 - 基于分析结果生成拆分后的 React 组件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析并生成组件（完整流程）
  py -3 scripts/component_generator.py --input verify-flow/verify-030/react-component/ --output ./split/
  
  # 只生成高分组件
  py -3 scripts/component_generator.py --input ./my-component/ --output ./split/ --min-score 0.5
  
  # 使用自定义分析结果
  py -3 scripts/component_generator.py --input ./my-component/ --analysis result.json --output ./split/
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入组件目录路径（包含 index.jsx 和 index.module.css）'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='./react-split/',
        help='输出目录路径（默认: ./react-split/）'
    )
    
    parser.add_argument(
        '--analysis',
        help='JSON 格式的分析结果文件路径（可选，默认实时分析）'
    )
    
    parser.add_argument(
        '--min-score',
        type=float,
        default=0.5,
        help='最小置信度阈值（默认 0.5）'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='只显示将要生成的组件，不创建文件'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )
    
    args = parser.parse_args()
    
    # 验证输入路径
    if not os.path.exists(args.input):
        print("错误：输入路径不存在 - {}".format(args.input), file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(args.input):
        print("错误：输入路径必须是目录 - {}".format(args.input), file=sys.stderr)
        sys.exit(1)
    
    # 如果没有指定 --output，默认在与输入目录同级创建 react-split/
    if args.output == './react-split/':
        input_parent = os.path.dirname(os.path.abspath(args.input))
        args.output = os.path.join(input_parent, 'react-split')
    
    try:
        # 加载或执行分析
        if args.analysis:
            # 从文件加载分析结果
            with open(args.analysis, 'r', encoding='utf-8') as f:
                analysis_result = json.load(f)
            
            # 解析 JSX 和 CSS
            element_tree = parse_jsx_file(os.path.join(args.input, 'index.jsx'))
            css_file = os.path.join(args.input, 'index.module.css')
            css_rules = parse_css(css_file) if os.path.exists(css_file) else {}
        else:
            # 执行分析
            if args.verbose:
                print("正在分析目录：{}".format(args.input), file=sys.stderr)
            
            analysis_result = analyze_component_dir(args.input)
            
            # 解析 JSX 和 CSS
            element_tree = parse_jsx_file(os.path.join(args.input, 'index.jsx'))
            css_file = os.path.join(args.input, 'index.module.css')
            css_rules = parse_css(css_file) if os.path.exists(css_file) else {}
        
        # 过滤低分候选
        if args.min_score > 0.3:
            analysis_result['candidates'] = [
                c for c in analysis_result['candidates']
                if c['score'] >= args.min_score
            ]
            analysis_result['summary']['candidates_count'] = len(analysis_result['candidates'])
        
        # Dry-run 模式
        if args.dry_run:
            print("\n[DRY-RUN 模式] 将要生成的组件：")
            print("-" * 60)
            for cand in analysis_result.get('candidates', []):
                print("  - {} (class: .{}, score: {:.2f})".format(
                    cand.get('suggested_name', 'Unknown'),
                    cand.get('className', ''),
                    cand.get('score', 0)
                ))
            print("-" * 60)
            print("\n输出目录: {}".format(os.path.abspath(args.output)))
            print("\n运行以下命令生成实际组件：")
            print("  py -3 scripts/component_generator.py --input {} --output {}".format(
                args.input, args.output
            ))
            sys.exit(0)
        
        # 生成组件
        if args.verbose:
            print("正在生成组件到：{}".format(args.output), file=sys.stderr)
        
        # 计算源 images 目录路径
        source_images_dir = os.path.join(args.input, 'images')
        
        result = generate_all_components(
            analysis_result,
            element_tree,
            css_rules,
            args.output,
            min_score=args.min_score,
            source_images_dir=source_images_dir,
            input_dir=args.input
        )
        
        # 打印结果
        print_generation_result(result)
        
        # 保存生成报告
        report_path = os.path.join(args.output, 'generation-report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        if args.verbose:
            print("\n报告已保存到: {}".format(report_path), file=sys.stderr)
    
    except FileNotFoundError as e:
        print("错误：{}".format(e), file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print("错误：JSON 解析失败 - {}".format(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("错误：{}".format(e), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
