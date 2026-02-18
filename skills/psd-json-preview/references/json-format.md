# JSON 格式说明

该技能期望 PSD 导出的图层树 JSON，节点包含：

```json
{
  "name": "layer-name",
  "kind": "group|pixel|type",
  "visible": true,
  "bbox": [x1, y1, x2, y2],
  "children": []
}
```

`bbox` 为 PSD 画布中的绝对坐标。

## 图片匹配

图层名称映射到图片文件名：

- `layer-name` → `layer-name.png`（也支持 .jpg/.jpeg/.webp）

如果切片名称不同，请重命名切片或调整 JSON 图层名称。
