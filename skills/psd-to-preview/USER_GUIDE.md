# psd-to-preview AI 使用手册

## 技能定位
该技能是**零门槛 PSD 转代码的工作流入口**。它集成了解析、切图、生成预览的全过程，能够一句话触发完整的自动化管道。

## 用户 Prompt 建议

### 1. 快捷全流程转化（一句话搞定）
> "使用 psd-to-preview 技能，帮我把 `path/to/design.psd` 转换成代码，并生成 React 组件存放在 test-001 文件夹。"

### 2. 核心进阶：文案转代码
如果您希望页面的文本是真正可以复制和编辑的 HTML 文字：
> "使用 psd-to-preview 技能，帮我把 `path/to/design.psd` 转为代码。要求：**文案转代码**（不切文字图片），并产出 Vue 组件。"

### 3. 环境预检查（解决报错）
如果在执行过程中 AI 提示缺少 Python 库：
> "请检查 PSD 转换所需的依赖环境并帮我安装好。"

## AI 内部工作流
当您发送上述 Prompt 时，AI 会自动按顺序执行以下步骤：
1.  **依赖预检查**：检查并确保 `psd-tools` 和 `scikit-image` 已安装。
2.  **图层解析 (`psd-layer-reader`)**：生成图层树 JSON。
3.  **智能切图 (`psd-slicer`)**：根据需求导出图片（若要求文案转代码则加上 `--skip-type`）。
4.  **预览合成 (`psd-json-preview`)**：生成 HTML / React / Vue 文件（若要求文案转代码则加上 `--include-text`）。

## 布局标签支持
在 PSD 设计阶段，通过在图层或组名称前添加 `[flow-y]`、`[flow-x]` 等标签，可以获得真正的自适应 Flex 布局与特殊定位（而不是死板的绝对坐标叠加）。详细的标签定义请阅读 [布局标签使用指南](./LAYOUT_TAGS_GUIDE.md)。

## 开发者提示
- **输出目录**: 默认为 PSD 同名目录下的 `preview/`。
- **组件名称**: 默认为 `PsdComponent`，您可以通过 Prompt 指定特定名称。
- **强制约束**: 如果要保证还原度，建议 Prompt 中包含“带上样式还原文字”等关键词。

---
**版本**: 1.0 | **关联技能**: [psd-to-preview](SKILL.md)
