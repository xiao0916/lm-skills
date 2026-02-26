#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图层名称翻译模块 - 将 PSD 图层名翻译为中文注释

功能：
1. 内置通用 PSD 命名词库（40+ 词汇）
2. 支持加载项目级 layer-name-dict.json 自定义映射
3. 分词翻译策略：按 - _ 分词后逐 token 翻译，避免子串误匹配
4. PS 泛型名识别与跳过
5. 统一注释格式输出

用法：
    from layer_name_translator import LayerNameTranslator

    translator = LayerNameTranslator("path/to/layer-name-dict.json")  # 可选
    comment = translator.format_comment("btn-share", kind="pixel")
    # => "<!-- btn-share: 分享按钮 -->"
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional


# ============================================================
# 内置通用词库 - 覆盖常见 PSD 图层命名元素
# ============================================================
BUILTIN_WORD_MAP: Dict[str, str] = {
    # --- 容器/背景 ---
    "bg": "背景",
    "background": "背景",
    "card": "卡片",
    "frame": "框架",
    "box": "盒子",
    "container": "容器",
    "wrapper": "包裹器",
    "panel": "面板",
    "section": "区域",
    "content": "内容",

    # --- 按钮/操作 ---
    "btn": "按钮",
    "button": "按钮",
    "close": "关闭",
    "back": "返回",
    "share": "分享",
    "draw": "抽取",
    "store": "商店",
    "submit": "提交",
    "confirm": "确认",
    "cancel": "取消",
    "save": "保存",
    "delete": "删除",
    "edit": "编辑",
    "add": "添加",
    "search": "搜索",
    "refresh": "刷新",
    "download": "下载",
    "upload": "上传",

    # --- 文本/标签 ---
    "text": "文本",
    "title": "标题",
    "subtitle": "副标题",
    "name": "名称",
    "label": "标签",
    "tip": "提示",
    "tips": "提示",
    "desc": "描述",
    "description": "描述",
    "info": "信息",
    "date": "日期",
    "time": "时间",
    "year": "年份",
    "month": "月份",
    "day": "日",
    "nickname": "昵称",
    "balance": "余额",
    "price": "价格",
    "count": "数量",
    "num": "数字",
    "number": "数字",

    # --- 图标/视觉元素 ---
    "icon": "图标",
    "arrow": "箭头",
    "flower": "花朵",
    "star": "星星",
    "badge": "徽章",
    "avatar": "头像",
    "img": "图片",
    "image": "图片",
    "photo": "照片",
    "pic": "图片",
    "thumb": "缩略图",
    "banner": "横幅",
    "cover": "封面",

    # --- 弹窗/遮罩 ---
    "modal": "弹窗",
    "mask": "遮罩",
    "popup": "弹出层",
    "dialog": "对话框",
    "toast": "提示条",
    "overlay": "遮罩层",
    "rule": "规则",

    # --- 页面结构 ---
    "group": "分组",
    "header": "头部",
    "footer": "底部",
    "nav": "导航",
    "sidebar": "侧边栏",
    "tab": "选项卡",
    "tabs": "选项卡组",
    "list": "列表",
    "item": "项目",
    "row": "行",
    "col": "列",
    "column": "列",
    "grid": "网格",
    "menu": "菜单",
    "toolbar": "工具栏",

    # --- 状态 ---
    "on": "开",
    "off": "关",
    "active": "激活",
    "disabled": "禁用",
    "hover": "悬停",
    "selected": "选中",
    "checked": "勾选",
    "loading": "加载中",
    "empty": "空",
    "error": "错误",
    "success": "成功",

    # --- 其他 ---
    "daily": "每日",
    "rare": "稀有",
    "route": "线路",
    "prize": "奖品",
    "mine": "我的",
    "my": "我的",
    "new": "新",
    "hot": "热门",
    "top": "顶部",
    "bottom": "底部",
    "left": "左",
    "right": "右",
    "center": "居中",
    "main": "主要",
    "sub": "子",
    "divider": "分割线",
    "line": "线条",
    "border": "边框",
    "shadow": "阴影",
    "layer": "图层",

    # --- 自定义项目词汇（项目专用，根据实际项目命名规范定义） ---
    "rs": "瑞兽",
    "shouhu": "守护",
    "bgm": "背景音乐",
    "tianma": "天马",
}

