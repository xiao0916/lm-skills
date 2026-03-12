# -*- coding: utf-8 -*-
from utils import unwrap_value, rgba_to_array


def _extract_style_from_data(style_sheet_data, font_set):
    """
    从样式数据中提取 run 样式信息。
    主路径和 fallback 路径共用此函数。
    """
    if not hasattr(style_sheet_data, 'get'):
        return {}

    run_data = {}

    # fontName
    font_idx = style_sheet_data.get("Font")
    if isinstance(font_idx, int) and 0 <= font_idx < len(font_set):
        font_entry = font_set[font_idx]
        if hasattr(font_entry, 'get'):
            run_data["fontName"] = font_entry.get("Name")

    # fontSize
    if "FontSize" in style_sheet_data:
        run_data["fontSize"] = unwrap_value(style_sheet_data.get("FontSize"))

    # color
    color_source = (
        style_sheet_data.get("FgColor")
        or style_sheet_data.get("FillColor")
        or style_sheet_data.get("Color")
    )
    color_array = rgba_to_array(color_source)
    if color_array:
        run_data["color"] = color_array

    # alignment
    alignment = style_sheet_data.get("Justification")
    if alignment is None:
        alignment = style_sheet_data.get("Alignment")
    if alignment is not None:
        run_data["alignment"] = unwrap_value(alignment)

    # leading / tracking / baselineShift / autoLeading
    for key in ["Leading", "Tracking", "BaselineShift", "AutoLeading"]:
        if key in style_sheet_data:
            val = style_sheet_data.get(key)
            run_data[key[0].lower() + key[1:]] = unwrap_value(val)

    return run_data


