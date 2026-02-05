---
name: psd-layer-reader
description: 读取并导出 Photoshop（.psd）图层树为 JSON，包含图层元信息（名称、类型、可见性、bbox），并支持按图层名过滤。适用于需要查看 PSD 图层结构、定位特定图层组（如 rule-modal）、或生成结构化图层数据的场景。
---

# PSD 图层读取器

## 概览
将 PSD 图层树导出为 JSON，可按图层名过滤，仅返回匹配分支。

## 工作流

### 1) 安装依赖（每个环境仅需一次）
```bash
py -3 -m pip install psd-tools
```

### 2) 导出完整图层树（JSON）
```bash
py -3 -X utf8 scripts/psd_layers.py "path	oile.psd" --output "psd_layers.json"
```

### 3) 仅导出匹配分支（精确匹配）
```bash
py -3 -X utf8 scripts/psd_layers.py "path	oile.psd" --name "rule-modal" --output "rule_modal.json"
```

### 4) 仅导出匹配分支（包含匹配）
```bash
py -3 -X utf8 scripts/psd_layers.py "path	oile.psd" --name "modal" --match contains --output "modal.json"
```

## 输出格式（JSON）
每个节点包含：
- `name`（字符串）
- `kind`（字符串）
- `visible`（布尔值）
- `bbox`（[x1, y1, x2, y2]）
- `children`（子节点数组）

## 备注
- Windows 下建议使用 `py -3 -X utf8`，避免编码错误。
- 脚本已使用 `ensure_ascii=false`，可保留中文图层名。

## 资源
- `scripts/psd_layers.py`：PSD 图层树导出脚本。
