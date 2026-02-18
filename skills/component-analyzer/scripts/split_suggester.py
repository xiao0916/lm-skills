# -*- coding: utf-8 -*-
"""
拆分建议生成器 - Split Suggester

基于组件分析结果生成拆分建议，支持 JSON 和 Markdown 输出。

主要功能：
1. 提取子组件建议 - 识别可复用的 JSX 结构
2. 合并组件建议 - 发现可合并的相似组件
3. Props 重构建议 - 统一和优化组件接口
4. 样式分离建议 - 提取共享样式
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Suggestion:
    """单个拆分建议的数据结构"""
    id: int
    type: str  # 'extract', 'merge', 'props', 'style'
    target: List[str]
    description: str
    priority: str  # 'high', 'medium', 'low'
    details: Dict[str, Any] = field(default_factory=dict)
    code_example: Optional[str] = None


class SplitSuggester:
    """拆分建议生成器主类"""
    
    def __init__(self):
        self.suggestions: List[Suggestion] = []
        self.suggestion_id_counter = 0
    
    def _get_next_id(self) -> int:
        """获取下一个建议 ID"""
        self.suggestion_id_counter += 1
        return self.suggestion_id_counter
    
    def generate_suggestions(
        self,
        dependency_graph: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> List[Suggestion]:
        """
        主函数：基于依赖图和模式检测结果生成所有拆分建议
        
        参数：
            dependency_graph: 组件依赖图
                {
                    "components": [...],
                    "dependencies": [...],
                    "imports": {...}
                }
            patterns: 模式检测结果
                {
                    "duplicated_jsx": [...],
                    "similar_components": [...],
                    "shared_props": [...],
                    "shared_styles": [...]
                }
        
        返回：
            List[Suggestion]: 所有生成的建议列表
        """
        self.suggestions = []
        
        # 1. 生成组件提取建议（基于重复 JSX 结构）
        if "duplicated_jsx" in patterns:
            for pattern in patterns["duplicated_jsx"]:
                suggestion = self.suggest_component_extraction(pattern)
                if suggestion:
                    self.suggestions.append(suggestion)
        
        # 2. 生成组件合并建议（基于相似组件）
        if "similar_components" in patterns:
            for pattern in patterns["similar_components"]:
                suggestion = self.suggest_component_merge(pattern)
                if suggestion:
                    self.suggestions.append(suggestion)
        
        # 3. 生成 Props 重构建议（基于共享 props）
        if "shared_props" in patterns:
            for shared_props_pattern in patterns["shared_props"]:
                suggestion = self.suggest_props_refactor(shared_props_pattern)
                if suggestion:
                    self.suggestions.append(suggestion)
        
        # 4. 生成样式分离建议（基于共享样式）
        if "shared_styles" in patterns:
            for style_pattern in patterns["shared_styles"]:
                suggestion = self._suggest_style_extraction(style_pattern)
                if suggestion:
                    self.suggestions.append(suggestion)
        
        # 5. 基于依赖图生成额外的架构建议
        if dependency_graph:
            arch_suggestions = self._generate_architecture_suggestions(dependency_graph)
            self.suggestions.extend(arch_suggestions)
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        self.suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))
        
        return self.suggestions
    
    def suggest_component_extraction(self, pattern: Dict[str, Any]) -> Optional[Suggestion]:
        """
        建议提取子组件
        
        当组件内部有重复的 JSX 结构时，建议提取为独立的子组件。
        
        参数：
            pattern: 重复 JSX 模式
                {
                    "structure": str,
                    "components": List[str],
                    "occurrences": int,
                    "complexity_score": float
                }
        
        返回：
            Suggestion 或 None（如果不需要建议）
        """
        components = pattern.get("components", [])
        occurrences = pattern.get("occurrences", 0)
        complexity = pattern.get("complexity_score", 0)
        structure = pattern.get("structure", "")
        
        if len(components) < 2 or occurrences < 2:
            return None
        
        # 根据重复次数和复杂度确定优先级
        if occurrences >= 5 and complexity > 0.7:
            priority = "high"
        elif occurrences >= 3 and complexity > 0.5:
            priority = "medium"
        else:
            priority = "low"
        
        # 生成组件名称建议
        suggested_name = self._generate_component_name(structure)
        
        description = (
            f"在 {len(components)} 个组件中发现重复的 JSX 结构（出现 {occurrences} 次）。"
            f"建议提取为独立的 '{suggested_name}' 子组件以提高代码复用性。"
        )
        
        code_example = self._generate_extraction_example(suggested_name, structure)
        
        return Suggestion(
            id=self._get_next_id(),
            type="extract",
            target=components,
            description=description,
            priority=priority,
            details={
                "occurrences": occurrences,
                "complexity_score": complexity,
                "suggested_name": suggested_name,
                "structure_preview": structure[:200] + "..." if len(structure) > 200 else structure
            },
            code_example=code_example
        )
    
    def suggest_component_merge(self, pattern: Dict[str, Any]) -> Optional[Suggestion]:
        """
        建议合并组件
        
        当多个组件功能相似、props 接口相近时，建议合并为一个通用组件。
        
        参数：
            pattern: 相似组件模式
                {
                    "components": List[str],
                    "similarity_score": float,
                    "common_props": List[str],
                    "differences": List[str]
                }
        
        返回：
            Suggestion 或 None
        """
        components = pattern.get("components", [])
        similarity = pattern.get("similarity_score", 0)
        common_props = pattern.get("common_props", [])
        differences = pattern.get("differences", [])
        
        if len(components) < 2:
            return None
        
        # 相似度越高，优先级越高
        if similarity >= 0.8:
            priority = "high"
        elif similarity >= 0.6:
            priority = "medium"
        elif similarity >= 0.4:
            priority = "low"
        else:
            return None  # 相似度太低，不建议合并
        
        suggested_name = self._generate_merged_component_name(components)
        
        description = (
            f"组件 {', '.join(components)} 具有 {similarity:.1%} 的相似度，"
            f"共享 {len(common_props)} 个相同的 props。"
            f"建议合并为通用的 '{suggested_name}' 组件，通过配置参数处理差异。"
        )
        
        code_example = self._generate_merge_example(suggested_name, components, common_props, differences)
        
        return Suggestion(
            id=self._get_next_id(),
            type="merge",
            target=components,
            description=description,
            priority=priority,
            details={
                "similarity_score": similarity,
                "common_props": common_props,
                "differences": differences,
                "suggested_name": suggested_name
            },
            code_example=code_example
        )
    
    def suggest_props_refactor(self, components_pattern: Dict[str, Any]) -> Optional[Suggestion]:
        """
        建议重构 props 接口
        
        当多个组件有相似的 props 定义时，建议统一接口或提取公共类型。
        
        参数：
            components_pattern: 共享 props 模式
                {
                    "components": List[str],
                    "shared_props": List[str],
                    "props_variations": Dict[str, List[str]]
                }
        
        返回：
            Suggestion 或 None
        """
        components = components_pattern.get("components", [])
        shared_props = components_pattern.get("shared_props", [])
        variations = components_pattern.get("props_variations", {})
        
        if len(components) < 2 or len(shared_props) < 2:
            return None
        
        # 根据共享 props 数量和组件数量确定优先级
        if len(shared_props) >= 5 and len(components) >= 3:
            priority = "high"
        elif len(shared_props) >= 3:
            priority = "medium"
        else:
            priority = "low"
        
        description = (
            f"{len(components)} 个组件共享 {len(shared_props)} 个相同的 props 定义："
            f"{', '.join(shared_props[:5])}{'...' if len(shared_props) > 5 else ''}。"
            f"建议创建统一的 Props 接口或基类。"
        )
        
        code_example = self._generate_props_refactor_example(shared_props, variations)
        
        return Suggestion(
            id=self._get_next_id(),
            type="props",
            target=components,
            description=description,
            priority=priority,
            details={
                "shared_props": shared_props,
                "props_variations": variations,
                "affected_component_count": len(components)
            },
            code_example=code_example
        )
    
    def _suggest_style_extraction(self, style_pattern: Dict[str, Any]) -> Optional[Suggestion]:
        """
        建议提取共享样式（内部方法）
        
        参数：
            style_pattern: 共享样式模式
                {
                    "components": List[str],
                    "shared_styles": List[str],
                    "style_type": str  # 'css', 'inline', 'styled-components'
                }
        
        返回：
            Suggestion 或 None
        """
        components = style_pattern.get("components", [])
        shared_styles = style_pattern.get("shared_styles", [])
        style_type = style_pattern.get("style_type", "css")
        
        if len(shared_styles) < 2:
            return None
        
        if len(components) >= 5 and len(shared_styles) >= 5:
            priority = "high"
        elif len(components) >= 3:
            priority = "medium"
        else:
            priority = "low"
        
        description = (
            f"{len(components)} 个组件共享 {len(shared_styles)} 条样式规则。"
            f"建议提取到公共样式文件或使用 CSS-in-JS 方案统一管理。"
        )
        
        code_example = self._generate_style_extraction_example(style_type, shared_styles)
        
        return Suggestion(
            id=self._get_next_id(),
            type="style",
            target=components,
            description=description,
            priority=priority,
            details={
                "shared_styles": shared_styles,
                "style_type": style_type,
                "style_count": len(shared_styles)
            },
            code_example=code_example
        )
    
    def _generate_architecture_suggestions(
        self,
        dependency_graph: Dict[str, Any]
    ) -> List[Suggestion]:
        """基于依赖图生成架构层面的建议"""
        suggestions = []
        
        components = dependency_graph.get("components", [])
        dependencies = dependency_graph.get("dependencies", [])
        
        # 检测循环依赖
        cycles = self._detect_circular_dependencies(dependencies)
        if cycles:
            for cycle in cycles:
                suggestion = Suggestion(
                    id=self._get_next_id(),
                    type="architecture",
                    target=cycle,
                    description=f"检测到循环依赖: {' → '.join(cycle)} → {cycle[0]}。建议重构组件关系，消除循环依赖。",
                    priority="high",
                    details={"cycle": cycle}
                )
                suggestions.append(suggestion)
        
        # 检测过深的组件层级
        deep_paths = self._detect_deep_nesting(dependencies)
        for path in deep_paths:
            suggestion = Suggestion(
                id=self._get_next_id(),
                type="architecture",
                target=path,
                description=f"组件层级过深（{len(path)} 层）: {' → '.join(path)}。建议扁平化组件结构。",
                priority="medium",
                details={"depth": len(path), "path": path}
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _detect_circular_dependencies(self, dependencies: List[Dict[str, Any]]) -> List[List[str]]:
        """检测循环依赖"""
        cycles = []
        graph = {}
        
        for dep in dependencies:
            source = dep.get("source")
            target = dep.get("target")
            if source and target:
                if source not in graph:
                    graph[source] = []
                graph[source].append(target)
        
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        result = dfs(neighbor)
                        if result:
                            return result
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        return path[cycle_start:]
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        for node in graph:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    cycles.append(cycle)
        
        return cycles
    
    def _detect_deep_nesting(self, dependencies: List[Dict[str, Any]], max_depth: int = 5) -> List[List[str]]:
        """检测过深的组件层级"""
        deep_paths = []
        graph = {}
        
        for dep in dependencies:
            source = dep.get("source")
            target = dep.get("target")
            if source and target:
                if source not in graph:
                    graph[source] = []
                graph[source].append(target)
        
        def dfs(node, path, depth):
            if depth > max_depth:
                deep_paths.append(path[:])
                return
            
            if node in graph:
                for neighbor in graph[node]:
                    path.append(neighbor)
                    dfs(neighbor, path, depth + 1)
                    path.pop()
        
        for root in graph:
            dfs(root, [root], 1)
        
        return deep_paths
    
    def _generate_component_name(self, structure: str) -> str:
        """根据结构生成建议的组件名称"""
        # 简单启发式：基于结构特征命名
        if "button" in structure.lower():
            return "SharedButton"
        elif "card" in structure.lower():
            return "CardContainer"
        elif "list" in structure.lower():
            return "ListItem"
        elif "input" in structure.lower() or "field" in structure.lower():
            return "FormField"
        elif "modal" in structure.lower() or "dialog" in structure.lower():
            return "ModalWrapper"
        else:
            return "SharedComponent"
    
    def _generate_merged_component_name(self, components: List[str]) -> str:
        """根据组件列表生成合并后的名称"""
        if not components:
            return "UnifiedComponent"
        
        # 寻找共同前缀
        common_prefix = components[0]
        for comp in components[1:]:
            i = 0
            while i < len(common_prefix) and i < len(comp) and common_prefix[i] == comp[i]:
                i += 1
            common_prefix = common_prefix[:i]
        
        if common_prefix and len(common_prefix) >= 2:
            return f"{common_prefix}Base"
        else:
            return "UnifiedComponent"
    
    def _generate_extraction_example(self, component_name: str, structure: str) -> str:
        """生成组件提取的代码示例"""
        return f"""// 提取前的代码（重复）
