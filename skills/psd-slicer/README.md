# PSD Slicer - PSD 切片导出器

快速将 PSD 文件的图层导出为 PNG 图片。

## 快速开始

```bash
# 安装依赖
py -3 -m pip install psd-tools

# 导出所有图层
py -3 scripts/export_slices.py design.psd

# 指定输出目录
py -3 scripts/export_slices.py design.psd -o assets/layers
```

## 中文图层导出（新功能）

如果你的 PSD 包含中文命名的图层，可以使用 psd-layer-reader 生成的 JSON 文件进行名称映射导出。

**快速开始（使用项目中的 original.psd）**：

```bash
# 1. 先生成 JSON 映射文件（包含 originalName 和 name）
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py assets/original.psd -o layer-tree.json

# 2. 使用映射导出中文图层
py -3 .claude/skills/psd-slicer/scripts/export_slices.py assets/original.psd --mapping-json layer-tree.json -o images/
```

**通用示例（使用你的 PSD 文件）**：

```bash
# 1. 生成 JSON 映射
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py your-design.psd -o layer-tree.json

# 2. 导出切图
py -3 .claude/skills/psd-slicer/scripts/export_slices.py your-design.psd --mapping-json layer-tree.json -o output/
```

这样中文图层 `"按钮"` 会被导出为规范化的文件名如 `layer-abc123.png`。

### 工作原理

- `psd-layer-reader` 生成 JSON，包含 `originalName`（原始中文名）和 `name`（规范化英文名）
- `psd-slicer` 使用 PSD 中的 `layer.name`（等于 `originalName`）在映射表中查找
- 导出时使用 `name` 字段作为文件名

### 使用场景

- **网页开发**: 设计师使用中文命名图层，导出后使用规范化的英文文件名
- **组件库**: 保持 PSD 的可读性，同时生成代码友好的资源文件名
- **团队协作**: 中文图层名便于设计师理解，英文文件名便于开发人员使用

### ⚠️ 重要提示

- **版本同步**: 如果修改了 PSD 文件，必须重新生成 JSON 映射文件
- **映射匹配**: 使用 `layer.name` 作为查找键，确保 PSD 和 JSON 版本一致

### 实际案例参考

**share-modal.psd 导出实录**：

```bash
# 完整导出流程
py -3 .claude/skills/psd-layer-reader/scripts/psd_layers.py \
  --psd assets/share-modal.psd \
  --output output/layer-tree.json

py -3 .claude/skills/psd-slicer/scripts/export_slices.py \
  --psd assets/share-modal.psd \
  --output output/sliced-images \
  --mapping-json output/layer-tree.json
```

**输出示例**：
```
Loaded 177 name mappings              # 加载了 177 个名称映射
Mapped '背景' -> 'layer-npdngy.png'    # 中文图层映射为规范文件名
Mapped '唱片' -> 'group-9bi971.png'    # 图层组也会被映射
...
Done! Exported 126 layers             # 成功导出 126 个图层
```

**常见问题及解决**：

| 警告信息 | 原因 | 解决方案 |
|---------|------|----------|
| `Duplicate originalName '唱片'` | PSD 中有同名图层 | 正常现象，会自动添加 `_1`、`_2` 后缀 |
| `Layer effects require: scikit-image` | 图层包含特殊效果 | `pip install scikit-image` |

## 常用命令

```bash
# 仅导出图层组
py -3 scripts/export_slices.py design.psd -g

# 按前缀过滤（如：slice-button、slice-header）
py -3 scripts/export_slices.py design.psd -p slice-

# 组合使用：仅导出 component- 开头的图层组
py -3 scripts/export_slices.py design.psd -o ./comps/ -g -p component-

# 允许中文/特殊字符命名（特殊场景）
py -3 scripts/export_slices.py design.psd --allow-illegal-names
```

## 参数说明

| 参数                    | 短参 | 说明                        |
| ----------------------- | ---- | --------------------------- |
| `--output`              | `-o` | 输出目录（默认：`images/`） |
| `--groups-only`         | `-g` | 仅导出图层组，跳过单个图层  |
| `--prefix`              | `-p` | 前缀过滤（如：`slice-`）    |
| `--allow-illegal-names` | 无   | 允许中文/特殊字符（慎用）   |
| `--mapping-json`        | `-m` | JSON 映射文件路径，用于导出中文图层名 |

## 命名规则

默认情况下，仅导出符合 `[a-zA-Z0-9_-]` 的图层名称：

- ✅ **合法**：`button`、`btn-primary`、`slice-01`、`component_card`
- ❌ **非法**：`按钮`（中文）、`Button<>`（特殊字符）、`icon[close]`（方括号）

**为什么要限制命名？**

- 确保跨平台文件系统兼容性
- 避免后续工具处理问题
- 符合代码和资源命名规范

## 典型场景

### 网页开发

```bash
# 导出所有设计元素
py -3 scripts/export_slices.py landing-page.psd -o ./public/images/
```

### 组件库开发

```bash
# 仅导出标记为 component- 的组件
py -3 scripts/export_slices.py ui-library.psd -g -p component- -o ./src/assets/
```

### 设计交付

```bash
# 导出所有图层（包括中文命名）
py -3 scripts/export_slices.py design.psd --allow-illegal-names
```

## 特性说明

- ✅ 自动递归处理嵌套图层组
- ✅ 跳过不可见图层
- ✅ 自动处理重名冲突（添加 `_1`、`_2` 后缀）
- ✅ 跳过空白或零尺寸图层
- ✅ 保留图层透明度

## 故障排查

**问题：没有导出任何文件**

- 检查图层名称是否合法（默认不支持中文）
- 尝试使用 `--allow-illegal-names` 参数

**问题：某些图层被跳过**

- 检查前缀过滤参数 `-p` 是否正确
- 确认图层是可见的
- 确认图层不是空白的

**问题：矢量图层导出失败**

- 安装可选依赖：`py -3 -m pip install 'psd-tools[composite]'`

## 项目结构

```
psd-slicer/
├── SKILL.md              # AI 技能定义（OpenCode）
├── README.md             # 本文档（人类用户参考）
└── scripts/
    └── export_slices.py  # 核心导出脚本
```

## 相关技能

- **psd-layer-reader** - 读取 PSD 图层结构为 JSON
- **psd-to-preview** - PSD 到预览页面的完整转换工作流

---

**维护说明**：本技能是 `psd-to-code` 项目的一部分，用于从 PSD 提取图层图片。
