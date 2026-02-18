# PSD 组件拆分器 - 完整工作流指南

本文档详细介绍 `psd-component-splitter` 的完整工作流、实战示例和常见问题。

**快速开始参见：** [SKILL.md](../SKILL.md)

## 目录

1. [快速概览](#快速概览)
2. [完整工作流](#完整工作流)
3. [实战示例](#实战示例)
4. [常见问题 FAQ](#常见问题-faq)

---

## 快速概览

**一句话概括**：PSD 文件 → 读取图层结构 → 导出图片 → 拆分组件

```
┌──────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  PSD文件  │ ──▶ │  psd-layer-reader │ ──▶ │ psd-slicer   │ ──▶ │psd-component-    │
│          │     │  (生成JSON结构)    │     │ (导出图片)    │     │splitter(拆分组件)│
└──────────┘     └──────────────────┘     └──────────────┘     └──────────────────┘
                                                                      │
                                                                      ▼
                                                            ┌──────────────────┐
                                                            │ React/Vue 组件   │
                                                            │ 可直接集成到项目  │
                                                            └──────────────────┘
```

### 最简工作流（一条命令）

如果你已经完成了前置步骤，直接使用：

```bash
py -3 .claude/skills/psd-component-splitter/scripts/split_components.py \
  --json layer-tree.json \
  --images sliced-images/ \
  --out output/ \
  --framework react
```

---

## 完整工作流

### 前置步骤

1. **读取 PSD 图层结构**

```bash
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  design.psd -o layer-tree.json
```

2. **导出 PSD 图层图片**

```bash
# 基本用法
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  design.psd -o sliced-images/

# 带名称映射（处理中文图层名）
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  design.psd --mapping-json layer-tree.json -o sliced-images/
```

3. **拆分生成组件**

```bash
py -3 .claude/skills/psd-component-splitter/scripts/split_components.py \
  --json layer-tree.json \
  --images sliced-images/ \
  --out output/ \
  --framework react
```

### JSON 格式要求

组件拆分器需要符合以下格式的 JSON：

```json
{
  "name": "root",
  "kind": "group",
  "bbox": [0, 0, 750, 1334],
  "children": [
    {
      "name": "header",
      "kind": "group",
      "bbox": [0, 0, 750, 100],
      "children": [...]
    }
  ]
}
```

**必需字段**：`name`、`kind`、`bbox`
**分组类型**：`kind: "group"` 必须有 `children` 数组

---

## 实战示例

### 示例一：简单卡片组件

假设有一个名为 `card-design.psd` 的文件，包含以下结构：

```
card-design.psd
├── header（组）
│   ├── avatar（图层）
│   └── name（图层）
├── content（组）
│   ├── text（图层）
│   └── image（图层）
└── footer（组）
    └── button（图层）
```

**完整工作流**：

```bash
# 1. 创建项目目录
mkdir -p card-project

# 2. 生成 JSON 结构
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  card-design.psd \
  -o card-project/layer-tree.json

# 3. 导出切片图片
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  card-design.psd \
  -o card-project/sliced-images/

# 4. 拆分生成 React 组件
py -3 .claude/skills/psd-component-splitter/scripts/split_components.py \
  --json card-project/layer-tree.json \
  --images card-project/sliced-images/ \
  --out card-project/components/ \
  --framework react \
  --component-name CardApp

# 5. 查看结果
cd card-project/components/
ls -la
```

**输出结构**：

```
card-project/components/
├── App.jsx                    # 主入口组件
├── App.module.less            # 全局样式
├── components/                # 子组件目录
│   ├── group-header/          # Header 组件
│   │   ├── index.jsx
│   │   └── index.module.less
│   ├── group-content/         # Content 组件
│   │   ├── index.jsx
│   │   └── index.module.less
│   └── group-footer/          # Footer 组件
│       ├── index.jsx
│       └── index.module.less
└── images/                    # 图片资源
    ├── layer-avatar.png
    ├── layer-name.png
    └── ...
```

**使用组件**：

```jsx
// 在你的项目中使用
import CardApp from './card-project/components/App';

function MyPage() {
  return (
    <div>
      <h1>我的页面</h1>
      <CardApp />
    </div>
  );
}
```

---

### 示例二：电商首页

更复杂的电商页面，包含多个功能模块：

```bash
# 1. 准备工作目录
mkdir -p ecommerce-page

# 2. 分析 PSD 结构
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  ecommerce-home.psd \
  -o ecommerce-page/layer-tree.json

# 3. 导出所有切片（处理中文图层名）
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  ecommerce-home.psd \
  --mapping-json ecommerce-page/layer-tree.json \
  -o ecommerce-page/images/

# 4. 生成 Vue 组件
py -3 .claude/skills/psd-component-splitter/scripts/split_components.py \
  --json ecommerce-page/layer-tree.json \
  --images ecommerce-page/images/ \
  --out ecommerce-page/vue-components/ \
  --framework vue \
  --component-name EcommerceHome

# 5. 复制到 Vue 项目
cp -r ecommerce-page/vue-components/* my-vue-project/src/
```

**生成的组件层次**：

```
EcommerceHome（主入口）
├── TopNav（顶部导航）
├── SearchBar（搜索栏）
├── CategoryNav（分类导航）
├── BannerCarousel（轮播图）
├── ProductGrid（商品网格）
└── BottomNav（底部导航）
```

---

### 示例三：快速原型开发

适用于快速将设计稿转换为可交互原型：

```bash
#!/bin/bash
# quick-proto.sh - 一键生成组件

PSD_FILE=$1
OUTPUT_DIR=$2
FRAMEWORK=${3:-react}

if [ -z "$PSD_FILE" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "用法: ./quick-proto.sh <psd文件> <输出目录> [框架:react|vue]"
  exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "📄 读取 PSD 结构..."
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  "$PSD_FILE" \
  -o "$OUTPUT_DIR/layer-tree.json"

echo "🖼️ 导出切片图片..."
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  "$PSD_FILE" \
  --mapping-json "$OUTPUT_DIR/layer-tree.json" \
  -o "$OUTPUT_DIR/sliced-images/"

echo "⚛️ 生成 $FRAMEWORK 组件..."
py -3 .claude/skills/psd-component-splitter/scripts/split_components.py \
  --json "$OUTPUT_DIR/layer-tree.json" \
  --images "$OUTPUT_DIR/sliced-images/" \
  --out "$OUTPUT_DIR/components/" \
  --framework "$FRAMEWORK"

echo "✅ 完成！组件已生成到 $OUTPUT_DIR/components/"
```

**使用方法**：

```bash
chmod +x quick-proto.sh
./quick-proto.sh design.psd my-app react
```

---

### 示例四：React + TypeScript 项目集成

将生成的组件集成到现有的 TypeScript 项目中：

```bash
# 1. 生成组件
py -3 .claude/skills/psd-component-splitter/scripts/split_components.py \
  --json layer-tree.json \
  --images sliced-images/ \
  --out temp-components/ \
  --framework react

# 2. 添加 TypeScript 类型定义（手动或脚本）
# 为每个组件添加 .d.ts 文件

# 3. 复制到项目中
cp -r temp-components/components/* my-ts-project/src/components/
cp -r temp-components/images/* my-ts-project/src/assets/images/

# 4. 修改导入路径
# 将相对路径 './images/' 修改为 '@/assets/images/'
```

**TypeScript 类型定义示例**：

```typescript
// components/group-header/index.d.ts
export interface HeaderProps {
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}

export default function Header(props: HeaderProps): JSX.Element;
```

---

### 示例五：Vue + Vite 项目集成

集成到 Vue 3 + Vite 项目：

```bash
# 1. 生成 Vue 组件
py -3 .claude/skills/psd-component-splitter/scripts/split_components.py \
  --json layer-tree.json \
  --images sliced-images/ \
  --out vue-output/ \
  --framework vue

# 2. 复制组件
cp -r vue-output/components/* my-vite-project/src/components/

# 3. 复制图片
cp -r vue-output/images/* my-vite-project/public/images/

# 4. 修改图片路径
# 将 '../images/' 修改为 '/images/'
```

**在 Vue 页面中使用**：

```vue
<template>
  <div class="home-page">
    <PsdApp />
  </div>
</template>

<script setup>
import PsdApp from './components/group-psd-app/index.vue';
</script>
```

---

## 常见问题 FAQ

### Q1: PSD 没有第一级分组怎么办？

**原因**：组件拆分器依赖第一级 `kind: "group"` 来识别组件边界。

**解决方案**：

1. **在 PSD 中创建分组**（推荐）：选中图层后按 `Ctrl+G`/`Cmd+G`

2. **使用 psd-json-preview**：如果只需要单页预览而非组件拆分：

```bash
py -3 .claude/skills/psd-json-preview/scripts/generate_preview.py \
  --json layer-tree.json --images sliced-images/ --out preview/
```

3. **手动修改 JSON**：在第一级 children 中添加 `kind: "group"` 的包装层

---

### Q2: 如何处理命名冲突？

**自动处理**：

- `psd-layer-reader`：自动添加 `_1`、`_2` 后缀区分
- `psd-slicer`：自动处理重名冲突
- `psd-component-splitter`：自动转换组件名

**手动处理**：

在 PSD 中重命名图层，或使用 `--prefix` 参数：

```bash
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  design.psd -p "section1-" -o sliced-section1/
```

---

### Q3: 嵌套分组如何处理？

**回答**：只识别第一级分组作为独立组件。

```
design.psd
├── header（第一级分组 → 生成独立组件）
│   ├── nav（第二级 → 作为 header 的子元素）
│   └── logo（第二级 → 作为 header 的子元素）
├── content（第一级分组 → 生成独立组件）
└── footer（第一级分组 → 生成独立组件）
```

**子分组处理**：

- 第二级及以下的分组会被视为普通图层
- 它们的位置和样式会被包含在父组件中

---

### Q4: 组件代码可以自定义吗？

**回答**：可以，通过以下方式：

1. **修改生成器模板**：编辑 `react_generator.py` 或 `vue_generator.py`

2. **生成后手动调整**：

```jsx
// 添加自定义 props
export default function Header({ className, style, onClick, title }) {
  return (
    <div className={...}>
      <h1>{title}</h1>  {/* 添加自定义内容 */}
    </div>
  );
}
```

3. **使用样式覆盖**：

```jsx
<Header className="my-custom-header" style={{ background: 'red' }} />
```

---

### Q5: 支持哪些框架和版本？

| 框架 | 版本 | 样式方案 |
|------|------|----------|
| React | 16.8+（Hooks） | CSS Modules (.css) |
| Vue | 3.x | Scoped CSS |

---

### Q6: 如何处理超大 PSD 文件？

**优化策略**：

1. **分批处理**：使用 `psd-layer-reader` 的过滤功能

```bash
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  large.psd --name "header" -o header.json
```

2. **仅导出可见图层**：`psd-slicer` 默认会跳过不可见图层

3. **降低图片质量**：导出后使用图像压缩工具

---

### Q7: 生成的组件能直接用吗？

**回答**：可以直接使用，但建议进行以下优化：

1. **添加 TypeScript 类型**
2. **添加单元测试**
3. **优化样式**（移除冗余 CSS）
4. **添加响应式支持**
5. **添加无障碍属性**（aria-label 等）

---

### Q8: 技能关系与选择指南

```
psd-layer-reader ──┬──▶ psd-component-splitter ⭐
                   │
psd-slicer ────────┤    （本技能 - 组件拆分）
                   │
                   ├──▶ psd-json-preview    （HTML 预览）
                   │
                   └──▶ psd-semantic-layout （Flexbox 布局）
```

| 需求 | 推荐技能 |
|------|----------|
| 拆分为独立组件 | **psd-component-splitter** |
| 单页 HTML 预览 | psd-json-preview |
| 语义化 Flexbox 布局 | psd-semantic-layout |
| 仅导出图片 | psd-slicer |
| 仅查看结构 | psd-layer-reader |

---

### Q9: 如何调试生成失败的问题？

**排查步骤**：

1. **检查 JSON 格式**：

```bash
py -3 -m json.tool layer-tree.json > /dev/null && echo "✅ JSON 有效"
```

2. **验证分组结构**：

```bash
py -3 -c "
import json
data = json.load(open('layer-tree.json'))
groups = [c for c in data.get('children', []) if c.get('kind') == 'group']
print(f'找到 {len(groups)} 个第一级分组')
for g in groups:
    print(f'  - {g[\"name\"]}')
"
```

3. **查看详细错误**：

```bash
py -3 -u scripts/split_components.py ... 2>&1
```
