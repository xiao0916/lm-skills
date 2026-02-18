#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code Splitter 测试文件

测试内容：
- JSX 解析器功能
- CSS 解析器功能
- 分析器算法
- 组件生成功能

运行方式：
    cd .claude/skills/code-splitter
    python -m pytest tests/test_splitter.py -v
    
    或者：
    python tests/test_splitter.py
"""

import os
import sys
import json
import unittest
from pathlib import Path

# 添加 scripts 目录到 Python 路径
# 确保可以导入 scripts 目录下的模块
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# 导入被测试的模块
try:
    from jsx_parser import JSXParser, parse_jsx, parse_jsx_file, JSXElement
    from css_parser import parse_css, parse_css_to_json
    from analyzer import SplitAnalyzer, analyze, analyze_component_dir
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入模块: {e}")
    MODULES_AVAILABLE = False


# 获取 fixtures 目录路径
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestJSXParser(unittest.TestCase):
    """测试 JSX 解析器"""
    
    @classmethod
    def setUpClass(cls):
        if not MODULES_AVAILABLE:
            cls.skipTest(cls, "模块不可用")
    
    def test_parse_simple_jsx(self):
        """测试解析简单的 JSX"""
        jsx = '<div className={styles["test"]}><span>Hello</span></div>'
        result = parse_jsx(jsx)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "div")
        self.assertEqual(result[0]["className"], "test")
        self.assertEqual(len(result[0]["children"]), 1)
    
    def test_parse_self_closing_tag(self):
        """测试解析自闭合标签"""
        jsx = '<div className={styles["icon"]} />'
        result = parse_jsx(jsx)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "div")
        self.assertEqual(result[0]["className"], "icon")
        self.assertTrue(result[0]["selfClosing"])
    
    def test_parse_attributes(self):
        """测试解析属性"""
        jsx = '<div className={styles["btn"]} role="button" aria-label="点击">Click</div>'
        result = parse_jsx(jsx)
        
        self.assertEqual(result[0]["attributes"]["role"], "button")
        self.assertEqual(result[0]["attributes"]["aria-label"], "点击")
    
    def test_parse_from_file(self):
        """测试从文件解析 JSX"""
        simple_file = FIXTURES_DIR / "simple.jsx"
        if simple_file.exists():
            result = parse_jsx_file(str(simple_file))
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
    
    def test_parse_medium_jsx(self):
        """测试中复杂度的 JSX"""
        medium_file = FIXTURES_DIR / "medium.jsx"
        if medium_file.exists():
            result = parse_jsx_file(str(medium_file))
            self.assertIsInstance(result, list)
            # 应该有一个顶层元素
            self.assertEqual(len(result), 1)
            # 顶层应该是 card-container
            self.assertEqual(result[0]["className"], "card-container")
    
    def test_jsx_element_to_dict(self):
        """测试 JSXElement 转换为字典"""
        elem = JSXElement(tag="div", className="test")
        elem.children.append(JSXElement(tag="span", className="child"))
        
        result = elem.to_dict()
        self.assertEqual(result["tag"], "div")
        self.assertEqual(result["className"], "test")
        self.assertEqual(len(result["children"]), 1)


class TestCSSParser(unittest.TestCase):
    """测试 CSS 解析器"""
    
    @classmethod
    def setUpClass(cls):
        if not MODULES_AVAILABLE:
            cls.skipTest(cls, "模块不可用")
    
    def test_parse_css_file(self):
        """测试解析 CSS 文件"""
        css_file = FIXTURES_DIR / "test.module.css"
        if css_file.exists():
            result = parse_css(str(css_file))
            self.assertIsInstance(result, dict)
            # 检查是否解析到了类
            self.assertIn("root", result)
            self.assertIn("header", result)
            self.assertIn("card", result)
    
    def test_css_properties(self):
        """测试 CSS 属性解析"""
        css_file = FIXTURES_DIR / "test.module.css"
        if css_file.exists():
            result = parse_css(str(css_file))
            
            # 检查 root 类的属性
            root_props = result["root"]["properties"]
            self.assertEqual(root_props["width"], "100px")
            self.assertEqual(root_props["height"], "200px")
    
    def test_css_raw_text(self):
        """测试保留原始 CSS 文本"""
        css_file = FIXTURES_DIR / "test.module.css"
        if css_file.exists():
            result = parse_css(str(css_file))
            
            # 检查是否保留了原始文本
            self.assertIn("raw", result["root"])
            self.assertIn(".root", result["root"]["raw"])


class TestAnalyzer(unittest.TestCase):
    """测试分析器"""
    
    @classmethod
    def setUpClass(cls):
        if not MODULES_AVAILABLE:
            cls.skipTest(cls, "模块不可用")
    
    def test_semantic_classname_analysis(self):
        """测试语义类名分析"""
        jsx = '<div className={styles["btn-primary"]} />'
        element_tree = parse_jsx(jsx)
        css_map = {"btn-primary": {"properties": {}, "raw": ""}}
        
        analyzer = SplitAnalyzer(element_tree, css_map)
        score, semantic_type, prefix = analyzer.analyze_semantic_classname("btn-primary")
        
        self.assertGreater(score, 0)
        self.assertEqual(semantic_type, "button")
        self.assertEqual(prefix, "Btn")
    
    def test_card_semantic_analysis(self):
        """测试卡片类名分析"""
        jsx = '<div className={styles["card-container"]} />'
        element_tree = parse_jsx(jsx)
        css_map = {"card-container": {"properties": {}, "raw": ""}}
        
        analyzer = SplitAnalyzer(element_tree, css_map)
        score, semantic_type, prefix = analyzer.analyze_semantic_classname("card-container")
        
        self.assertGreaterEqual(score, 0.9)
        self.assertEqual(semantic_type, "card")
        self.assertEqual(prefix, "Card")
    
    def test_dom_structure_analysis(self):
        """测试 DOM 结构分析"""
        # 创建一个包裹多个子元素的元素
        jsx = '''
        <div className={styles["container"]}>
            <div className={styles["child1"]} />
            <div className={styles["child2"]} />
            <div className={styles["child3"]} />
            <div className={styles["child4"]} />
            <div className={styles["child5"]} />
            <div className={styles["child6"]} />
        </div>
        '''
        element_tree = parse_jsx(jsx)
        css_map = {}
        
        analyzer = SplitAnalyzer(element_tree, css_map)
        score, reason = analyzer.analyze_dom_structure(element_tree[0])
        
        # 包裹6个子元素应该得到高分
        self.assertGreater(score, 0)
        self.assertIn("6", reason)
    
    def test_full_analysis(self):
        """测试完整的分析流程"""
        medium_file = FIXTURES_DIR / "medium.jsx"
        if not medium_file.exists():
            self.skipTest("medium.jsx 不存在")
        
        element_tree = parse_jsx_file(str(medium_file))
        css_map = {}  # 简化测试，不使用 CSS
        
        result = analyze(element_tree, css_map)
        
        # 检查结果结构
        self.assertIn("candidates", result)
        self.assertIn("summary", result)
        self.assertIn("total_elements", result["summary"])
        
        # 应该检测到一些候选组件
        # card-container, card-header 等应该被识别
        candidates = result["candidates"]
        self.assertIsInstance(candidates, list)
    
    def test_generate_component_name(self):
        """测试组件名生成"""
        jsx = '<div className={styles["daily-card"]} />'
        element_tree = parse_jsx(jsx)
        css_map = {}
        
        analyzer = SplitAnalyzer(element_tree, css_map)
        
        # 测试各种类名的组件名生成
        name1 = analyzer.generate_component_name("daily-card", "Card", "card")
        self.assertEqual(name1, "DailyCard")
        
        name2 = analyzer.generate_component_name("btn-primary", "Btn", "button")
        self.assertEqual(name2, "PrimaryBtn")
        
        name3 = analyzer.generate_component_name("header-main", "Header", "header")
        self.assertEqual(name3, "MainHeader")


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @classmethod
    def setUpClass(cls):
        if not MODULES_AVAILABLE:
            cls.skipTest(cls, "模块不可用")
    
    def test_analyze_component_dir(self):
        """测试分析组件目录"""
        # 使用 fixtures 目录作为测试目录
        # 需要有 index.jsx 和 index.module.css
        fixtures_dir = str(FIXTURES_DIR)
        
        # 检查是否存在必要的文件
        has_jsx = any(f.endswith('.jsx') for f in os.listdir(fixtures_dir))
        
        if has_jsx:
            try:
                result = analyze_component_dir(fixtures_dir)
                self.assertIn("candidates", result)
                self.assertIn("summary", result)
            except FileNotFoundError:
                # 如果没有 index.jsx，会抛出异常，这是预期的
                pass
    
    def test_complex_jsx_analysis(self):
        """测试复杂 JSX 的分析"""
        complex_file = FIXTURES_DIR / "complex.jsx"
        if not complex_file.exists():
            self.skipTest("complex.jsx 不存在")
        
        element_tree = parse_jsx_file(str(complex_file))
        css_map = {}
        
        result = analyze(element_tree, css_map)
        
        # 复杂页面应该有很多元素
        summary = result["summary"]
        self.assertGreater(summary["total_elements"], 10)
        
        # 应该检测到一些候选组件
        candidates = result["candidates"]
        # header, footer, sidebar 等应该被识别
        candidate_names = [c["suggested_name"] for c in candidates]
        
        # 检查是否识别出语义明确的组件
        self.assertTrue(
            any("Header" in name or "Footer" in name or "Card" in name 
                for name in candidate_names),
            f"应该识别出 Header、Footer 或 Card 组件，实际得到: {candidate_names[:5]}"
        )


def run_manual_tests():
    """手动运行测试（不使用 unittest）"""
    print("=" * 60)
    print("Code Splitter 手动测试")
    print("=" * 60)
    
    if not MODULES_AVAILABLE:
        print("错误: 无法导入必要模块，测试中止")
        return False
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试 1: JSX 解析
    print("\n[测试 1] JSX 解析")
    try:
        jsx = '<div className={styles["test"]}><span>Hello</span></div>'
        result = parse_jsx(jsx)
        assert len(result) == 1, "应该有一个顶层元素"
        assert result[0]["tag"] == "div", "标签应该是 div"
        assert result[0]["className"] == "test", "类名应该是 test"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1
    
    # 测试 2: CSS 解析
    print("\n[测试 2] CSS 解析")
    try:
        css_file = FIXTURES_DIR / "test.module.css"
        if css_file.exists():
            result = parse_css(str(css_file))
            assert "root" in result, "应该解析到 root 类"
            assert "card" in result, "应该解析到 card 类"
            print("  ✓ 通过")
            tests_passed += 1
        else:
            print("  ⚠ 跳过: 测试文件不存在")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1
    
    # 测试 3: 语义分析
    print("\n[测试 3] 语义类名分析")
    try:
        jsx = '<div className={styles["btn-primary"]} />'
        element_tree = parse_jsx(jsx)
        css_map = {}
        analyzer = SplitAnalyzer(element_tree, css_map)
        score, semantic_type, prefix = analyzer.analyze_semantic_classname("btn-primary")
        assert score > 0, "应该得到正分数"
        assert semantic_type == "button", "类型应该是 button"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1
    
    # 测试 4: 组件名生成
    print("\n[测试 4] 组件名生成")
    try:
        jsx = '<div />'
        element_tree = parse_jsx(jsx)
        analyzer = SplitAnalyzer(element_tree, {})
        
        name = analyzer.generate_component_name("daily-card", "Card", "card")
        assert name == "DailyCard", f"应该是 DailyCard, 实际得到 {name}"
        
        name = analyzer.generate_component_name("header-main", "Header", "header")
        assert name == "MainHeader", f"应该是 MainHeader, 实际得到 {name}"
        
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1
    
    # 测试 5: 完整分析流程
    print("\n[测试 5] 完整分析流程")
    try:
        medium_file = FIXTURES_DIR / "medium.jsx"
        if medium_file.exists():
            element_tree = parse_jsx_file(str(medium_file))
            result = analyze(element_tree, {})
            assert "candidates" in result, "结果应该包含 candidates"
            assert "summary" in result, "结果应该包含 summary"
            print(f"  ✓ 通过 (检测到 {len(result['candidates'])} 个候选)")
            tests_passed += 1
        else:
            print("  ⚠ 跳过: 测试文件不存在")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print(f"测试完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)
    
    return tests_failed == 0


if __name__ == '__main__':
    # 如果以脚本方式运行，执行手动测试
    if len(sys.argv) > 1 and sys.argv[1] == '--manual':
        success = run_manual_tests()
        sys.exit(0 if success else 1)
    else:
        # 运行 unittest
        unittest.main(verbosity=2)
