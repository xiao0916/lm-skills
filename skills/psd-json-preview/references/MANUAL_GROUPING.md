# 手动处理 PSD 分组结构指南

## 概述

`psd-json-preview` 默认将所有图层平铺到 canvas 中，使用绝对定位且全部相对于 canvas 定位。这种方式简单直接，适合像素级精确还原，但不保留 PSD 的分组层级。

如果需要在生成的 HTML 中保留 PSD 的分组结构（例如为了更好的语义化、便于后续维护），需要手动修改生成的代码。

## 为什么需要手动处理？

**默认行为**：

- 所有图层平铺，无论在 PSD 中是否有分组
- 所有图层直接作为 `.canvas` 的子元素
- 简单但失去了 PSD 的结构信息

**手动分组后的优势**：

- 保留 PSD 设计的层级结构
- HTML 代码更具语义化
- 便于后续针对特定分组进行整体操作（如隐藏、动画等）
- 更易于理解和维护

## 完整操作步骤

### 步骤 1：识别 PSD 中的图层组

打开 `layer-tree.json`，查找 `"kind": "group"` 的节点：

```json
{
  "name": "rs-card",
  "kind": "group",
  "visible": true,
  "bbox": [119, 145, 739, 994],
  "children": [
    {
      "name": "rs-layer-3",
      "kind": "pixel",
      "bbox": [313, 145, 656, 429]
    },
    {
      "name": "rs-layer-2",
      "kind": "pixel",
      "bbox": [211, 314, 507, 881]
    }
  ]
}
```

记录以下信息：

- **分组名称**：`rs-card`
- **分组边界**：`bbox: [119, 145, 739, 994]`
- **子图层列表**：`rs-layer-3`, `rs-layer-2`, ...

### 步骤 2：修改 HTML 结构

在 `index.html` 中，将属于该组的图层用 `<div>` 包裹：

**修改前：**

```html
<div class="canvas">
  <div class="layer_rs_layer_3"></div>
  <div class="layer_rs_layer_2"></div>
  <div class="layer_rs_layer_1"></div>
</div>
```

**修改后：**

```html
<div class="canvas">
  <div class="group_rs_card">
    <div class="layer_rs_layer_3"></div>
    <div class="layer_rs_layer_2"></div>
    <div class="layer_rs_layer_1"></div>
  </div>
</div>
```

### 步骤 3：添加分组容器样式

在 `styles.css` 中添加分组容器的样式：

```css
/* rs-card 组容器 (bbox: [119, 145, 739, 994]) */
.group_rs_card {
  left: 119px; /* bbox[0] */
  top: 145px; /* bbox[1] */
  width: 620px; /* bbox[2] - bbox[0] = 739 - 119 */
  height: 849px; /* bbox[3] - bbox[1] = 994 - 145 */
}
```

### 步骤 4：设置子元素定位

**关键步骤**：必须为分组内的子元素显式设置 `position: absolute`：

```css
/* 分组内子元素必须设置绝对定位 */
.group_rs_card > div {
  position: absolute;
  display: block;
}
```

> **为什么需要这一步？**  
> 虽然 `.canvas > div` 已经设置了 `position: absolute`，但这个规则不会应用到 `.group_rs_card` 的子元素（因为它们不是 `.canvas` 的直接子元素）。必须单独为分组的子元素设置定位。

### 步骤 5：转换子图层坐标

将子图层的坐标从相对 canvas 转换为相对父容器：

**原始（相对 canvas）：**

```css
.layer_rs_layer_3 {
  left: 313px;
  top: 145px;
  width: 343px;
  height: 284px;
}
```

**转换后（相对父容器）：**

```css
.layer_rs_layer_3 {
  left: 194px; /* 313 - 119 = 194 */
  top: 0px; /* 145 - 145 = 0 */
  width: 343px; /* 不变 */
  height: 284px; /* 不变 */
}
```

**转换公式：**

```
left_relative = left_absolute - parent_left
top_relative = top_absolute - parent_top
```

其中：

- `left_absolute` / `top_absolute`：子图层在 PSD 中的绝对坐标
- `parent_left` / `parent_top`：父容器的 left/top 值（即 bbox[0] / bbox[1]）

## 常见错误排查

### 错误 1：分组容器覆盖整个 canvas

❌ **错误代码：**

```css
.group_rs_card {
  left: 0;
  top: 0;
  width: 750px; /* canvas 的宽度 */
  height: 1624px; /* canvas 的高度 */
}
```

**问题**：分组容器覆盖了整个画布，而不是它实际占据的区域。

✅ **正确做法**：使用分组在 PSD 中的实际 bbox 计算尺寸。

---

### 错误 2：子图层坐标未转换

❌ **错误代码：**

```css
.layer_rs_layer_3 {
  left: 313px; /* 仍然是相对 canvas 的坐标 */
  top: 145px;
}
```

**问题**：子图层的坐标仍然相对于 canvas，而不是相对于父容器，导致位置错误。

✅ **正确做法**：