function ComponentA() {{
  return (
    <div className="wrapper">
      <span className="content">内容</span>
    </div>
  );
}}

// 提取后的代码
import {{ {component_name} }} from './components/{component_name}';

function ComponentA() {{
  return (
    <{component_name}>
      <span className="content">内容</span>
    </{component_name}>
  );
}}

// {component_name}.jsx
export function {component_name}({{ children }}) {{
  return (
    <div className="wrapper">
      {{children}}
    </div>
  );
}}"""
    
    def _generate_merge_example(
        self,
        component_name: str,
        components: List[str],
        common_props: List[str],
        differences: List[str]
    ) -> str:
        """生成组件合并的代码示例"""
        props_def = ', '.join([f'{prop}: any' for prop in common_props[:3]])
        variant_prop = "variant" if differences else ""
        
        return f"""// 合并前的多个组件
function {components[0]}(props) {{ return <div>...</div>; }}
function {components[1] if len(components) > 1 else 'ComponentB'}(props) {{ return <div>...</div>; }}

// 合并后的统一组件
interface {component_name}Props {{
  {props_def}
  {f"variant: '{' | '.join(differences[:3])}';" if differences else ""}
}}

export function {component_name}({{ {', '.join(common_props[:3])}{', variant' if differences else ''} }}: {component_name}Props) {{
  return (
    <div className={{`base-class {{variant}}`}}>
      {{/* 根据 variant 渲染不同内容 */}}
    </div>
  );
}}"""
    
    def _generate_props_refactor_example(
        self,
        shared_props: List[str],
        variations: Dict[str, List[str]]
    ) -> str:
        """生成 props 重构的代码示例"""
        props_list = '\n  '.join([f'{prop}: string;' for prop in shared_props[:5]])
        
        return f"""// 重构前 - 分散的 props 定义
