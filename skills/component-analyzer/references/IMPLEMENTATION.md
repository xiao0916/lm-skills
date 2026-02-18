# Component Analyzer 实现细节

本文档包含 Component Analyzer 的详细实现信息，供需要深入了解或扩展功能的开发者参考。

## 目录

1. [相似度计算算法](#相似度计算算法)
2. [正则表达式解析模式](#正则表达式解析模式)
3. [数据结构定义](#数据结构定义)
4. [扩展开发指南](#扩展开发指南)

---

## 相似度计算算法

### 综合相似度公式

```
similarity = (props_similarity * 0.4) + (jsx_similarity * 0.4) + (css_similarity * 0.2)
```

### 1. Props 签名相似度 (40%)

**完全匹配**：两个组件的 props 列表完全相同
```python
if set(comp_a['props']) == set(comp_b['props']):
    return 0.4
```

**部分匹配**：计算交集比例
```python
common_props = set(comp_a['props']) & set(comp_b['props'])
all_props = set(comp_a['props']) | set(comp_b['props'])
return (len(common_props) / len(all_props)) * 0.4
```

### 2. JSX 结构相似度 (40%)

使用 Jaccard 相似度计算：

```python
elements_a = set(extract_element_types(comp_a['jsx_elements']))
elements_b = set(extract_element_types(comp_b['jsx_elements']))

intersection = len(elements_a & elements_b)
union = len(elements_a | elements_b)

if union == 0:
    return 0
return (intersection / union) * 0.4
```

### 3. CSS Module 相似度 (20%)

```python
a_uses_css = comp_a.get('css_module_import') is not None
b_uses_css = comp_b.get('css_module_import') is not None

if a_uses_css and b_uses_css:
    return 0.2  # 两者都用
elif not a_uses_css and not b_uses_css:
    return 0.1  # 两者都不用（中性）
else:
    return 0    # 一个用一个不用
```

### 层次聚类算法

使用贪心算法进行聚类：

```python
def group_by_pattern(components, threshold=0.7):
    patterns = []
    assigned = set()
    
    for i, comp_a in enumerate(components):
        if comp_a['component_name'] in assigned:
            continue
        
        pattern = [comp_a]
        
        for j, comp_b in enumerate(components[i+1:], i+1):
            if comp_b['component_name'] in assigned:
                continue
            
            similarity = calculate_similarity(comp_a, comp_b)
            if similarity >= threshold:
                pattern.append(comp_b)
                assigned.add(comp_b['component_name'])
        
        if len(pattern) > 1:
            patterns.append(pattern)
        assigned.add(comp_a['component_name'])
    
    return patterns
```

---

## 正则表达式解析模式

### Import 语句解析

支持多种 import 形式：

```python
IMPORT_PATTERNS = {
    # import React from 'react'
    'default': r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]",
    
    # import { useState, useEffect } from 'react'
    'named': r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]",
    
    # import { Button as Btn } from 'antd'
    'aliased': r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]",
    
    # import * as Utils from './utils'
    'namespace': r"import\s+\*\s+as\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]",
    
    # import './styles.css' (side-effect)
    'side_effect': r"import\s+['\"]([^'\"]+)['\"]"
}
```

### Export 语句解析

```python
EXPORT_PATTERNS = {
    # export default Component
    'default': r"export\s+default\s+(\w+)",
    
    # export { Component }
    'named_block': r"export\s+\{([^}]+)\}",
    
    # export * from './module'
    're_export': r"export\s+\*\s+from\s+['\"]([^'\"]+)['\"]"
}
```

### Props 解析

```python
# const Component = ({ prop1, prop2 }) =>
PROPS_ARROW_FUNCTION = r"const\s+(\w+)\s*=\s*\(\s*\{([^}]*)\}"

# function Component({ prop1, prop2 })
PROPS_FUNCTION_DECLARATION = r"function\s+(\w+)\s*\(\s*\{([^}]*)\}"

# ({ prop1 = defaultValue, prop2, ...rest })
PROPS_WITH_DEFAULTS = r"(\w+)\s*(?:=\s*[^,]+)?"

# ...rest
REST_PROPS = r"\.\.\.(\w+)"
```

### JSX 元素解析

```python
# <div className="xxx">
JSX_OPEN_TAG = r"<(\w+)(?:\s+[^>]*)?>"

# <div />
JSX_SELF_CLOSING = r"<(\w+)(?:\s+[^>]*)?/>"

# className="xxx" or className={'xxx'}
CLASSNAME_ATTR = r"className\s*=\s*(?:['\"]([^'\"]+)['\"]|\{[^}]+\})"
```

---

## 数据结构定义

### 组件信息结构

```python
{
    "file_path": "components/Header/index.jsx",      # 文件路径
    "component_name": "Header",                      # 组件名
    "imports": [                                     # 导入列表
        {
            "source": "react",                       # 来源模块
            "default": "React",                      # 默认导入名
            "named": ["useState", "useEffect"],      # 命名导入列表
            "namespace": None                        # 命名空间导入
        }
    ],
    "exports": [                                     # 导出列表
        {
            "type": "default",                       # 导出类型
            "name": "Header"                         # 导出名称
        }
    ],
    "props": ["title", "onClick", "className"],      # Props 列表
    "jsx_elements": [                                # JSX 元素列表
        {
            "type": "div",                           # 元素类型
            "class_name": "header",                  # 类名
            "attributes": {...},                     # 其他属性
            "children": [...]                        # 子元素
        }
    ],
    "css_module_import": "./index.module.css"       # CSS Module 路径
}
```

### 依赖图结构

```python
{
    "nodes": [                                       # 节点列表
        {
            "id": "App",                             # 组件 ID
            "file": "App.jsx",                       # 文件路径
            "type": "entry"                          # 类型：entry/component
        }
    ],
    "edges": [                                       # 边列表
        {
            "from": "App",                           # 起始节点
            "to": "Header",                          # 目标节点
            "type": "import"                         # 关系类型
        }
    ],
    "cycles": [],                                    # 循环依赖列表
    "entry_point": {                                 # 入口点
        "id": "App",
        "file": "App.jsx"
    }
}
```

### 模式结构

```python
{
    "patterns": [
        {
            "id": "pattern_1",                       # 模式 ID
            "signature": "({ name }) => <div/p>",    # 签名描述
            "components": ["UserCard", "ProductCard"], # 属于该模式的组件
            "similarity": 0.85,                      # 相似度
            "suggestion": "可提取为公共组件"           # 建议
        }
    ],
    "total_components": 10,                          # 组件总数
    "pattern_count": 2,                              # 模式数量
    "threshold": 0.7                                 # 使用的阈值
}
```

### 建议结构

```python
{
    "id": 1,                                         # 建议 ID
    "type": "extract",                               # 类型
    "priority": "high",                              # 优先级
    "target": ["Card", "Modal"],                     # 目标组件
    "description": "...",                            # 描述
    "details": {...},                                # 详细信息
    "code_example": "..."                            # 代码示例
}
```

---

## 扩展开发指南

### 添加新的解析器

如需支持其他框架（如 Svelte、Angular）：

1. 在 `scripts/` 创建新的解析器文件
2. 实现标准接口：

```python
def parse_<framework>_file(file_path):
    """
    解析框架组件文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        dict: 符合组件信息结构的数据
    """
    pass

def extract_<framework>_imports(content):
    """提取导入语句"""
    pass

def extract_<framework>_exports(content):
    """提取导出语句"""
    pass
```

3. 在 `analyze_components.py` 中添加框架支持：

```python
if framework == 'svelte':
    from svelte_parser import parse_svelte_file
    component_info = parse_svelte_file(file_path)
```

### 添加新的建议类型

1. 在 `split_suggester.py` 中添加建议生成函数：

```python
def suggest_new_optimization(pattern):
    """
    生成新的优化建议
    
    Args:
        pattern: 模式信息
        
    Returns:
        dict: 建议对象
    """
    return {
        "id": generate_id(),
        "type": "new_type",
        "priority": calculate_priority(pattern),
        "target": [comp['component_name'] for comp in pattern['components']],
        "description": "建议描述",
        "details": {...},
        "code_example": "..."
    }
```

2. 在 `generate_suggestions()` 中调用：

```python
suggestion = suggest_new_optimization(pattern)
if suggestion:
    suggestions.append(suggestion)
```

### 自定义相似度计算

修改 `pattern_detector.py` 中的 `calculate_similarity()`：

```python
def calculate_similarity(comp_a, comp_b, custom_weights=None):
    """
    计算组件相似度
    
    Args:
        comp_a: 组件 A 信息
        comp_b: 组件 B 信息
        custom_weights: 自定义权重 {'props': 0.3, 'jsx': 0.5, 'css': 0.2}
    """
    weights = custom_weights or {
        'props': 0.4,
        'jsx': 0.4,
        'css': 0.2
    }
    
    props_sim = calculate_props_similarity(comp_a, comp_b)
    jsx_sim = calculate_jsx_similarity(comp_a, comp_b)
    css_sim = calculate_css_similarity(comp_a, comp_b)
    
    return (
        props_sim * weights['props'] +
        jsx_sim * weights['jsx'] +
        css_sim * weights['css']
    )
```

### 添加可视化输出

如需生成可视化依赖图：

1. 安装依赖：`pip install graphviz`
2. 创建可视化模块：

```python
def generate_graphviz_dot(graph):
    """生成 Graphviz DOT 格式"""
    lines = ['digraph DependencyGraph {']
    
    for node in graph['nodes']:
        lines.append(f'  "{node["id"]}" [label="{node["id"]}"];')
    
    for edge in graph['edges']:
        lines.append(f'  "{edge["from"]}" -> "{edge["to"]}";')
    
    lines.append('}')
    return '\n'.join(lines)
```

---

## 性能优化建议

### 大型项目处理

对于包含 >100 个组件的项目：

1. **并行解析**：使用多线程并行解析文件
2. **增量分析**：只分析变更的文件
3. **缓存结果**：缓存解析结果避免重复计算

```python
from concurrent.futures import ThreadPoolExecutor

def parse_files_parallel(file_paths):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(parse_react_file, file_paths))
    return results
```

### 内存优化

1. 使用生成器代替列表（流式处理）
2. 及时释放不需要的数据
3. 限制递归深度

---

## 测试指南

### 单元测试示例

```python
def test_parse_imports():
    content = """
    import React from 'react';
    import { useState, useEffect } from 'react';
    import styles from './index.module.css';
    """
    
    imports = parse_imports(content)
    
    assert len(imports) == 3
    assert imports[0]['default'] == 'React'
    assert imports[1]['named'] == ['useState', 'useEffect']
```

### 集成测试

```bash
# 测试完整流程
py -3 scripts/analyze_components.py \
  --input ./test-components \
  --output ./test-output.json

# 验证输出
python -c "import json; data = json.load(open('test-output.json')); assert 'dependency_graph' in data"
```

---

## 故障排查

### 常见问题

**Q: 解析结果为空？**
- 检查文件扩展名是否为 `.jsx` 或 `.vue`
- 检查文件编码是否为 UTF-8
- 使用 `--verbose` 查看详细日志

**Q: 依赖图不完整？**
- 确保使用相对路径导入（`./` 或 `../`）
- 检查 import 路径是否正确解析
- 验证组件文件名是否符合规范

**Q: 相似度计算不准确？**
- 调整 `--threshold` 参数
- 检查组件 Props 和 JSX 是否被正确提取
- 考虑自定义相似度权重

**Q: 性能问题？**
- 减少同时分析的组件数量
- 使用 `--include-patterns` 限制检测模式
- 考虑使用 SSD 存储加快文件读取
