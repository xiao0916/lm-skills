# 技术实现细节

## 架构概述

Code Splitter 采用模块化架构，由以下核心模块组成：

```
scripts/
├── jsx_parser.py          # JSX 解析器（正则方案）
├── css_parser.py          # CSS Modules 解析器
├── analyzer.py            # 智能分析算法
├── component_generator.py # 组件生成器
├── asset_analyzer.py      # 资源分析器
├── check_env.py           # 环境检查
└── split_component.py     # CLI 入口
```

## JSX 解析器

### 实现方式

使用正则表达式解析 JSX，而非 AST：

- **优点**：无 Node.js 依赖，纯 Python 实现，速度快
- **缺点**：无法处理复杂表达式（条件渲染、map 循环等）

### 核心正则模式

```python
# 元素标签
r'<(\w+)'

# className（styles["name"] 格式）
r'className=\{styles\["([^"]+)"\]\}'

# 自闭合标签
r'<\w+[^>]*/>'

# 注释
r'\{/\*\s*(.+?)\s*\*/\}'
```

### 输出格式

```python
{
  "tag": "div",
  "className": "rs-card",
  "attributes": {"role": "img"},
  "selfClosing": False,
  "children": [
    {
      "tag": "div",
      "className": "rs-layer-1",
      "selfClosing": True,
      "children": []
    }
  ]
}
```

## CSS 解析器

### 实现方式

使用正则表达式解析 CSS Modules：

```python
# 选择器
r'\.([\w-]+)\s*\{'

# 属性
r'([\w-]+)\s*:\s*([^;]+);?'
```

### 输出格式

```python
{
  "rs-card": {
    "properties": {
      "left": "119px",
      "top": "145px",
      "width": "343px"
    },
    "raw": ".rs-card {\n  left: 119px;\n  ...\n}"
  }
}
```

## 分析算法

### 多维度评分

```python
def calculate_score(element, css_map):
    semantic = match_pattern(element.className) * 0.6
    structure = count_children(element) * 0.01 * 0.3
    duplicate = similarity_score(element) * 0.1
    position = position_score(css_map, element.className) * 0.0
    return min(semantic + structure + duplicate + position, 1.0)
```

### 语义类名模式

```python
SEMANTIC_PATTERNS = {
    r'^btn-': 'button',
    r'^button-?': 'button',
    r'^icon-': 'icon',
    r'^text-': 'text',
    r'^header-?': 'header',
    r'^footer-?': 'footer',
    r'^card-?': 'card',
    r'^nav-?': 'navigation',
    r'^modal-?': 'modal',
}
```

### DOM 结构分析

```python
def analyze_dom_structure(element):
    child_count = len(element.get('children', []))
    nested_depth = calculate_depth(element)
    semantic_types = count_semantic_types(element)
    
    score = 0
    if child_count >= 6:
        score += 0.5
    elif child_count >= 4:
        score += 0.35
    
    if nested_depth >= 2:
        score += 0.05
    
    if semantic_types >= 3:
        score += 0.15
    
    return score
```

## 组件生成器

### 组件模板

```jsx
/**
 * ${name} 组件
 * ${description}
 * 
 * @param {string} className - 额外的 CSS 类名
 * @param {Object} style - 内联样式
 * @param {Function} onClick - 点击事件处理
 */
const ${name} = ({ 
  className = '', 
  style = {}, 
  onClick,
  ...rest 
}) => {
  return (
    <div 
      className={`\${styles.root} \${className}`}
      style={style}
      onClick={onClick}
      {...rest}
    >
      ${children}
    </div>
  );
};

export default ${name};
```

### CSS 提取逻辑

1. 从组件元素中提取所有 className
2. 从原 CSS 中匹配对应的规则
3. 复制到新的 `.module.css` 文件
4. **不做坐标转换**（v1 限制）

### App.jsx 生成

```jsx
import React from 'react';
import Card from './components/card/index.jsx';
import Header from './components/header/index.jsx';
import styles from './App.module.css';

const App = () => {
  return (
    <div className={styles.page}>
      <Header />
      <Card />
    </div>
  );
};

export default App;
```

## 已知限制

### v1 版本限制

1. **JSX 解析**：使用正则，不支持复杂表达式
2. **CSS 处理**：只支持 CSS Modules，不做坐标转换
3. **框架支持**：只支持 React 函数组件
4. **状态管理**：不处理 hooks 依赖

### 未来改进（v2）

- 使用 Babel AST 解析 JSX
- 支持 Vue SFC
- 支持 TypeScript
- 坐标自动转换
- hooks 依赖分析
