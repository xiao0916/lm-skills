# 用户详细指南

## 完整工作流程

### 示例 1：完整工作流

```bash
# 第 1 步：分析组件（只读模式）
py -3 .claude/skills/code-splitter/scripts/split_component.py \
  --input verify-flow/verify-030/react-component/ \
  --dry-run \
  --output split-report.md

# 查看生成的 report.md，确认拆分建议

# 第 2 步：生成组件（只生成高分组件）
py -3 .claude/skills/code-splitter/scripts/component_generator.py \
  --input verify-flow/verify-030/react-component/ \
  --output ./split-components/ \
  --min-score 0.6
```

### 示例 2：生成目录结构

```
split-components/
├── dailyCard/
│   ├── index.jsx          # DailyCard 组件
│   └── index.module.css   # DailyCard 样式
├── header/
│   ├── index.jsx          # Header 组件
│   └── index.module.css   # Header 样式
├── footer/
│   ├── index.jsx          # Footer 组件
│   └── index.module.css   # Footer 样式
├── app/
│   ├── index.jsx          # 整合所有子组件
│   └── index.module.css   # App 样式
└── generation-report.json # 生成报告
```

### 示例 3：查看详细日志

```bash
# Suggestion Mode 详细输出
py -3 scripts/split_component.py --input ./my-component/ --dry-run -v

# Generate Mode 详细输出
py -3 scripts/component_generator.py --input ./my-component/ --output ./split/ -v
```

## 命令行参数说明

### split_component.py 参数

| 参数 | 短参 | 说明 | 默认值 |
|-----|------|------|-------|
| `--input` | `-i` | 输入组件目录路径（必需） | - |
| `--dry-run` | `-d` | 建议模式：只生成报告，不创建文件 | false |
| `--output` | `-o` | 输出报告文件路径 | stdout |
| `--min-score` | - | 最小置信度阈值 | 0.3 |
| `--verbose` | `-v` | 显示详细信息 | false |

### component_generator.py 参数

| 参数 | 短参 | 说明 | 默认值 |
|-----|------|------|-------|
| `--input` | `-i` | 输入组件目录路径（必需） | - |
| `--output` | `-o` | 输出目录路径 | `./generated-components/` |
| `--analysis` | - | JSON 格式的分析结果文件 | 实时分析 |
| `--min-score` | - | 最小置信度阈值 | 0.3 |
| `--dry-run` | `-d` | 只预览，不创建文件 | false |
| `--verbose` | `-v` | 显示详细信息 | false |

## 分析维度详解

### 维度 1：语义类名分析

通过 CSS 类名推断组件语义类型：

| 类名模式 | 语义类型 | 置信度 | 组件名前缀 |
|---------|---------|-------|----------|
| `card-*` / `*-card` | Card | 0.95 | Card |
| `btn-*` / `button-*` | Button | 0.90 | Btn |
| `header-*` | Header | 0.90 | Header |
| `footer-*` | Footer | 0.90 | Footer |
| `modal-*` / `dialog-*` | Modal | 0.90 | Modal |
| `nav-*` | Navigation | 0.85 | Nav |
| `form-*` | Form | 0.85 | Form |
| `icon-*` | Icon | 0.70 | Icon |
| `title-*` | Title | 0.70 | Title |

### 维度 2：DOM 结构分析

分析元素在 DOM 树中的位置和包裹关系：

- **包裹多个子元素**：包裹 6+ 个子元素 +0.5 分，4+ 个子元素 +0.35 分
- **嵌套深度**：嵌套 2+ 层 +0.05 分
- **语义多样性**：包含 3+ 种语义类型 +0.15 分

### 维度 3：重复模式检测

识别相似结构：
- 相同类名前缀的元素组
- 相似子结构的容器

### 维度 4：位置分析

根据元素在页面中的位置推断组件类型：

| 位置关键词 | 推断类型 | 额外得分 |
|-----------|---------|---------|
| top, header, nav | Header | +0.3 |
| bottom, footer | Footer | +0.3 |
| left, right, sidebar | Sidebar | +0.25 |

## 置信度解读

### 置信度等级

| 等级 | 分数范围 | 标记 | 建议操作 |
|-----|---------|------|---------|
| **HIGH** | 0.80 - 1.0 | [HIGH] | 强烈建议拆分，低风险 |
| **MEDIUM** | 0.50 - 0.79 | [MEDIUM] | 可以拆分，需要人工审核 |
| **LOW** | 0.30 - 0.49 | [LOW] | 谨慎拆分，可能过度拆分 |
| **IGNORE** | < 0.30 | - | 不建议拆分 |

### 置信度计算

```
总分 = 语义类名得分 × 0.6 + DOM结构得分 × 0.3 + 位置得分 × 0.1
```

## 与其他技能的配合

### 与 psd-to-preview 配合使用

完整的 PSD 到 React 组件工作流：

```bash
# 1. 从 PSD 生成 React 组件
py -3 .claude/skills/psd-to-preview/scripts/run_workflow.py \
  assets/design.psd \
  output/

# 2. 分析生成的组件
py -3 .claude/skills/code-splitter/scripts/split_component.py \
  --input output/preview/react-component/ \
  --dry-run

# 3. 拆分为小组件
py -3 .claude/skills/code-splitter/scripts/component_generator.py \
  --input output/preview/react-component/ \
  --output output/split/
```

### 与 frontend-code-review 配合使用

```bash
# 1. 生成拆分后的组件
py -3 scripts/component_generator.py --input ./comp/ --output ./split/

# 2. 使用 frontend-code-review 检查生成的代码
# （按照项目代码审查流程）
```
