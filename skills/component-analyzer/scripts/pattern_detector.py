# -*- coding: utf-8 -*-
"""
重复模式检测器模块

检测组件间的相似模式，识别可复用的组件结构
"""

import re
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict


class PatternDetector:
    """
    组件模式检测器

    用于检测组件间的相似性，识别可提取为公共组件的模式
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """
        初始化模式检测器

        Args:
            similarity_threshold: 相似度阈值，超过此值的组件被视为相似模式
        """
        self.similarity_threshold = similarity_threshold
        self.pattern_counter = 0

    def detect_similar_props(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测具有相似 props 签名的组件

        Args:
            components: 组件列表，每个组件包含 'name' 和 'props' 字段

        Returns:
            具有相似 props 的组件分组列表
        """
        # 按 props 签名分组
        props_groups = defaultdict(list)

        for component in components:
            props = component.get('props', [])
            # 创建标准化签名：排序并转换为元组
            props_signature = tuple(sorted(props))
            props_groups[props_signature].append(component)

        # 筛选出有相似 props 的组（2个及以上组件）
        similar_groups = []
        for props_sig, comps in props_groups.items():
            if len(comps) >= 2:
                similar_groups.append({
                    'type': 'props_similarity',
                    'signature': props_sig,
                    'components': [c['name'] for c in comps],
                    'component_data': comps,
                    'similarity': 1.0  # 完全相同的 props
                })

        return similar_groups

    def detect_similar_structure(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测具有相似 JSX 结构的组件

        Args:
            components: 组件列表，每个组件包含 'name' 和 'jsx_elements' 字段

        Returns:
            具有相似 JSX 结构的组件分组列表
        """
        similar_groups = []
        processed = set()

        for i, comp_a in enumerate(components):
            if comp_a['name'] in processed:
                continue

            similar_comps = [comp_a]
            jsx_a = set(comp_a.get('jsx_elements', []))

            for j, comp_b in enumerate(components[i + 1:], start=i + 1):
                if comp_b['name'] in processed:
                    continue

                jsx_b = set(comp_b.get('jsx_elements', []))
                similarity = self._calculate_jsx_similarity(jsx_a, jsx_b)

                # 如果 JSX 结构相似度超过阈值，视为相似
                if similarity >= 0.6:  # 结构相似度阈值
                    similar_comps.append(comp_b)

            if len(similar_comps) >= 2:
                group_signature = self._generate_structure_signature(similar_comps)
                similar_groups.append({
                    'type': 'structure_similarity',
                    'signature': group_signature,
                    'components': [c['name'] for c in similar_comps],
                    'component_data': similar_comps,
                    'similarity': self._calculate_group_similarity(similar_comps)
                })
                processed.update(c['name'] for c in similar_comps)

        return similar_groups

    def calculate_similarity(self, comp_a: Dict[str, Any], comp_b: Dict[str, Any]) -> float:
        """
        计算两个组件的综合相似度

        相似度计算策略：
        1. Props 签名相似度：40%
        2. JSX 结构相似度：40%
        3. CSS Modules 使用：20%

        Args:
            comp_a: 第一个组件数据
            comp_b: 第二个组件数据

        Returns:
            0.0 到 1.0 之间的相似度分数
        """
        similarity = 0.0

        # 1. Props 签名相似度 (40%)
        props_a = set(comp_a.get('props', []))
        props_b = set(comp_b.get('props', []))

        if props_a == props_b:
            similarity += 0.4
        elif props_a and props_b:
            # 部分匹配
            intersection = len(props_a & props_b)
            union = len(props_a | props_b)
            if union > 0:
                props_similarity = intersection / union
                similarity += props_similarity * 0.4

        # 2. JSX 结构相似度 (40%)
        jsx_a = set(comp_a.get('jsx_elements', []))
        jsx_b = set(comp_b.get('jsx_elements', []))

        jsx_similarity = self._calculate_jsx_similarity(jsx_a, jsx_b)
        similarity += jsx_similarity * 0.4

        # 3. CSS Module 使用 (20%)
        css_module_a = comp_a.get('uses_css_module', False)
        css_module_b = comp_b.get('uses_css_module', False)

        if css_module_a and css_module_b:
            # 都使用 CSS Module
            similarity += 0.2
        elif not css_module_a and not css_module_b:
            # 都不使用 CSS Module
            similarity += 0.1
        # 一个使用一个不使用时，不加这部分分数

        return round(similarity, 2)

    def group_by_pattern(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按模式对组件进行分组

        Args:
            components: 组件列表

        Returns:
            包含所有检测到的模式的分组结果
        """
        patterns = []
        self.pattern_counter = 0

        # 计算所有组件对的相似度
        similarity_matrix = self._build_similarity_matrix(components)

        # 使用聚类算法将相似的组件分组
        clustered_components = self._cluster_components(components, similarity_matrix)

        # 为每个簇生成模式
        for cluster in clustered_components:
            if len(cluster) >= 2:
                self.pattern_counter += 1
                pattern = self._create_pattern(cluster)
                patterns.append(pattern)

        return {
            'patterns': patterns,
            'total_components': len(components),
            'pattern_count': len(patterns),
            'threshold': self.similarity_threshold
        }

    def generate_pattern_report(self, patterns: List[Dict[str, Any]]) -> str:
        """
        生成模式检测报告

        Args:
            patterns: 检测到的模式列表

        Returns:
            格式化的 Markdown 报告
        """
        report_lines = [
            "# 组件模式检测报告",
            "",
            f"**检测阈值**: {self.similarity_threshold}",
            f"**发现模式数**: {len(patterns)}",
            ""
        ]

        if not patterns:
            report_lines.append("未检测到明显的重复模式。")
            return '\n'.join(report_lines)

        for pattern in patterns:
            report_lines.extend([
                f"## 模式 {pattern['id']}",
                "",
                f"**签名**: `{pattern.get('signature', 'N/A')}`",
                f"**相似度**: {pattern.get('similarity', 0):.2%}",
                f"**涉及组件**: {', '.join(pattern.get('components', []))}",
                "",
                f"**建议**: {pattern.get('suggestion', '无')}",
                ""
            ])

        # 添加总体建议
        report_lines.extend([
            "---",
            "",
            "## 总体建议",
            "",
            self._generate_overall_suggestions(patterns),
            ""
        ])

        return '\n'.join(report_lines)

    def _calculate_jsx_similarity(self, jsx_a: Set[str], jsx_b: Set[str]) -> float:
        """
        计算 JSX 元素集合的相似度

        使用 Jaccard 相似度：交集大小 / 并集大小
        """
        if not jsx_a and not jsx_b:
            return 1.0  # 两者都为空，视为完全相似

        if not jsx_a or not jsx_b:
            return 0.0  # 一个为空一个有元素，视为完全不同

        intersection = len(jsx_a & jsx_b)
        union = len(jsx_a | jsx_b)

        return intersection / union if union > 0 else 0.0

    def _generate_structure_signature(self, components: List[Dict[str, Any]]) -> str:
        """
        生成结构签名，用于标识模式
        """
        if not components:
            return "unknown"

        # 使用第一个组件的 JSX 元素类型作为基础签名
        base_comp = components[0]
        jsx_elements = base_comp.get('jsx_elements', [])

        if not jsx_elements:
            return "({ props }) => JSX"

        # 提取主要结构特征
        element_types = []
        for elem in jsx_elements[:5]:  # 取前5个主要元素
            # 简化元素名
            simplified = re.sub(r'[^a-zA-Z]', '', elem.split('.')[-1])
            if simplified:
                element_types.append(simplified)

        props_pattern = self._extract_props_pattern(components)

        return f"({props_pattern}) => <{'/'.join(element_types)}>"

    def _extract_props_pattern(self, components: List[Dict[str, Any]]) -> str:
        """
        从组件列表中提取共同的 props 模式
        """
        if not components:
            return "props"

        common_props = set(components[0].get('props', []))

        for comp in components[1:]:
            props = set(comp.get('props', []))
            common_props &= props

        if common_props:
            return "{ " + ", ".join(sorted(common_props)) + " }"

        return "props"

    def _calculate_group_similarity(self, components: List[Dict[str, Any]]) -> float:
        """
        计算组内所有组件的平均相似度
        """
        if len(components) < 2:
            return 1.0

        total_similarity = 0.0
        pair_count = 0

        for i, comp_a in enumerate(components):
            for comp_b in components[i + 1:]:
                total_similarity += self.calculate_similarity(comp_a, comp_b)
                pair_count += 1

        return round(total_similarity / pair_count, 2) if pair_count > 0 else 1.0

    def _build_similarity_matrix(self, components: List[Dict[str, Any]]) -> List[List[float]]:
        """
        构建组件间的相似度矩阵
        """
        n = len(components)
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]

        for i in range(n):
            matrix[i][i] = 1.0  # 自身相似度为1
            for j in range(i + 1, n):
                similarity = self.calculate_similarity(components[i], components[j])
                matrix[i][j] = similarity
                matrix[j][i] = similarity

        return matrix

    def _cluster_components(self, components: List[Dict[str, Any]],
                           similarity_matrix: List[List[float]]) -> List[List[Dict[str, Any]]]:
        """
        使用层次聚类将相似组件分组

        使用简单的贪心算法：从第一个组件开始，将与它相似的组件加入同一组
        """
        n = len(components)
        if n == 0:
            return []

        visited = [False] * n
        clusters = []

        for i in range(n):
            if visited[i]:
                continue

            cluster = [components[i]]
            visited[i] = True

            for j in range(i + 1, n):
                if not visited[j] and similarity_matrix[i][j] >= self.similarity_threshold:
                    cluster.append(components[j])
                    visited[j] = True

            clusters.append(cluster)

        return clusters

    def _create_pattern(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从组件簇创建模式对象
        """
        self.pattern_counter += 1

        # 生成模式签名
        signature = self._generate_structure_signature(components)

        # 计算组内相似度
        similarity = self._calculate_group_similarity(components)

        # 生成建议
        suggestion = self._generate_suggestion(components, similarity)

        return {
            'id': f'pattern_{self.pattern_counter}',
            'signature': signature,
            'components': [c.get('name', 'Unknown') for c in components],
            'similarity': similarity,
            'suggestion': suggestion,
            'component_count': len(components)
        }

    def _generate_suggestion(self, components: List[Dict[str, Any]],
                            similarity: float) -> str:
        """
        根据相似度生成重构建议
        """
        if similarity >= 0.9:
            return "高度相似，强烈建议提取为公共组件以消除重复代码"
        elif similarity >= 0.75:
            return "可提取为公共组件，通过 props 控制差异"
        elif similarity >= 0.6:
            return "结构相似，考虑使用组合模式或高阶组件"
        else:
            return "存在相似性，建议评估是否需要抽象"

    def _generate_overall_suggestions(self, patterns: List[Dict[str, Any]]) -> str:
        """
        生成总体建议
        """
        total_components = sum(p.get('component_count', 0) for p in patterns)

        suggestions = [
            f"本次检测发现了 **{len(patterns)}** 个重复模式，",
            f"涉及 **{total_components}** 个组件。",
            ""
        ]

        # 按相似度排序
        sorted_patterns = sorted(patterns, key=lambda x: x.get('similarity', 0), reverse=True)

        high_similarity = [p for p in sorted_patterns if p.get('similarity', 0) >= 0.8]
        if high_similarity:
            suggestions.append(f"其中有 **{len(high_similarity)}** 个高相似度模式（≥80%），建议优先处理。")

        suggestions.extend([
            "",
            "**推荐行动：**",
            "1. 优先处理高相似度的组件组（相似度 ≥ 0.8）",
            "2. 评估是否可以通过 props 参数化差异",
            "3. 考虑使用 React 的组合模式提高复用性",
            "4. 提取公共组件后，更新相关测试用例"
        ])

        return '\n'.join(suggestions)

    def set_threshold(self, threshold: float):
        """
        设置相似度阈值

        Args:
            threshold: 新的阈值 (0.0 - 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
        else:
            raise ValueError("阈值必须在 0.0 到 1.0 之间")


def detect_patterns(components: List[Dict[str, Any]],
                   threshold: float = 0.7) -> Dict[str, Any]:
    """
    便捷的接口函数：检测组件中的重复模式

    Args:
        components: 组件列表
        threshold: 相似度阈值

    Returns:
        包含所有检测到的模式的结果字典
    """
    detector = PatternDetector(similarity_threshold=threshold)
    return detector.group_by_pattern(components)


# 示例用法
if __name__ == "__main__":
    # 示例组件数据
    example_components = [
        {
            'name': 'UserCard',
            'props': ['name', 'avatar', 'onClick'],
            'jsx_elements': ['div', 'img', 'h3', 'p', 'button'],
            'uses_css_module': True
        },
        {
            'name': 'ProductCard',
            'props': ['name', 'image', 'price', 'onClick'],
            'jsx_elements': ['div', 'img', 'h3', 'span', 'button'],
            'uses_css_module': True
        },
        {
            'name': 'ArticleCard',
            'props': ['title', 'cover', 'onClick'],
            'jsx_elements': ['div', 'img', 'h3', 'p', 'button'],
            'uses_css_module': True
        },
        {
            'name': 'ComplexChart',
            'props': ['data', 'options'],
            'jsx_elements': ['svg', 'path', 'g', 'rect', 'text'],
            'uses_css_module': False
        }
    ]

    # 检测模式
    detector = PatternDetector(similarity_threshold=0.7)
    result = detector.group_by_pattern(example_components)

    # 生成报告
    report = detector.generate_pattern_report(result['patterns'])
    print(report)