// ComponentA: {{ {', '.join(shared_props[:3])} }}
// ComponentB: {{ {', '.join(shared_props[:3])} }}

// 重构后 - 统一的 Props 接口
interface BaseComponentProps {{
  {props_list}
}}

// 各组件继承基接口
interface ComponentAProps extends BaseComponentProps {{
  // ComponentA 特有属性
}}

interface ComponentBProps extends BaseComponentProps {{
  // ComponentB 特有属性
}}"""
    
    def _generate_style_extraction_example(self, style_type: str, shared_styles: List[str]) -> str:
        """生成样式提取的代码示例"""
        if style_type == "styled-components":
            return """// 提取前 - 重复样式
const ButtonA = styled.button`
  padding: 8px 16px;
  border-radius: 4px;
`;

const ButtonB = styled.button`
  padding: 8px 16px;
  border-radius: 4px;
`;

// 提取后 - 共享样式
const BaseButton = styled.button`
  padding: 8px 16px;
  border-radius: 4px;
`;

const ButtonA = styled(BaseButton)`
  background: blue;
`;

const ButtonB = styled(BaseButton)`
  background: red;
`;"""
        else:
            return """/* 提取前 - 重复样式 */
.component-a { padding: 8px; margin: 4px; }
.component-b { padding: 8px; margin: 4px; }

