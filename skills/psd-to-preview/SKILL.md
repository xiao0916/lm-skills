---
name: psd-to-preview
description: 从 PSD 设计文件到预览页面 + React 组件 + Vue 组件的完整转换工作流。
---

# psd-to-preview: PSD 转预览和 React 组件

## AI 执行指令（置顶）

**当用户请求使用此技能时，必须按以下步骤实际执行命令。**

**AI 执行规则**：

1. **默认**：用户未明确说"导出中文图层"时，**绝对不要**使用 `--mapping-json`
2. **中文图层**：默认跳过是预期行为，只有用户明确要求时才导出

### 依赖预检查（AI 执行前必须执行）

AI 在执行工作流前，**必须**先检查依赖是否已安装：

```powershell
# 检查 psd-tools
py -3 -c "import psd_tools" 2>&1
# 如果返回 ImportError，表示未安装

# 检查 scikit-image
py -3 -c "import skimage" 2>&1
```

**如果缺少依赖，AI 必须询问用户**：

> "检测到缺少以下依赖，是否安装？
>
> - `psd-tools`（必需）
> - `scikit-image`（必需）
>
> 输入 '是' 确认安装，或 '否' 跳过（部分图层可能无法导出）"

**用户确认后，AI 执行安装**：

```powershell
# 安装必需依赖
py -3 -m pip install psd-tools

# 安装可选依赖（如果用户同意）
py -3 -m pip install scikit-image
```

**版本检查（可选）**：

```powershell
# 检查已安装的版本
py -3 -c "import psd_tools; print('psd-tools:', psd_tools.__version__)"
py -3 -c "import skimage; print('scikit-image:', skimage.__version__)"
```

**注意事项**:

- 如果用户选择不安装 `psd-tools`，无法继续执行工作流
- 如果用户选择不安装 `scikit-image`，可以执行但部分带图层效果的元素会被跳过
- 安装完成后，建议重新检查依赖是否安装成功

---

### 执行命令

```powershell
# 步骤 1：图层解析
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  --psd <PSD文件路径> --output <输出目录>/layer-tree.json

# 步骤 2：图层切片
py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  --psd <PSD文件路径> --output <输出目录>/sliced-images
# 注：中文图层会被跳过。只有用户明确要求导出中文图层时，才加 --mapping-json

# 步骤 3：代码生成
py -3 .claude/skills/psd-json-preview/scripts/generate_preview.py \
  --json <输出目录>/layer-tree.json --images <输出目录>/sliced-images \
  --out <输出目录>/preview --generate-react --generate-vue \
  --component-name PsdComponent --preserve-names
```

**关键提醒**：

- ✅ 使用 `py -3`（Windows）或 `python3`（Linux/Mac）
- ⚠️ 输出目录示例：`verify-flow/verify-028`（不要在路径末尾加 `/preview`）

---

### 执行检查清单

- [ ] `<输出目录>/layer-tree.json` 有数据
- [ ] `<输出目录>/sliced-images/` 有 PNG 文件
- [ ] `<输出目录>/preview/` 有 HTML 文件
- [ ] `<输出目录>/react-component/` 有 JSX 和 CSS 文件
- [ ] `<输出目录>/vue-component/` 有 Vue 文件

---

## 工作原理

PSD → psd-layer-reader → layer-tree.json → psd-slicer → sliced-images/ → psd-json-preview → preview/ + react-component/ + vue-component/

---

## 快速参考

### 核心参数

| 参数       | 说明         | 示例                    |
| ---------- | ------------ | ----------------------- |
| `--psd`    | PSD 文件路径 | `assets/design.psd`     |
| `--output` | 输出目录     | `output/design-preview` |

### 常见问题

**Q: 某些图层没有被导出？**  
A: psd-slicer 会跳过不可见层和非法命名图层（中文等）。

**Q: PSD 包含中文图层？**  
A: 默认跳过。只有用户明确要求导出时，步骤2加 `--mapping-json <输出目录>/layer-tree.json`

**Q: 为什么会出现 `preview/preview/` 双重嵌套？**  
A: 输出目录名不要用 "preview"，建议用 `verify-028`、`design-v1` 等。

---

## 输出目录结构

```
output/
├── preview.html          # 主预览页面
├── layer-tree.json       # 图层数据
├── sliced-images/        # PNG切片
├── preview/              # 预览资源
├── react-component/      # React组件
└── vue-component/        # Vue组件
```

---

## 故障排查

| 错误          | 原因       | 解决方案         |
| ------------- | ---------- | ---------------- |
| PSD 未找到    | 路径错误   | 检查文件路径     |
| 权限错误      | 无写入权限 | 检查目录权限     |
| 预览加载失败  | 路径错误   | 确保目录结构完整 |
| JSON 解析错误 | 文件损坏   | 重新运行工作流   |

---

## 依赖说明

### 必需依赖

- `psd-tools`: PSD 文件解析核心库

### 可选依赖

- `scikit-image`: 用于导出包含图层效果的元素（如阴影、发光、渐变等）

### 手动安装命令

如果预检查阶段的自动安装失败，可手动执行：

```bash
# 安装依赖
py -3 -m pip install psd-tools
py -3 -m pip install scikit-image
```

**注意**：虽然 SKILL.md 中包含安装命令，但 AI 执行时**不会自动运行**。请参考"依赖预检查"小节，让 AI 在执行工作流前检查并安装依赖。

---

**版本**: 1.4 | **更新**: 2026年2月12日
