# PSD Slicer 用户使用指南

本文档提供详细的使用示例和 Prompt 模板，帮助用户更好地使用 psd-slicer 技能。

---

## 推荐 Prompt 示例

### 场景一：PSD 包含中文图层（推荐）

**用户说**：
> "我有一个 PSD 设计文件 `design.psd`，里面有很多中文命名的图层（比如"按钮"、"背景"、"标题"等），帮我把这些图层导出为 PNG 图片，并且使用英文文件名。"

**AI 执行**：
```bash
# 步骤 1: 生成 JSON 映射
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py design.psd -o layer-tree.json

# 步骤 2: 使用映射导出中文图层
py -3 .claude/skills/psd-slicer/scripts/export_slices.py design.psd --mapping-json layer-tree.json -o images/
```

---

### 场景二：只需要特定前缀的图层

**用户说**：
> "从 `ui-kit.psd` 中提取所有标记为 `icon-` 开头的图标图层，导出到 `assets/icons/` 目录。"

**AI 执行**：
```bash
py -3 .claude/skills/psd-slicer/scripts/export_slices.py ui-kit.psd -p icon- -o assets/icons/
```

---

### 场景三：仅导出图层组

**用户说**：
> "导出 `landing-page.psd` 中所有的图层组（跳过单个图层），保存到 `components/` 文件夹。"

**AI 执行**：
```bash
py -3 .claude/skills/psd-slicer/scripts/export_slices.py landing-page.psd -g -o components/
```

---

### 场景四：完整的 PSD 切图工作流

**用户说**：
> "我有一个 PSD 文件 `homepage.psd`，帮我：1）分析图层结构；2）导出所有切图；3）确保中文图层名能正确导出。"

**AI 执行**：
```bash
# 1. 分析图层结构
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py homepage.psd -o homepage-layers.json

# 2. 导出所有切图（使用映射支持中文）
py -3 .claude/skills/psd-slicer/scripts/export_slices.py homepage.psd --mapping-json homepage-layers.json -o slices/
```

---

## Prompt 关键词速查

| 用户关键词 | AI 识别 | 对应参数 |
|-----------|---------|----------|
| "中文图层" / "中文命名" | 使用名称映射 | `--mapping-json` |
| "只导出组" / "图层组" | 仅导出图层组 | `-g` / `--groups-only` |
| "icon-" / "button-" 开头 | 按前缀过滤 | `-p` / `--prefix` |
| "保存到 xxx 文件夹" | 指定输出目录 | `-o` / `--output` |
| "跳过中文" / "不要中文" | 不使用映射 | 不带 `--mapping-json` |

---

## 最佳 Prompt 模板

```
我有一个 PSD 文件 [文件名.psd]，需要导出 [所有图层/特定图层]。
[图层包含中文命名 / 需要导出 icon- 开头的图层 / 只需要图层组]
请帮我导出到 [输出目录]。
```

**完整示例**：
> "我有一个 PSD 文件 `app-design.psd`，需要导出所有图层。这个文件有很多中文命名的图层（比如"首页背景"、"用户头像"）。请帮我导出到 `assets/images/` 目录，确保中文图层也能被正确导出。"

---

## 常见错误及解决方案

### 错误 1：没有导出任何文件
**原因**：图层名称包含中文，但没有使用 `--mapping-json` 参数
**解决**：使用 psd-layer-reader 生成 JSON 映射，然后使用 `--mapping-json` 参数导出

### 错误 2：某些图层被跳过
**原因**：
- 图层不可见
- 图层是空白的（零尺寸）
- 前缀过滤参数不匹配
**解决**：检查图层可见性和前缀参数

### 错误 3：文件名冲突
**解决**：脚本会自动处理重名冲突（添加 `_1`、`_2` 后缀），无需手动处理

---

## 高级用法

### 组合使用多个参数
```bash
# 导出 icon- 开头的图层组，保存到 assets/icons/
py -3 scripts/export_slices.py design.psd -g -p icon- -o assets/icons/
```

### 导出时显示详细信息
```bash
# 脚本会自动输出导出日志，包括：
# - 映射关系（如：Mapped '封套' -> 'group-euz1zh.png'）
# - 导出的文件类型（Layer/Group）
# - 跳过的图层（如果名称不合法且无映射）
```

---

**文档版本**: v1.0  
**更新日期**: 2026-02-12