/* 提取后 - 共享样式 */
.shared-base {
  padding: 8px;
  margin: 4px;
}

.component-a { /* 特有样式 */ }
.component-b { /* 特有样式 */ }"""
    
    def format_output(
        self,
        suggestions: List[Suggestion],
        format_type: str,
        dependency_graph: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        格式化输出建议
        
        参数：
            suggestions: 建议列表
            format_type: 输出格式 ('json' 或 'markdown')
            dependency_graph: 可选的依赖图信息
        
        返回：
            str: 格式化后的输出字符串
        """
        if format_type.lower() == "json":
            return self._format_json(suggestions, dependency_graph)
        elif format_type.lower() == "markdown":
            return self._format_markdown(suggestions, dependency_graph)
        else:
            raise ValueError(f"不支持的格式类型: {format_type}")
    
    def _format_json(
        self,
        suggestions: List[Suggestion],
        dependency_graph: Optional[Dict[str, Any]]
    ) -> str:
        """格式化为 JSON 输出"""
        # 统计信息
        summary = {
            "total_components": len(dependency_graph.get("components", [])) if dependency_graph else 0,
            "patterns_detected": len(set(s.type for s in suggestions)),
            "suggestions_count": len(suggestions),
            "by_priority": {
                "high": len([s for s in suggestions if s.priority == "high"]),
                "medium": len([s for s in suggestions if s.priority == "medium"]),
                "low": len([s for s in suggestions if s.priority == "low"])
            },
            "by_type": {
                "extract": len([s for s in suggestions if s.type == "extract"]),
                "merge": len([s for s in suggestions if s.type == "merge"]),
                "props": len([s for s in suggestions if s.type == "props"]),
                "style": len([s for s in suggestions if s.type == "style"]),
                "architecture": len([s for s in suggestions if s.type == "architecture"])
            }
        }
        
        # 建议列表
        suggestions_data = []
        for s in suggestions:
            s_dict = asdict(s)
            suggestions_data.append(s_dict)
        
        output = {
            "summary": summary,
            "suggestions": suggestions_data,
            "generated_at": datetime.now().isoformat(),
            "dependency_graph": dependency_graph or {}
        }
        
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    def _format_markdown(
        self,
        suggestions: List[Suggestion],
        dependency_graph: Optional[Dict[str, Any]]
    ) -> str:
        """格式化为 Markdown 输出"""
        lines = []
        
        # 标题
        lines.append("# 组件拆分建议报告\n")
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # 概览
        lines.append("## 概览\n")
        
        total_components = len(dependency_graph.get("components", [])) if dependency_graph else 0
        lines.append(f"- **组件总数**: {total_components}")
        lines.append(f"- **检测到的模式**: {len(set(s.type for s in suggestions))}")
        lines.append(f"- **拆分建议总数**: {len(suggestions)}\n")
        
        # 优先级统计
        high_count = len([s for s in suggestions if s.priority == "high"])
        medium_count = len([s for s in suggestions if s.priority == "medium"])
        low_count = len([s for s in suggestions if s.priority == "low"])
        
        lines.append("### 按优先级分布\n")
        lines.append(f"- 高优先级: {high_count}")
        lines.append(f"- 中优先级: {medium_count}")
        lines.append(f"- 低优先级: {low_count}\n")
        
        # 按类型统计
        lines.append("### 按类型分布\n")
        type_names = {
            "extract": "组件提取",
            "merge": "组件合并",
            "props": "Props 重构",
            "style": "样式分离",
            "architecture": "架构优化"
        }
        type_counts = {}
        for s in suggestions:
            type_counts[s.type] = type_counts.get(s.type, 0) + 1
        for type_key, count in sorted(type_counts.items()):
            lines.append(f"- {type_names.get(type_key, type_key)}: {count}")
        lines.append("")
        
        # 详细建议
        lines.append("---\n")
        lines.append("## 详细建议\n")
        
        priority_labels = {"high": "[高]", "medium": "[中]", "low": "[低]"}
        type_labels = {
            "extract": "组件提取",
            "merge": "组件合并", 
            "props": "Props 重构",
            "style": "样式分离",
            "architecture": "架构优化"
        }
        
        for i, s in enumerate(suggestions, 1):
            lines.append(f"### 建议 {i}: {type_labels.get(s.type, s.type)}\n")
            lines.append(f"**优先级**: {priority_labels.get(s.priority, s.priority)}\n")
            lines.append(f"**目标组件**: {', '.join(s.target)}\n")
            lines.append(f"**描述**: {s.description}\n")
            
            # 详细信息
            if s.details:
                lines.append("**详细信息**:")
                for key, value in s.details.items():
                    if isinstance(value, list):
                        lines.append(f"  - {key}: {', '.join(str(v) for v in value[:5])}{'...' if len(value) > 5 else ''}")
                    else:
                        lines.append(f"  - {key}: {value}")
                lines.append("")
            
            # 代码示例
            if s.code_example:
                lines.append("**参考实现**:")
                lines.append("```jsx")
                lines.append(s.code_example)
                lines.append("```\n")
            
            lines.append("---\n")
        
        # 依赖图
        if dependency_graph:
            lines.append("## 依赖图\n")
            components = dependency_graph.get("components", [])
            dependencies = dependency_graph.get("dependencies", [])
            
            lines.append(f"### 组件列表 ({len(components)} 个)\n")
            for comp in components:
                lines.append(f"- `{comp}`")
            lines.append("")
            
            if dependencies:
                lines.append(f"### 依赖关系 ({len(dependencies)} 条)\n")
                for dep in dependencies:
                    source = dep.get("source", "?")
                    target = dep.get("target", "?")
                    lines.append(f"- `{source}` → `{target}`")
                lines.append("")
        
        return "\n".join(lines)


