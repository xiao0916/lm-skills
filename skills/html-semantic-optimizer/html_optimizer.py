#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML 语义化优化核心模块

提供HTML语义化转换功能，将通用标签（div、span）自动转换为
语义化HTML5标签（header、nav、main、article、button等）。
"""

import json
import re
import io
import sys

from bs4 import BeautifulSoup

# Python 2/3 兼容
PY2 = sys.version_info[0] == 2
if PY2:
    string_types = (str, unicode)
else:
    string_types = (str,)


class SemanticRule(object):
    """
    语义化规则类 - 表示一条从类名到语义化标签的映射规则
    """

    def __init__(self, name, keywords, target_tag, priority=0):
        self.name = name
        self.keywords = keywords
        self.target_tag = target_tag
        self.priority = priority

    def matches_class(self, class_names):
        """检查给定的类名列表是否匹配当前规则"""
        for cls in class_names:
            for keyword in self.keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, cls, re.IGNORECASE):
                    return True
        return False

    def __repr__(self):
        return "<SemanticRule '{0}' -> <{1}> (priority: {2})>".format(
            self.name, self.target_tag, self.priority)


class RuleEngine(object):
    """
    规则引擎类 - 管理和执行语义化规则匹配
    """

    def __init__(self, rules=None):
        self.rules = []
        if rules:
            self.load_rules(rules)

    def load_rules(self, rules_config):
        """从配置列表加载规则"""
        for rule_data in rules_config:
            rule = SemanticRule(
                name=rule_data["name"],
                keywords=rule_data["keywords"],
                target_tag=rule_data["target_tag"],
                priority=rule_data.get("priority", 0)
            )
            self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def load_from_file(self, filepath):
        """从JSON配置文件加载规则"""
        with io.open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.load_rules(config.get('rules', []))

    def find_matching_rule(self, class_names):
        """查找匹配给定类名的最佳规则"""
        for rule in self.rules:
            if rule.matches_class(class_names):
                return rule
        return None


class DOMTransformer(object):
    """
    DOM转换器类 - 解析HTML并根据规则引擎匹配结果转换标签类型
    """

    # 需要跳过的标签列表
    EXCLUDED_TAGS = {'script', 'style', 'html', 'body', 'head', 'meta', 'link'}

    def __init__(self, rule_engine):
        self.rule_engine = rule_engine

    def transform(self, html_content):
        """转换HTML内容"""
        soup = BeautifulSoup(html_content, 'html.parser')

        for element in soup.find_all():
            if element.name in self.EXCLUDED_TAGS:
                continue

            class_attr = element.get('class', [])
            if isinstance(class_attr, string_types):
                class_names = class_attr.split()
            else:
                class_names = list(class_attr)

            rule = self.rule_engine.find_matching_rule(class_names)
            if rule:
                self._transform_element(element, rule.target_tag, soup)

        return soup.prettify()

    def _transform_element(self, element, new_tag, soup):
        """执行元素转换"""
        if element.name == new_tag:
            return

        new_element = soup.new_tag(new_tag)

        # 复制所有原始属性
        for key, value in element.attrs.items():
            new_element[key] = value

        # 自动为<a>标签添加href属性
        if new_tag == 'a' and not new_element.get('href'):
            new_element['href'] = '#'

        # 自动为<button>标签添加type属性
        if new_tag == 'button' and not new_element.get('type'):
            new_element['type'] = 'button'

        # 复制子元素
        for child in list(element.children):
            new_element.append(child)

        element.replace_with(new_element)


def optimize_html(html_content, rules_config=None):
    """
    优化HTML内容（便捷函数）
    
    Args:
        html_content: 原始HTML字符串
        rules_config: 规则配置列表，为None则使用默认规则
    
    Returns:
        优化后的HTML字符串
    """
    if rules_config is None:
        # 使用内置默认规则
        rules_config = [
            {"name": "button", "keywords": ["btn", "button", "按钮"], "target_tag": "button", "priority": 10},
            {"name": "link", "keywords": ["link", "链接", "a-btn", "nav-link"], "target_tag": "a", "priority": 10},
            {"name": "navigation", "keywords": ["nav", "navbar", "导航", "menu"], "target_tag": "nav", "priority": 5},
            {"name": "header", "keywords": ["header", "头部", "top-bar"], "target_tag": "header", "priority": 5},
            {"name": "footer", "keywords": ["footer", "底部", "bottom"], "target_tag": "footer", "priority": 5},
            {"name": "main", "keywords": ["main", "content", "主内容"], "target_tag": "main", "priority": 5},
        ]
    
    engine = RuleEngine(rules_config)
    transformer = DOMTransformer(engine)
    return transformer.transform(html_content)
