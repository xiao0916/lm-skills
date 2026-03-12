# psd-layer-reader AI 使用手册

## 技能定位
该技能用于**解析 PSD 文件结构**并生成 JSON 格式的图层树。它是所有后续自动化流程的基础。

## 用户 Prompt 建议

### 1. 结构分析
如果您想了解设计稿中有哪些图层，可以使用：
> "请分析 `path/to/design.psd` 的图层结构，告诉我有多少个主要的分组。"

### 2. 特定图层提取
如果您只需要某个特定的弹窗或按钮的数据，可以使用：
> "从 `path/to/design.psd` 中提取名为 'rule-modal' 的图层及其子图层的信息。"

### 3. 多样匹配（模糊匹配）
如果您不确定图层的精确名称：
> "帮我在 `path/to/design.psd` 中查找所有名字包含 'button' 的图层，并输出它们的坐标和样式。"

## AI 决策逻辑（针对开发者）
当 AI 收到上述指令时，会执行以下核心命令：
```bash
# 生成完整 JSON
py -3 -X utf8 scripts/psd_layers.py "design.psd" --output "layers.json"

# 按需过滤
py -3 -X utf8 scripts/psd_layers.py "design.psd" --name "target" --match contains --output "filter.json"
```

## 布局标签提示
在编写 UI 代码时，请注意 `layoutTag` 字段。更详细的排版算法与响应式能力，请阅读 [布局标签使用指南](../psd-to-preview/LAYOUT_TAGS_GUIDE.md)。
- `[flow-y]`: 对应垂直流式布局（Flex column）。
- `[flow-x]`: 对应水平流式布局（Flex row）。
- `[fixed]`: 对应固定视口定位。
- `[abs]`: 对应绝对定位（脱离 Flex 流排版）。

---
**版本**: 1.0 | **关联技能**: [psd-layer-reader](../SKILL.md)