# 便捷函数接口（供外部直接调用）

def generate_suggestions(
    dependency_graph: Dict[str, Any],
    patterns: Dict[str, Any]
) -> List[Suggestion]:
    """
    基于分析结果生成拆分建议
    
    这是一个便捷函数，创建 Suggester 实例并调用 generate_suggestions。
    
    参数：
        dependency_graph: 组件依赖图
        patterns: 模式检测结果
    
    返回：
        List[Suggestion]: 建议列表
    
    示例：
        >>> suggestions = generate_suggestions(
        ...     dependency_graph={"components": ["A", "B"], "dependencies": []},
        ...     patterns={"duplicated_jsx": [...]}
        ... )
    """
    suggester = SplitSuggester()
    return suggester.generate_suggestions(dependency_graph, patterns)


def suggest_component_extraction(pattern: Dict[str, Any]) -> Optional[Suggestion]:
    """
    建议提取子组件（便捷函数）
    
    参数：
        pattern: 重复 JSX 模式
    
    返回：
        Suggestion 或 None
    """
    suggester = SplitSuggester()
    return suggester.suggest_component_extraction(pattern)


def suggest_component_merge(pattern: Dict[str, Any]) -> Optional[Suggestion]:
    """
    建议合并组件（便捷函数）
    
    参数：
        pattern: 相似组件模式
    
    返回：
        Suggestion 或 None
    """
    suggester = SplitSuggester()
    return suggester.suggest_component_merge(pattern)


