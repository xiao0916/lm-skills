# psd-to-preview 参考文档

> 本文档是 psd-to-preview 的详细参考文档，快速执行指南请参见 [SKILL.md](./SKILL.md)

---

## 目录

- [工作原理](#工作原理)
- [工作流步骤详解](#工作流步骤详解)
- [使用场景](#使用场景)
- [输出目录结构](#输出目录结构)
- [工作流参数详解](#工作流参数详解)
- [React 组件生成说明](#react-组件生成说明)
- [最佳实践](#最佳实践)
- [技术规格](#技术规格)
- [工作流集成](#工作流集成)

---

## 工作原理

这个技能通过三个无缝衔接的步骤，自动将 Photoshop 设计文件转换为可交互的预览页面和 React 组件：

```
PSD 文件
   ↓
【步骤 1】psd-layer-reader: 图层树解析（输出 JSON）
   ├─ 读取 PSD 层级结构
   ├─ 提取完整元数据
   └─ 输出: layer-tree.json (130 行元数据)
   ↓
【步骤 2】psd-slicer: 图层切片导出
   ├─ 自动导出所有可见图层为 PNG
   ├─ 规范化文件命名
   └─ 输出: sliced-images/ (多张 PNG)
   ↓
【步骤 3】psd-json-preview: 代码生成（预览 + React + Vue）
   ├─ 综合上述两个输出
   ├─ 生成交互式 HTML 预览
   ├─ 生成 React 组件（JSX + CSS Modules）
   ├─ 生成 Vue 组件（SFC + Scoped CSS）
   └─ 输出: preview/ (预览文件 + react-component/ + vue-component/)
   ↓
✅ 完成: 预览页面 + 可复用的 React 组件 + Vue 组件
```

---

## 工作流步骤详解

### 步骤 1：图层树解析 (psd-layer-reader)

**作用**：读取 PSD 的完整层级结构，导出为 JSON 格式

**输入**：PSD 文件路径  
**输出**：`layer-tree.json` (JSON 格式)

**提取的元数据**：

- **名称** (name)：图层名称
- **类型** (kind)：group/pixel/type
- **可见性** (visible)：true/false
- **坐标** (bbox)：[x, y, width, height]
- **结构** (children)：嵌套关系

**示例 JSON 结构**：

```json
[
  {
    "name": "bg",
    "kind": "group",
    "visible": true,
    "bbox": [0, 0, 750, 3000],
    "children": [
      {
        "name": "background-image",
        "kind": "pixel",
        "visible": true,
        "bbox": [0, 0, 750, 3000],
        "children": []
      }
    ]
  }
]
```

### 步骤 2：图层切片导出 (psd-slicer)

**作用**：将 PSD 文件的所有图层导出为独立的 PNG 图片

**输入**：PSD 文件路径  
**输出**：`sliced-images/` 目录（多张 PNG 图片）

**自动处理**：

- 图层命名规范化（合法的文件名）
- 跳过不可见的图层
- 递归导出嵌套的图层组
- 保留原始图层的空间信息

**示例输出**：

```
sliced-images/
├── bg.png (背景)
├── logo.png (Logo)
├── button.png (按钮)
├── card-1.png (卡片)
└── card-2.png (卡片)
```

### 步骤 3：代码生成 (psd-json-preview)

**作用**：综合前两步的输出，生成交互式 HTML 预览页面、React 组件和 Vue 组件

**输入**：

- `layer-tree.json` (图层树)
- `sliced-images/` (切片图片)

**输出**：

- `preview.html` (主预览页面)
- `preview/` (资源目录)
- `preview/react-component/` (React 组件代码)
- `preview/vue-component/` (Vue 组件代码)

**页面功能**：

#### 功能区 1：设计画布预览

- 显示原始 PSD 的完整画布
- 所有图层的位置和关系
- 可滚动查看整个设计
- 自适应布局

#### 功能区 2：图层结构与元数据

- **树形结构**：展示图层的嵌套关系
  ```
  bg (group)
    ├─ background-image (pixel)
    ├─ content (group)
    │  ├─ title (type)
    │  └─ description (type)
    └─ footer (group)
  ```
- **元数据表格**：每层的详细信息
  | 序号 | 名称 | 类型 | 可见 | 坐标 | 尺寸 |
  |------|------|------|------|------|------|
  | 1 | bg | group | ✓ | 0,0 | 750×3000 |
- **统计**：图层总数、画布尺寸等

#### 功能区 3：切片图集

- 网格展示全部切片图片
- 每张图片的文件名标签
- 响应式自适应
- 点击可查看原始尺寸

### React 和 Vue 组件生成功能（集成在步骤 3 中）

**作用**：基于相同的图层数据和切片图片，生成可复用的 React 组件和 Vue 组件代码

**输入**：

- `layer-tree.json` (图层树)
- `sliced-images/` (切片图片)

**输出**：

- **React 组件**：
  - `preview/react-component/index.jsx` (React 组件)
  - `preview/react-component/index.module.less` (CSS Modules 样式)
  - `preview/react-component/images/` (图片资源副本)

- **Vue 组件**：
  - `preview/vue-component/index.vue` (Vue 单文件组件)
  - `preview/vue-component/index.module.less` (Scoped CSS 样式)
  - `preview/vue-component/images/` (图片资源副本)

**组件特性**：

#### 代码生成特点

- **JSX 结构**：使用 React 函数组件语法
- **Vue SFC**：使用 Vue 3 单文件组件语法
- **CSS Modules**：样式隔离，避免全局污染
- **保留图层名**：使用 `--preserve-names` 参数保持 PSD 原始图层名称，便于设计对应
- **嵌套结构**：自动识别图层组，生成对应的 JSX/Vue 嵌套结构

#### 样式处理

- **绝对定位**：像素级精确还原设计稿位置
- **响应式图片**：自动处理图片资源引用
- **BEM 兼容**：支持 BEM 命名规范的类名生成
- **注释说明**：中文注释解释每个图层的用途

#### 使用示例（React）

```jsx
import PsdComponent from "./react-component";

// 在你的应用中使用
function App() {
  return (
    <div>
      <PsdComponent />
    </div>
  );
}
```

#### 使用示例（Vue）

```vue
<script setup>
import PsdComponent from "./vue-component/index.vue";
</script>

<template>
  <div>
    <PsdComponent />
  </div>
</template>
```

---

## 使用场景

| 场景            | 描述                    | 主要用途             |
| --------------- | ----------------------- | -------------------- |
| 📋 **设计交付** | 生成完整的设计交付包    | 团队协作、设计验收   |
| 💻 **开发参考** | 提供切片资源和坐标信息  | 前端开发、样式编写   |
| 📚 **设计文档** | 记录图层结构和命名规范  | 设计系统、组件库     |
| ✅ **质量检查** | 验证导出完整性和精度    | 预验证、质量保证     |
| ⚛️ **组件开发** | 生成可复用的 React 组件 | 快速原型、组件库构建 |

---

## 输出目录结构

完整工作流的输出目录结构：

```
output-directory/
├─ 📄 START_HERE.txt              快速开始指引
├─ 📄 preview.html                ⭐ 主预览页面（在浏览器打开）
├─ 📄 README.md                   快速导航
├─ 📄 FLOW_REPORT.md              详细报告
├─ 📄 layer-tree.json             PSD 图层树 (JSON)
│
├─ 📁 sliced-images/              16+ 张 PNG 切片
│  ├─ bg.png
│  ├─ logo.png
│  ├─ button.png
│  └─ ...
│
├─ 📁 preview/                    预览资源
│  ├─ index.html (设计画布预览)
│  ├─ styles.css (预览样式)
│  └─ images/ (切片副本)
│
└─ 📁 preview/react-component/   ⭐ React 组件代码 (预览目录内)
   ├─ index.jsx (React 组件)
   ├─ index.module.less (CSS Modules)
   └─ images/ (切片副本)
```

---

## 工作流参数详解

### 核心参数

| 参数           | 说明                         | 示例                    |
| -------------- | ---------------------------- | ----------------------- |
| **psd_path**   | PSD 文件的完整路径或相对路径 | `assets/design.psd`     |
| **output_dir** | 输出目录的完整路径或相对路径 | `output/design-preview` |

### 可选参数

| 参数                     | 说明                         | 默认值 |
| ------------------------ | ---------------------------- | ------ |
| **include_preview_docs** | 是否生成预览文档 (README 等) | `true` |
| **include_checklist**    | 是否生成质量检查清单         | `true` |
| **generate_report**      | 是否生成详细验证报告         | `true` |

---

## React 组件生成说明

### 组件生成选项

psd-to-preview 工作流默认使用以下 React 组件生成配置：

| 参数               | 值             | 说明                        |
| ------------------ | -------------- | --------------------------- |
| `--name`           | `PsdComponent` | 生成的 React 组件名称       |
| `--preserve-names` | ✓              | 保留 PSD 原始图层名作为类名 |
| `--no-text`        | ✗              | 包含文字图层（默认）        |

### 组件文件结构

```
react-component/
├─ index.jsx                    # React 组件代码
├─ index.module.less           # CSS Modules 样式
└─ images/                     # 图片资源副本
```

### 组件使用方法

```jsx
// 1. 导入组件
import PsdComponent from "./react-component";

// 2. 在应用中使用
function App() {
  return (
    <div>
      <h1>我的设计</h1>
      <PsdComponent />
    </div>
  );
}
```

### 样式定制

生成的组件使用 CSS Modules，可以通过以下方式定制：

```jsx
// 传递自定义样式
<PsdComponent style={{ width: "800px", margin: "0 auto" }} />
```

### 开发建议

- **快速原型**：直接使用生成的组件进行原型开发
- **样式调整**：修改 `index.module.less` 文件定制样式
- **组件拆分**：基于生成的代码拆分为更小的组件
- **状态管理**：添加 React state 来实现交互功能

### 最佳实践

1. **保留原始命名**：使用 `--preserve-names` 保持与设计稿的一致性
2. **逐步优化**：先使用生成的组件，再逐步优化样式和结构
3. **版本控制**：将生成的组件纳入版本控制，便于追踪变化
4. **组件复用**：提取公共样式和逻辑，提高代码复用性

---

## 最佳实践

### ✅ 推荐做法

1. **目录组织**
   - 将所有 PSD 文件放在 `assets/` 目录
   - 将预览输出放在 `output/` 或 `previews/` 目录
   - 按设计版本或功能模块组织

2. **文件命名**
   - PSD 文件：`design-v1.0.psd`、`homepage.psd`
   - 输出目录：对应的设计名称或版本

3. **批量处理**
   - 多个 PSD 文件时，为每个分别运行工作流
   - 为每个输出创建独立目录
   - 便于版本管理和对比

4. **质量检查**
   - 验证输出目录中的所有文件
   - 检查切片图片的数量和质量
   - 查看预览页面是否正常加载

### ⚠️ 常见问题

**Q: 某些图层没有被导出？**  
A: 检查 PSD 中是否有不可见的图层。psd-slicer 会跳过不可见层。如需导出，请在 Photoshop 中打开图层可见性。

**Q: 预览页面无法加载图片？**  
A: 确保相对路径正确，`sliced-images/` 目录与 `preview.html` 在同一父目录。

**Q: 如何处理超大 PSD 文件？**  
A: 大文件可能需要更多时间处理。工作流会自动处理，通常 8-10 分钟内完成。

---

## 技术规格

| 项目           | 规格                                        |
| -------------- | ------------------------------------------- |
| **输入格式**   | `.psd` (Photoshop CC 2019+)，支持 1-100+ MB |
| **输出图片**   | PNG (32-bit 透明)，原始尺寸，无损压缩       |
| **输出 JSON**  | UTF-8 编码，完整保留嵌套关系                |
| **预览页面**   | HTML5 + CSS3 + JS，离线可用，无外部依赖     |
| **处理时间**   | 通常 8-10 分钟（取决于文件大小和图层数）    |
| **浏览器兼容** | Chrome、Firefox、Safari、Edge (现代版本)    |

---

## 工作流集成

**完整的设计转代码流程**：

1. psd-to-preview → 生成预览页面和 React 组件
2. frontend-design → 进一步优化前端代码
3. frontend-code-review → 代码审查

支持集成到 CI/CD 自动化流程。

---

**版本**: 1.0 | **最后更新**: 2026年2月11日