# 保持英文不翻译的 token（品牌词、专有名词）
KEEP_ENGLISH = {"logo", "slogan", "app", "vip", "ok", "id", "url", "qr", "bgm"}

# 无意义的连接词 - 翻译时跳过
SKIP_TOKENS = {"to", "the", "a", "an", "of", "and", "or", "in", "on", "at", "for", "with", "by"}

# PS 泛型名模式 - 匹配 <编组>、<矩形>、<图像> + <路径> 等
_GENERIC_PATTERN = re.compile(
    r'^[<＜].*[>＞]'  # 以 < 或全角 ＜ 开头
    r'|^图层\s*\d*$'   # "图层 3" 格式
)

# PS 泛型名集合（完整匹配）
GENERIC_WORDS = {
    "<图像>", "<编组>", "<路径>", "<形状>", "<剪切组>", "<椭圆>", "<矩形>", "<图层>",
    "<image>", "<group>", "<path>", "<shape>", "<layer>", "<rectangle>",
}

class LayerNameTranslator:
    """
    图层名称翻译器
    
    支持加载项目级字典文件（layer-name-dict.json），
    优先级：项目字典精确匹配 > 项目字典 token 匹配 > 内置词库 > 保留原名
    """

    def __init__(self, dict_path: Optional[str] = None):
        """
        初始化翻译器
        
        Args:
            dict_path: 项目级字典文件路径（可选）。
                       文件为 JSON 格式，key 为图层名或 token，value 为中文含义。
        """
        self.project_dict: Dict[str, str] = {}
        self.project_dict_lower: Dict[str, str] = {}  # 小写版本加速查找
        
        if dict_path:
            self._load_dict(dict_path)

    def _load_dict(self, dict_path: str) -> None:
        """加载项目级字典文件"""
        path = Path(dict_path)
        if not path.exists():
            print(f"[提示] 图层名字典文件未找到: {dict_path}，将仅使用内置词库")
            return
        
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 过滤掉注释字段（以 _ 开头的 key）
            self.project_dict = {
                k: v for k, v in data.items()
                if isinstance(k, str) and isinstance(v, str) and not k.startswith("_")
            }
            self.project_dict_lower = {
                k.lower(): v for k, v in self.project_dict.items()
            }
            
            count = len(self.project_dict)
            print(f"[OK] 已加载项目字典: {dict_path} ({count} 个词条)")
        except (json.JSONDecodeError, IOError) as e:
            print(f"[警告] 加载字典文件失败: {e}，将仅使用内置词库")

    def is_generic_name(self, name: str) -> bool:
        """
        判断是否为 PS 泛型名（如 <编组>、<矩形> + <矩形>、图层 3）
        
        泛型名是 Photoshop 自动生成的无意义名称，生成注释时可跳过。
        """
        stripped = name.strip()
        if not stripped:
            return True
        
        # 完整匹配
        if stripped in GENERIC_WORDS:
            return True
        
        # 组合泛型名：<矩形> + <矩形>
        if " + " in stripped:
            parts = [p.strip() for p in stripped.split("+")]
            return all(p in GENERIC_WORDS for p in parts)
        
        # 正则匹配
        if _GENERIC_PATTERN.match(stripped):
            return True
        
        return False

    def _has_chinese(self, text: str) -> bool:
        """检测文本中是否包含中文字符"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _clean_prefix(self, name: str) -> str:
        """清理图层名称前缀噪音字符（如 -h- 前缀）"""
        # 去掉以 -X- 开头的前缀（单字母标记）
        cleaned = re.sub(r'^-[a-zA-Z]-', '', name)
        # 去掉首尾的 - _ 和空格
        cleaned = cleaned.strip('-_ ')
        return cleaned if cleaned else name

    def translate(self, layer_name: str) -> str:
        """
        翻译图层名称为中文
        
        翻译优先级：
        1. 项目字典精确匹配（完整图层名）
        2. 已含中文 → 清理噪音后返回
        3. 项目字典 token 匹配 + 内置词库逐 token 翻译
        
        Args:
            layer_name: 原始图层名称
        
        Returns:
            翻译后的中文名称，未匹配时返回原名
        """
        name = layer_name.strip()
        if not name:
            return layer_name

        lower_name = name.lower()

        # 1. 项目字典精确匹配（完整图层名）
        if lower_name in self.project_dict_lower:
            return self.project_dict_lower[lower_name]

        # 2. 已含中文 → 清理噪音后返回
        if self._has_chinese(name):
            return self._clean_prefix(name)

        # 3. 保持英文的品牌词
        if lower_name in KEEP_ENGLISH:
            return name

        # 4. 分词翻译
        tokens = [t for t in re.split(r'[-_]+', lower_name) if t]
        if not tokens:
            return layer_name

        translated_parts = []
        has_translation = False  # 是否至少翻译了一个 token

        for token in tokens:
            # 保持英文的特殊 token
            if token in KEEP_ENGLISH:
                translated_parts.append(token)
                continue

            # 无意义的连接词跳过
            if token in SKIP_TOKENS:
                continue

            # 项目字典 token 匹配
            if token in self.project_dict_lower:
                translated_parts.append(self.project_dict_lower[token])
                has_translation = True
                continue

            # 内置词库匹配
            if token in BUILTIN_WORD_MAP:
                translated_parts.append(BUILTIN_WORD_MAP[token])
                has_translation = True
                continue

            # 纯数字保留
            if token.isdigit():
                translated_parts.append(token)
                continue

            # 未匹配的 token 保留原样
            translated_parts.append(token)

        if not has_translation:
            return layer_name

        # 拼接规则：中文 token 间无分隔符，涉及英文/数字用 - 连接
        result = self._join_tokens(translated_parts)
        return result if result else layer_name

    def _join_tokens(self, parts: list) -> str:
        """
        智能拼接翻译后的 token
        
        规则：
        - 两个中文 token 之间不加分隔符（如 "分享" + "按钮" → "分享按钮"）
        - 涉及英文/数字 token 时用 "-" 连接（如 "logo" + "图标" → "logo-图标"）
        """
        if not parts:
            return ""
        
        result = [parts[0]]
        for i in range(1, len(parts)):
            prev = parts[i - 1]
            curr = parts[i]
            
            prev_is_cjk = self._has_chinese(prev)
            curr_is_cjk = self._has_chinese(curr)
            
            if prev_is_cjk and curr_is_cjk:
                # 两个中文 token 之间无分隔符
                result.append(curr)
            else:
                # 涉及英文/数字用 - 连接
                result.append("-")
                result.append(curr)
        
        return "".join(result)

    def format_comment(self, original_name: str, kind: str = "pixel") -> str:
        """
        生成 HTML 注释字符串
        
        格式：<!-- 原名: 中文翻译 -->
        泛型名（如 <编组>）返回空字符串（跳过注释）。
        
        Args:
            original_name: 原始图层名称
            kind: 图层类型（group/pixel/type）
        
        Returns:
            HTML 注释字符串，泛型名返回空字符串
        """
        if self.is_generic_name(original_name):
            return ""
        
        translated = self.translate(original_name)
        
        # 如果翻译结果与原名相同，只输出原名
        if translated == original_name:
            return f"<!-- {original_name} -->"
        
        return f"<!-- {original_name}: {translated} -->"

    def format_css_comment(self, original_name: str) -> str:
        """
        生成 CSS 注释字符串
        
        格式：/* 原名: 中文翻译 */
        泛型名返回空字符串。
        
        Args:
            original_name: 原始图层名称
        
        Returns:
            CSS 注释字符串，泛型名返回空字符串
        """
        if self.is_generic_name(original_name):
            return ""
        
        translated = self.translate(original_name)
        
        if translated == original_name:
            return f"/* {original_name} */"
        
        return f"/* {original_name}: {translated} */"

    def translate_for_alt(self, original_name: str) -> str:
        """
        生成 alt / aria-label 文本
        
        优先返回中文翻译，泛型名返回空字符串。
        """
        if self.is_generic_name(original_name):
            return ""
        return self.translate(original_name)
