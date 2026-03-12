# psd-json-preview AI 使用手册

## 技能定位
该技能将解析后的 JSON 数据和切片图片合成为可交互的 **HTML 页面** 或 **前端组件（React/Vue）**。

## 用户 Prompt 建议

### 1. 生成静态预览
> "使用 `layer-tree.json` 和 `sliced-images` 目录生成网页预览。"

### 2. 生成 React 组件
> "生成预览并同时创建 React 组件，组件名设为 'RewardPanel'，要求保留原始图层类名。"

### 3. 生成 Vue 组件
> "将解析出的设计稿转换为 Vue 3 组件（SFC），并存放到 output 目录。"

### 4. 文字还原（核心推荐）
如果您在切图时跳过了文本图层，必须在生成代码时开启文本渲染：
> "生成预览并开启 `--include-text` 参数，把文字图层直接还原为 HTML 文字标签，不要用图片。"

## AI 决策逻辑（针对开发者）
AI 在生成预览时会综合以下参数：
- `--include-text`: 将 JSON 中的 `textInfo` 转化为 CSS 样式。**这是实现文案可编辑性的关键。**
- `--generate-react` / `--generate-vue`: 触发框架组件的生成。
- `--preserve-names`: 使用 PSD 原始图层名作为类名，方便用户在代码中对应设计稿。
- `--flatten`: 若 PSD 结构非常混乱，可使用平铺模式强制按绝对定位排列，牺牲维护性换取显示一致性。

## 输出结构说明
生成的目录包含：
- `/preview`: 用于浏览器查看的 HTML 文件。
- `/react-component`: `.jsx`、`.less` 及其私有图片资源。
- `/vue-component`: `.vue` 单文件组件。

---
**版本**: 1.0 | **关联技能**: [psd-json-preview](../SKILL.md)