def suggest_props_refactor(components_pattern: Dict[str, Any]) -> Optional[Suggestion]:
    """
    建议重构 props（便捷函数）
    
    参数：
        components_pattern: 共享 props 模式
    
    返回：
        Suggestion 或 None
    """
    suggester = SplitSuggester()
    return suggester.suggest_props_refactor(components_pattern)


def format_output(
    suggestions: List[Suggestion],
    format_type: str,
    dependency_graph: Optional[Dict[str, Any]] = None
) -> str:
    """
    格式化输出建议（便捷函数）
    
    参数：
        suggestions: 建议列表
        format_type: 输出格式 ('json' 或 'markdown')
        dependency_graph: 可选的依赖图
    
    返回：
        str: 格式化后的字符串
    
    示例：
        >>> output = format_output(suggestions, "json")
        >>> print(output)
    """
    suggester = SplitSuggester()
    return suggester.format_output(suggestions, format_type, dependency_graph)


if __name__ == "__main__":
    # 示例用法和测试
    print("=" * 60)
    print("拆分建议生成器 - Split Suggester")
    print("=" * 60)
    
    # 模拟测试数据
    test_dependency_graph = {
        "components": ["Button", "Card", "Header", "Footer", "List"],
        "dependencies": [
            {"source": "Card", "target": "Button"},
            {"source": "Header", "target": "Button"},
            {"source": "List", "target": "Card"}
        ],
        "imports": {}
    }
    
    test_patterns = {
        "duplicated_jsx": [
            {
                "structure": "<div className='wrapper'><span>{children}</span></div>",
                "components": ["Card", "Modal"],
                "occurrences": 5,
                "complexity_score": 0.8
            }
        ],
        "similar_components": [
            {
                "components": ["PrimaryButton", "SecondaryButton"],
                "similarity_score": 0.85,
                "common_props": ["onClick", "disabled", "size"],
                "differences": ["variant"]
            }
        ],
        "shared_props": [
            {
                "components": ["Card", "Modal", "Panel"],
                "shared_props": ["title", "children", "className"],
                "props_variations": {}
            }
        ],
        "shared_styles": [
            {
                "components": ["Button", "Input"],
                "shared_styles": ["padding: 8px", "border-radius: 4px"],
                "style_type": "css"
            }
        ]
    }
    
    # 生成建议
    suggester = SplitSuggester()
    suggestions = suggester.generate_suggestions(test_dependency_graph, test_patterns)
    
    print(f"\n生成了 {len(suggestions)} 条建议\n")
    
    # 输出 JSON 格式
    print("=" * 60)
    print("JSON 格式输出预览:")
    print("=" * 60)
    json_output = suggester.format_output(suggestions, "json", test_dependency_graph)
    print(json_output[:1000] + "..." if len(json_output) > 1000 else json_output)
    
    print("\n" + "=" * 60)
    print("Markdown 格式输出预览:")
    print("=" * 60)
    md_output = suggester.format_output(suggestions, "markdown", test_dependency_graph)
    print(md_output[:1500] + "..." if len(md_output) > 1500 else md_output)
