---
name: psd-slicer
description: 将 Photoshop（.psd）文件的所有图层导出为独立的 PNG 图片。适用于从 PSD 文件提取图层图片、为网页开发生成切片、或为其他工具准备图层资源。自动处理图层命名、跳过不可见图层、递归导出嵌套图层组。
---

# PSD 切片导出器

## 核心功能

自动将 PSD 文件的可见图层导出为独立 PNG 图片，支持灵活过滤和命名验证。

**特性**：

- ✅ 强制命名合法性检查（`[a-zA-Z0-9_-]` 仅，确保生产安全）
- ✅ 递归处理嵌套图层组
- ✅ 自动处理重名冲突
- ✅ 支持按组/前缀过滤
- ✅ 跳过不可见/空白图层

## 使用方式

### 基础命令

```bash
# 导出所有合法命名的图层
py -3 scripts/export_slices.py design.psd

# 自定义输出目录
py -3 scripts/export_slices.py design.psd -o assets/layers

# 仅导出图层组（跳过单个图层）
py -3 scripts/export_slices.py design.psd -g

# 按前缀过滤（如：slice-button）
py -3 scripts/export_slices.py design.psd -p slice-

# 组合使用
py -3 scripts/export_slices.py design.psd -o ./comps/ -g -p component-
```

### 参数说明

| 参数                    | 短参 | 说明                                  |
| ----------------------- | ---- | ------------------------------------- |
| `--output`              | `-o` | 输出目录（默认：`images/`）           |
| `--groups-only`         | `-g` | 仅导出图层组                          |
| `--prefix`              | `-p` | 前缀过滤（如：`slice-`）              |
| `--allow-illegal-names` | 无   | 允许中文/特殊字符（慎用）             |
| `--mapping-json`        | `-m` | JSON 映射文件路径（用于中文图层导出） |

## 何时使用名称映射

当 PSD 文件包含中文、日文或其他非 ASCII 字符命名的图层时，推荐使用 `--mapping-json` 参数。

### 技术实现

**映射关系**:

- PSD 中的 `layer.name` 返回原始名称（可能是中文）
- JSON 中的 `originalName` 保存相同的原始名称
- JSON 中的 `name` 是规范化后的合法文件名
- 映射表结构: `{layer.name: name}` 即 `{原始名称: 规范化名称}`

**工作流程**:

1. 使用 `psd-layer-reader` 分析 PSD 结构并生成 JSON
2. 检查 JSON 中的 `originalName` 和 `name` 映射关系
3. 使用 `psd-slicer` 的 `--mapping-json` 参数导出图层

**示例**:

```bash
# 步骤 1: 生成 JSON 映射
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py design.psd -o layer-tree.json

# 步骤 2: 使用映射导出
py -3 .claude/skills/psd-slicer/scripts/export_slices.py design.psd --mapping-json layer-tree.json -o assets/
```

**注意事项**:

- 确保 JSON 文件和 PSD 文件对应同一设计稿（版本必须同步）
- 如果 PSD 被修改，必须重新生成 JSON 文件
- 映射功能会自动处理嵌套的图层组（递归遍历 children）
- 如果图层在 JSON 中找不到映射且名称不合法，会被跳过并输出警告
- 映射匹配使用 PSD 的 `layer.name` 作为查找键

### 实战案例：share-modal.psd

**完整工作流**（含中文图层导出）：

```bash
# 步骤 1: 创建输出目录并生成 JSON 映射
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  --psd assets/share-modal.psd \
  --output verify-flow/verify-010/layer-tree.json

# 步骤 2: 使用映射导出中文图层
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  --psd assets/share-modal.psd \
  --output verify-flow/verify-010/sliced-images \
  --mapping-json verify-flow/verify-010/layer-tree.json
```

**实际输出示例**：

```
Loaded 177 name mappings
Mapped '背景' -> 'layer-npdngy.png'
Exported Layer: layer-npdngy.png
Mapped '图层 1' -> 'layer-9dgwjr.png'
Exported Layer: layer-9dgwjr.png
Mapped '唱片' -> 'group-9bi971.png'
Exported Group: group-9bi971.png
...
Done! Exported to: verify-flow/verify-010/sliced-images
```

**常见警告处理**：

1. **重复名称警告**（正常现象）：

   ```
   Warning: Duplicate originalName '唱片'
   Warning: Duplicate originalName '雨滴'
   ```

   这是因为 PSD 中存在同名图层，系统会自动添加 `_1`、`_2` 后缀区分。

2. **图层效果警告**（需安装依赖）：
   ```
   Warning: Could not export '活动规则': Layer effects require: scikit-image
   ```
   **解决方案**：
   ```bash
   pip install scikit-image
   # 或
   pip install 'psd-tools[composite]'
   ```

**导出统计示例**：

- 总图层映射：177 个
- 成功导出：126 个图层（31 个组 + 95 个图片）
- 带图层效果需额外依赖：约 10 个（如"活动规则"、"SLOGAN"、"标题"等）

### 向后兼容

- 不带 `--mapping-json` 参数时，行为与之前完全一致
- 中文图层仍会被跳过（除非使用 `--allow-illegal-names`）

## 命名规则

**合法✅**：`button`、`btn-primary`、`slice-01`、`component_card`
**非法❌**：`按钮`（中文）、`Button<>`（特殊字符）、`icon[close]`（方括号）

**规则**：默认仅导出符合 `[a-zA-Z0-9_-]` 的图层，确保文件系统兼容性和代码安全性。

## 依赖说明

### 必需依赖

- `psd-tools`: PSD 文件解析核心库

### 可选依赖

- `scikit-image`: 用于导出包含图层效果的元素（如阴影、发光、渐变等）

### 手动安装命令

```bash
# 安装依赖
py -3 -m pip install psd-tools
py -3 -m pip install scikit-image
```

**注意**：当前脚本在检测到缺少依赖时只会打印警告，不会自动安装。建议使用 `psd-to-preview` 技能的预检查功能，让 AI 在执行前检查并安装依赖。

## 常见场景

- **网页开发**：提取设计元素为 HTML/CSS 资源
- **组件导出**：使用 `-g -p component-` 导出标记的组件
- **预览生成**：为 psd-json-preview 技能准备切片图片
- **设计交付**：批量导出设计文件的所有图层

## 用户使用指南

详细的使用示例和 Prompt 模板请参考：
📄 **[references/USER_GUIDE.md](references/USER_GUIDE.md)**

### 快速参考

| 用户关键词              | AI 应执行                                      |
| ----------------------- | ---------------------------------------------- |
| "中文图层" / "中文命名" | 使用 `--mapping-json` 参数（先生成 JSON 映射） |
| "只导出组" / "图层组"   | 使用 `-g` / `--groups-only` 参数               |
| "icon-" 开头            | 使用 `-p icon-` 参数                           |
| "保存到 xxx"            | 使用 `-o xxx` 参数                             |

---

## 资源文件

- **scripts/export_slices.py** - 核心导出脚本（219行）
- **README.md** - 人类用户参考文档