def _as_number(value):
    """将值转换为数值类型。"""
    value = unwrap_value(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except Exception:
            return None
    return None


def _find_first_style_dict(node, max_depth=7):
    """深度有限搜索，查找包含已知样式键的字典。"""
    STYLE_KEYS = {
        "Font", "FontSize", "FgColor", "FillColor", "Color",
        "Leading", "AutoLeading", "Tracking", "Justification", "Alignment",
    }
    if max_depth <= 0:
        return None
    node = unwrap_value(node)
    if isinstance(node, dict):
        hits = sum(1 for k in STYLE_KEYS if k in node)
        if hits >= 2:
            return node
        for v in node.values():
            found = _find_first_style_dict(v, max_depth=max_depth - 1)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_first_style_dict(item, max_depth=max_depth - 1)
            if found is not None:
                return found
    return None


def _extract_fallback_style(style_dict, font_set):
    """
    当 StyleRun 缺失时，从段落/文档默认样式中提取信息。
    在公共函数基础上补充 autoLeading → leading 的换算逻辑。
    """
    # 先用公共函数提取基础样式
    run_data = _extract_style_from_data(style_dict, font_set)

    if not isinstance(style_dict, dict):
        return run_data

    font_size = run_data.get("fontSize")
    if font_size is not None:
        font_size = _as_number(font_size)
        if font_size is not None:
            run_data["fontSize"] = font_size

    # fontName fallback：无明确索引时取第一个字体
    if "fontName" not in run_data and font_set:
        font_entry0 = font_set[0] if font_set else None
        if isinstance(font_entry0, dict):
            run_data["fontName"] = font_entry0.get("Name")

    # autoLeading 百分比/倍数 → 像素换算
    auto_leading_val = run_data.get("autoLeading")
    if auto_leading_val is None and "autoLeading" in style_dict:
        auto_leading_val = unwrap_value(style_dict.get("autoLeading"))

    auto_percent = None
    if isinstance(auto_leading_val, (int, float)):
        v = float(auto_leading_val)
        auto_percent = v * 100 if 0 < v <= 10 else v
    elif isinstance(auto_leading_val, str):
        v = _as_number(auto_leading_val)
        if v is not None:
            auto_percent = v * 100 if 0 < v <= 10 else v

    if auto_percent is not None:
        run_data["autoLeading"] = auto_percent
        leading_val = run_data.get("leading")
        if (leading_val is None or leading_val == 0) and font_size is not None:
            run_data["leading"] = font_size * (auto_percent / 100.0)

    # tracking 单位换算（1/1000 em → px）
    tracking_raw = run_data.get("tracking")
    if tracking_raw is None and "tracking" in style_dict:
        tracking_raw = _as_number(style_dict.get("tracking"))
    if tracking_raw is not None and font_size is not None:
        tracking_raw = _as_number(tracking_raw)
        if tracking_raw is not None:
            run_data["tracking"] = font_size * (tracking_raw / 1000.0)
    elif tracking_raw is not None and font_size is None:
        # fontSize 缺失时不输出模糊单位
        run_data.pop("tracking", None)

    return run_data


def extract_text_info(layer):
    """从文本图层（kind == 'type'）中提取文本信息。"""
    if layer.kind != "type":
        return None

    try:
        text = layer.text or ""
        text = text.replace("\r", "\n")

        text_info = {"text": text}

        text_type = getattr(layer, "text_type", None)
        if text_type is not None:
            text_info["textType"] = str(text_type)

        engine_dict = layer.engine_dict if hasattr(layer, "engine_dict") else None
        resource_dict = layer.resource_dict if hasattr(layer, "resource_dict") else None
        font_set = resource_dict.get("FontSet", []) if hasattr(resource_dict, 'get') else []
        # 某些 PSD 的字体信息在 engine_dict.DocumentResources 下
        if not font_set and hasattr(engine_dict, 'get'):
            doc_res = engine_dict.get("DocumentResources")
            if hasattr(doc_res, 'get') and hasattr(doc_res.get("FontSet"), '__len__'):
                font_set = doc_res.get("FontSet") or []

        # ─── 主路径：从 StyleRun 中提取 runs ───
        runs = []
        run_length_array = []
        run_array = []
        if isinstance(engine_dict, dict) or hasattr(engine_dict, 'get'):
            style_run = engine_dict.get("StyleRun", {}) if engine_dict else {}
            if hasattr(style_run, 'get'):
                rla = style_run.get("RunLengthArray")
                ra = style_run.get("RunArray")
                if rla is not None:
                    run_length_array = rla
                if ra is not None:
                    run_array = ra

        if run_array and run_length_array:
            run_text = text
            if hasattr(engine_dict, 'get'):
                editor = engine_dict.get("Editor", {})
                if hasattr(editor, 'get') and "Text" in editor:
                    run_text = unwrap_value(editor.get("Text", text)) or text
                    run_text = run_text.replace("\r", "\n")

            text_index = 0
            for length, run_item in zip(run_length_array, run_array):
                length = int(length)
                run_data = {"text": run_text[text_index:text_index + length]}
                text_index += length

                # 获取 StyleSheetData
                style_sheet_data = None
                if hasattr(run_item, 'get'):
                    if "StyleSheet" in run_item and hasattr(run_item["StyleSheet"], 'get'):
                        style_sheet_data = run_item["StyleSheet"].get("StyleSheetData")
                    if style_sheet_data is None and "StyleSheetData" in run_item:
                        style_sheet_data = run_item.get("StyleSheetData")

                # 用公共函数提取样式
                style_data = _extract_style_from_data(style_sheet_data, font_set)
                run_data.update(style_data)
                runs.append(run_data)

        # ─── Fallback 路径：StyleRun 缺失时 ───
        if not runs and isinstance(engine_dict, dict):
            candidates = []
            paragraph_run = engine_dict.get("ParagraphRun")
            if isinstance(paragraph_run, dict):
                pr_array = paragraph_run.get("RunArray")
                if isinstance(pr_array, list) and pr_array:
                    candidates.append(pr_array[0])

            editor = engine_dict.get("Editor")
            if isinstance(editor, dict):
                editor_text = editor.get("Text")
                if isinstance(editor_text, dict):
                    psr = editor_text.get("ParagraphStyleRange")
                    if isinstance(psr, list) and psr:
                        candidates.append(psr[0])

            doc_res = engine_dict.get("DocumentResources")
            if isinstance(doc_res, dict):
                candidates.append(doc_res)

            for cand in candidates:
                cand = unwrap_value(cand)
                style_dict = None
                if isinstance(cand, dict):
                    ps = cand.get("ParagraphSheet")
                    if isinstance(ps, dict):
                        style_dict = (
                            ps.get("Properties")
                            or ps.get("ParagraphSheetData")
                            or ps.get("StyleSheetData")
                        )
                    if style_dict is None:
                        style_dict = (
                            cand.get("ParagraphSheetData")
                            or cand.get("Properties")
                            or cand.get("StyleSheetData")
                        )
                    if style_dict is None and isinstance(cand.get("StyleSheet"), dict):
                        style_dict = cand.get("StyleSheet", {}).get("StyleSheetData")

                if style_dict is None:
                    style_dict = _find_first_style_dict(cand)

                style_dict = unwrap_value(style_dict)
                if isinstance(style_dict, dict):
                    run_defaults = _extract_fallback_style(style_dict, font_set)
                    if run_defaults:
                        runs = [{"text": text, **run_defaults}]
                        break

        # ─── 汇总到 text_info ───
        if runs:
            text_info["runs"] = runs
            first_run = runs[0]
            for key in [
                "fontName", "fontSize", "color", "alignment",
                "leading", "tracking", "baselineShift", "autoLeading",
            ]:
                if key in first_run:
                    text_info[key] = first_run[key]

        return text_info if len(text_info) > 1 else None
    except Exception as e:
        # 记录提取失败的原因，便于调试
        # print(f"[!] Error extracting text info: {e}")
        return None
