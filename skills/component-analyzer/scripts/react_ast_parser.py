#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
React AST 解析器模块
使用正则表达式解析 React 组件，提取关键信息
兼容 Python 2.7+ 和 Python 3.x
"""

import re
import os
import sys

# Python 2/3 兼容性
PY2 = sys.version_info[0] == 2

if PY2:
    import io
    open = io.open


def parse_imports(content):
    """
    解析 import 语句
    
    支持的格式：
    - import React from 'react'                    (default)
    - import { useState, useEffect } from 'react'   (named)
    - import * as React from 'react'               (namespace)
    - import styles from './index.module.css'      (CSS Module)
    - import './styles.css'                        (side effect)
    """
    imports = []
    
    # 匹配 import 语句
    import_pattern = r"import\s+(.*?)\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]"
    
    for match in re.finditer(import_pattern, content, re.MULTILINE):
        import_info = {"source": ""}
        
        # side effect import
        if match.group(3):
            import_info["source"] = match.group(3)
            import_info["type"] = "side-effect"
        else:
            import_spec = match.group(1).strip()
            import_info["source"] = match.group(2)
            
            # default import
            default_match = re.match(r'^([a-zA-Z_$][a-zA-Z0-9_$]*)\s*$', import_spec)
            if default_match:
                import_info["default"] = default_match.group(1)
            
            # named imports
            named_match = re.search(r'\{\s*([^}]+)\s*\}', import_spec)
            if named_match:
                named_str = named_match.group(1)
                named_items = []
                for item in re.findall(r'([a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s+as\s+([a-zA-Z_$][a-zA-Z0-9_$]*))?', named_str):
                    if item[1]:
                        named_items.append({"name": item[0], "alias": item[1]})
                    else:
                        named_items.append(item[0])
                if named_items:
                    import_info["named"] = named_items
            
            # namespace import
            namespace_match = re.match(r'\*\s+as\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', import_spec)
            if namespace_match:
                import_info["namespace"] = namespace_match.group(1)
        
        imports.append(import_info)
    
    return imports


def parse_exports(content):
    """
    解析 export 语句
    
    支持的格式：
    - export default ComponentName
    - export default function ComponentName() {}
    - export const ComponentName = () => {}
    - export { ComponentName }
    - export * from './module'
    """
    exports = []
    
    # export default
    default_patterns = [
        r'export\s+default\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[;\n]',
        r'export\s+default\s+(?:function\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[\(\{]',
        r'export\s+default\s+(?:function\s*)?\(',
    ]
    
    for pattern in default_patterns:
        match = re.search(pattern, content)
        if match and match.group(1):
            exports.append({"type": "default", "name": match.group(1)})
            break
    
    if not any(e.get("type") == "default" for e in exports):
        anon_match = re.search(r'export\s+default\s+(?:function\s*\(|\(|[a-zA-Z_$])', content)
        if anon_match:
            exports.append({"type": "default", "name": None})
    
    # named exports
    named_var_pattern = r'export\s+(?:const|var|let)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*='
    for match in re.finditer(named_var_pattern, content):
        exports.append({"type": "named", "name": match.group(1)})
    
    # export block
    named_block_pattern = r'export\s+\{([^}]+)\}'
    for match in re.finditer(named_block_pattern, content):
        names_str = match.group(1)
        for name_match in re.finditer(r'([a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s+as\s+([a-zA-Z_$][a-zA-Z0-9_$]*))?', names_str):
            original_name = name_match.group(1)
            alias = name_match.group(2)
            exports.append({
                "type": "named",
                "name": alias if alias else original_name,
                "original_name": original_name if alias else None
            })
    
    # export function
    named_func_pattern = r'export\s+function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\('
    for match in re.finditer(named_func_pattern, content):
        name = match.group(1)
        if not any(e.get("name") == name for e in exports):
            exports.append({"type": "named", "name": name})
    
    # re-export
    reexport_pattern = r"export\s+\*\s+from\s+['\"]([^'\"]+)['\"]"
    for match in re.finditer(reexport_pattern, content):
        exports.append({"type": "re-export", "source": match.group(1)})
    
    return exports


def parse_props(content, component_name):
    """
    解析组件 props
    
    支持的格式：
    - const Component = ({ prop1, prop2 }) => {}
    - const Component = (props) => {}
    - function Component({ prop1, prop2 }) {}
    """
    props = []
    
    # Look for component definition: const ComponentName = (...)
    # Find the pattern and then extract parameters from parentheses
    component_pattern = r'(?:const|var|let)\s+' + re.escape(component_name) + r'\s*=\s*\('
    func_pattern = r'function\s+' + re.escape(component_name) + r'\s*\('
    export_default_pattern = r'export\s+default\s+(?:function\s+)?' + re.escape(component_name) + r'\s*\('
    
    params_str = None
    match = None
    
    # Try patterns in order
    for pattern in [component_pattern, func_pattern, export_default_pattern]:
        match = re.search(pattern, content)
        if match:
            break
    
    if match:
        # Found the pattern, now extract parameters from parentheses
        start_pos = match.end()  # Position right after '('
        
        paren_depth = 1
        end_pos = start_pos
        while end_pos < len(content) and paren_depth > 0:
            char = content[end_pos]
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            end_pos += 1
        
        if paren_depth == 0:
            params_str = content[start_pos:end_pos-1].strip()
    
    if not params_str:
        return props
    
    # destructuring mode
    if params_str.startswith('{') and params_str.endswith('}'):
        inner = params_str[1:-1].strip()
        
        # rest props
        rest_pattern = r'\.\.\.([a-zA-Z_$][a-zA-Z0-9_$]*)'
        for match in re.finditer(rest_pattern, inner):
            props.append(match.group(1))
        
        # normal props
        prop_pattern = r'([a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s*=\s*[^,]+)?'
        for match in re.finditer(prop_pattern, inner):
            prop_name = match.group(1)
            if prop_name not in props:
                props.append(prop_name)
    else:
        props.append(params_str.strip())
    
    return props


def parse_jsx_elements(content):
    """
    提取 JSX 元素（简化版）
    
    提取 return 语句中的 JSX 元素基本信息
    """
    elements = []
    
    # remove comments
    content_no_comments = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content_no_comments = re.sub(r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/', '', content_no_comments)
    
    # find return statement
    return_match = re.search(r'return\s*\(?\s*(<)', content_no_comments)
    if return_match:
        start_pos = return_match.end() - 1
        jsx_content = content_no_comments[start_pos:]
        elements = _extract_jsx_element(jsx_content)
    
    return elements


def _extract_jsx_element(jsx_content, depth=0, max_depth=10):
    """递归提取 JSX 元素"""
    if depth > max_depth:
        return []
    
    elements = []
    tag_pattern = r'<([a-zA-Z][a-zA-Z0-9]*)\s*([^>]*)>'
    self_closing_pattern = r'<([a-zA-Z][a-zA-Z0-9]*)\s*([^/>]*)/>'
    
    pos = 0
    while pos < len(jsx_content):
        # self-closing tag
        self_close_match = re.match(self_closing_pattern, jsx_content[pos:])
        if self_close_match:
            tag_name = self_close_match.group(1)
            attrs_str = self_close_match.group(2)
            
            element_info = {
                "type": tag_name,
                "self_closing": True,
                "attributes": _parse_jsx_attributes(attrs_str)
            }
            
            attrs = element_info["attributes"]
            class_name_val = None
            if isinstance(attrs, dict):
                class_name_val = attrs.get("className") or attrs.get("class")
            if class_name_val and isinstance(class_name_val, str):
                element_info["class_name"] = _extract_class_value(class_name_val)
            
            elements.append(element_info)
            pos += self_close_match.end()
            continue
        
        # open tag
        open_match = re.match(tag_pattern, jsx_content[pos:])
        if open_match:
            tag_name = open_match.group(1)
            attrs_str = open_match.group(2)
            
            element_info = {
                "type": tag_name,
                "self_closing": False,
                "attributes": _parse_jsx_attributes(attrs_str),
                "children": []
            }
            
            attrs = element_info["attributes"]
            class_name_val = None
            if isinstance(attrs, dict):
                class_name_val = attrs.get("className") or attrs.get("class")
            if class_name_val and isinstance(class_name_val, str):
                element_info["class_name"] = _extract_class_value(class_name_val)
            
            # find close tag
            close_pattern = r'</' + re.escape(tag_name) + r'\s*>'
            remaining = jsx_content[pos + open_match.end():]
            close_match = re.search(close_pattern, remaining)
            
            if close_match:
                inner_content = remaining[:close_match.start()]
                element_info["children"] = _extract_jsx_element(inner_content, depth + 1, max_depth)
                pos += open_match.end() + close_match.end() + len(inner_content)
            else:
                pos += open_match.end()
            
            elements.append(element_info)
            continue
        
        pos += 1
    
    return elements


def _parse_jsx_attributes(attrs_str):
    """解析 JSX 属性字符串"""
    attrs = {}
    
    # name="value" or name='value' or name={value}
    attr_pattern = r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|\{([^}]*)\})'
    
    for match in re.finditer(attr_pattern, attrs_str):
        attr_name = match.group(1)
        attr_value = match.group(2) or match.group(3) or match.group(4) or ""
        attrs[attr_name] = attr_value
    
    # boolean attributes
    bool_pattern = r'\s([a-zA-Z_$][a-zA-Z0-9_$]*)(?=\s|$|>)'
    for match in re.finditer(bool_pattern, attrs_str):
        attr_name = match.group(1)
        if attr_name not in attrs:
            attrs[attr_name] = True
    
    return attrs


def _extract_class_value(class_value):
    """提取 className 的值"""
    # styles["root"] or styles['root']
    match = re.search(r'styles\[["\']([^"\']+)', class_value)
    if match:
        return match.group(1)
    
    # styles.root
    match = re.search(r'styles\.([a-zA-Z_$][a-zA-Z0-9_$]*)', class_value)
    if match:
        return match.group(1)
    
    return class_value.strip()


def detect_css_module(imports):
    """检测 CSS Module 引用"""
    for imp in imports:
        source = imp.get("source", "")
        if ".module.css" in source or ".module.scss" in source or ".module.less" in source:
            if "default" in imp:
                return os.path.basename(source)
    return None


def extract_component_name(content, exports):
    """从导出信息中提取组件名称"""
    for exp in exports:
        if exp.get("type") == "default" and exp.get("name"):
            return exp["name"]
    
    for exp in exports:
        if exp.get("type") == "named" and exp.get("name"):
            return exp["name"]
    
    var_match = re.search(r'(?:const|var|let)\s+([A-Z][a-zA-Z0-9]*)\s*=', content)
    if var_match:
        return var_match.group(1)
    
    func_match = re.search(r'function\s+([A-Z][a-zA-Z0-9]*)\s*\(', content)
    if func_match:
        return func_match.group(1)
    
    return None


def parse_react_file(file_path):
    """
    主解析函数 - 解析 React 组件文件
    
    返回：
    {
        "file_path": "...",
        "component_name": "...",
        "imports": [...],
        "exports": [...],
        "props": [...],
        "jsx_elements": [...],
        "css_module_import": "..."
    }
    """
    result = {
        "file_path": file_path,
        "component_name": None,
        "imports": [],
        "exports": [],
        "props": [],
        "jsx_elements": [],
        "css_module_import": None
    }
    
    try:
        if not os.path.exists(file_path):
            result["error"] = "文件不存在: " + file_path
            return result
        
        # read file
        content = None
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, IOError):
                continue
        
        if content is None:
            try:
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
                    if PY2:
                        content = raw_content.decode('utf-8')
                    else:
                        content = raw_content.decode('utf-8')
            except Exception as e:
                result["error"] = "无法读取文件编码: " + str(e)
                return result
        
        # parse
        result["imports"] = parse_imports(content)
        result["exports"] = parse_exports(content)
        result["component_name"] = extract_component_name(content, result["exports"])
        
        if result["component_name"]:
            result["props"] = parse_props(content, result["component_name"])
        
        result["jsx_elements"] = parse_jsx_elements(content)
        result["css_module_import"] = detect_css_module(result["imports"])
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


if __name__ == '__main__':
    # test
    test_content = '''
import React from 'react';
import styles from './index.module.css';

const Bg = ({
  className = '',
  style = {},
  onClick,
  ...rest
}) => {
  return (
    <div
      className={`${styles["root"]} ${className}`}
      style={style}
      onClick={onClick}
      {...rest}
    />
  );
};

export default Bg;
'''
    
    print("Testing parse_imports...")
    imports = parse_imports(test_content)
    for imp in imports:
        print("  Import:", imp)
    
    print("\nTesting parse_exports...")
    exports = parse_exports(test_content)
    for exp in exports:
        print("  Export:", exp)
    
    print("\nTesting parse_props...")
    props = parse_props(test_content, "Bg")
    print("  Props:", props)
    
    print("\nTesting parse_jsx_elements...")
    jsx = parse_jsx_elements(test_content)
    for elem in jsx:
        print("  JSX:", elem)
    
    print("\nTesting detect_css_module...")
    css_module = detect_css_module(imports)
    print("  CSS Module:", css_module)