```css
.layer_rs_layer_3 {
  left: 194px; /* 313 - 119 */
  top: 0px; /* 145 - 145 */
}
```

---

### 错误 3：忘记设置子元素的 position

❌ **错误代码：**

```css
/* 缺少这个规则 */
.group_rs_card > div {
  /* 没有设置 position: absolute */
}
```

**问题**：子元素不会按照 left/top 值进行绝对定位，而是按照文档流排列。

✅ **正确做法**：

```css
.group_rs_card > div {
  position: absolute;
  display: block;
}
```

---

### 错误 4：只转换了部分子图层

❌ **错误**：只转换了 HTML 结构，但忘记转换某些子图层的 CSS 坐标。

**表现**：部分图层位置正确，部分图层位置错误。

✅ **正确做法**：确保分组内**所有**子图层的坐标都进行了转换。

## 实际案例：verify-013 的 rs-card 组

### JSON 数据

```json
{
  "name": "rs-card",
  "kind": "group",
  "bbox": [119, 145, 739, 994],
  "children": [
    { "name": "rs-layer-3", "bbox": [313, 145, 656, 429] },
    { "name": "rs-layer-2", "bbox": [211, 314, 507, 881] },
    { "name": "rs-layer-1", "bbox": [180, 212, 726, 994] },
    { "name": "rs-tianma-rare", "bbox": [132, 286, 739, 918] },
    { "name": "rs-tiama", "bbox": [119, 335, 690, 866] },
    { "name": "rs-rare-tip", "bbox": [312, 216, 344, 321] }
  ]
}
```

### HTML 结构

```html
<div class="canvas">
  <div class="group_rs_card">
    <div class="layer_rs_layer_3"></div>
    <div class="layer_rs_rare_tip"></div>
    <div class="layer_rs_layer_1"></div>
    <div class="layer_rs_tianma_rare"></div>
    <div class="layer_rs_layer_2"></div>
    <div class="layer_rs_tiama"></div>
  </div>
</div>
```

### CSS 样式

```css
/* 分组容器 */
.group_rs_card {
  left: 119px;
  top: 145px;
  width: 620px; /* 739 - 119 */
  height: 849px; /* 994 - 145 */
}

/* 子元素定位 */
.group_rs_card > div {
  position: absolute;
  display: block;
}

/* 子图层（坐标已转换） */
.layer_rs_layer_3 {
  left: 194px; /* 313 - 119 */
  top: 0px; /* 145 - 145 */
  width: 343px;
  height: 284px;
  background-image: url("./images/rs-layer-3.png");
  background-size: 100% 100%;
}

.layer_rs_layer_2 {
  left: 92px; /* 211 - 119 */
  top: 169px; /* 314 - 145 */
  width: 296px;
  height: 567px;
  background-image: url("./images/rs-layer-2.png");
  background-size: 100% 100%;
}

.layer_rs_layer_1 {
  left: 61px; /* 180 - 119 */
  top: 67px; /* 212 - 145 */
  width: 546px;
  height: 782px;
  background-image: url("./images/rs-layer-1.png");
  background-size: 100% 100%;
}

.layer_rs_tianma_rare {
  left: 13px; /* 132 - 119 */
  top: 141px; /* 286 - 145 */
  width: 607px;
  height: 632px;
  background-image: url("./images/rs-tianma-rare.png");
  background-size: 100% 100%;
}

.layer_rs_tiama {
  left: 0px; /* 119 - 119 */
  top: 190px; /* 335 - 145 */
  width: 571px;
  height: 531px;
  background-image: url("./images/rs-tiama.png");
  background-size: 100% 100%;
}

.layer_rs_rare_tip {
  left: 193px; /* 312 - 119 */
  top: 71px; /* 216 - 145 */
  width: 32px;
  height: 105px;
  background-image: url("./images/rs-rare-tip.png");
  background-size: 100% 100%;
}
```

## 验证方法

完成修改后，在浏览器中打开预览页面，检查：

1. **视觉效果**：所有图层是否显示在正确的位置
2. **结构层级**：使用浏览器开发者工具，确认 DOM 结构符合预期
3. **坐标计算**：随机选择几个子图层，手动验证坐标转换是否正确

## 何时需要手动分组？

**需要手动分组的场景**：

- 希望保留 PSD 的设计层级结构
- 需要对某个分组整体进行操作（如显示/隐藏、动画）
- 代码需要更好的可维护性和语义化
- 作为后续代码重构的基础

**不需要手动分组的场景**：

- 只是用于设计交付和视觉验证
- 追求像素级精确还原，不关心代码结构
- 预览页面是一次性的，不需要后续维护

## 总结

手动处理 PSD 分组需要三个关键步骤：

1. ✅ 使用分组的实际 bbox 设置容器尺寸
2. ✅ 为分组内子元素显式设置 `position: absolute`
3. ✅ 将子图层坐标转换为相对于父容器

遵循这些步骤，就能正确地在 HTML 中保留 PSD 的分组结构。
