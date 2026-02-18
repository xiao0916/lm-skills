#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
组件分析器测试套件

测试覆盖：
- React AST 解析器 (react_ast_parser)
- 依赖图构建 (dependency_graph)
- 模式检测 (pattern_detector)
- 分析器集成 (analyze_components)

运行方式:
    py -3 tests/test_splitter.py
    py -3 tests/test_splitter.py -v  # 详细模式
"""

from __future__ import print_function
import unittest
import sys
import os
import json

# 添加 scripts 目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(SCRIPT_DIR, '..', 'scripts')
sys.path.insert(0, SKILL_DIR)

# 导入被测试的模块
from react_ast_parser import (
    parse_react_file,
    parse_imports,
    parse_exports,
    parse_props,
    parse_jsx_elements,
    detect_css_module,
    extract_component_name
)
from dependency_graph import analyze_directory, build_dependency_graph, detect_circular_dependencies
from pattern_detector import PatternDetector, detect_patterns


class TestReactASTParser(unittest.TestCase):
    """测试 React AST 解析器"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试数据"""
        cls.fixtures_dir = os.path.join(SCRIPT_DIR, 'fixtures')
        cls.simple_file = os.path.join(cls.fixtures_dir, 'simple.jsx')
        cls.medium_file = os.path.join(cls.fixtures_dir, 'medium.jsx')
        cls.complex_file = os.path.join(cls.fixtures_dir, 'complex.jsx')
    
    def test_parse_simple_component(self):
        """测试解析简单组件"""
        result = parse_react_file(self.simple_file)
        
        # 验证基本字段
        self.assertIn('file_path', result)
        self.assertIn('component_name', result)
        self.assertIn('imports', result)
        self.assertIn('exports', result)
        self.assertIn('props', result)
        self.assertIn('jsx_elements', result)
        
        # 验证组件名
        self.assertEqual(result['component_name'], 'Simple')
        
        # 验证导入
        self.assertTrue(len(result['imports']) > 0)
        import_sources = [imp.get('source') for imp in result['imports']]
        self.assertIn('react', import_sources)
        
        # 验证导出
        self.assertTrue(len(result['exports']) > 0)
        has_default = any(e.get('type') == 'default' for e in result['exports'])
        self.assertTrue(has_default)
        
        # 验证 JSX 元素
        self.assertTrue(len(result['jsx_elements']) > 0)
        
        # 无错误
        self.assertNotIn('error', result)
    
    def test_parse_medium_component(self):
        """测试解析中等复杂度组件"""
        result = parse_react_file(self.medium_file)
        
        self.assertEqual(result['component_name'], 'Medium')
        
        # 验证 props
        self.assertTrue(len(result['props']) > 0)
        props_names = result['props']
        self.assertIn('title', props_names)
        self.assertIn('description', props_names)
        self.assertIn('onClick', props_names)
        
        # 验证 JSX 元素（解析器提取顶层元素）
        jsx_count = len(result['jsx_elements'])
        self.assertGreaterEqual(jsx_count, 1, 
            f"Expected at least 1 JSX element, got {jsx_count}")
    
    def test_parse_complex_component(self):
        """测试解析复杂组件"""
        result = parse_react_file(self.complex_file)
        
        self.assertEqual(result['component_name'], 'Complex')
        
        # 验证 JSX 元素（解析器提取顶层元素）
        jsx_count = len(result['jsx_elements'])
        self.assertGreaterEqual(jsx_count, 1, 
            f"Expected at least 1 JSX element, got {jsx_count}")
    
    def test_css_module_detection(self):
        """测试 CSS Module 检测"""
        result = parse_react_file(self.simple_file)
        
        # 应该检测到 CSS Module
        self.assertIsNotNone(result['css_module_import'])
        self.assertIn('.module.css', result['css_module_import'])
    
    def test_parse_imports_function(self):
        """测试 parse_imports 函数"""
        test_content = '''
import React from 'react';
import { useState, useEffect } from 'react';
import * as Utils from './utils';
import styles from './index.module.css';
import './global.css';
'''
        imports = parse_imports(test_content)
        
        self.assertEqual(len(imports), 5)
        
        # 检查默认导入
        react_import = next((imp for imp in imports if imp.get('source') == 'react' and 'default' in imp), None)
        self.assertIsNotNone(react_import)
        
        # 检查命名导入
        named_import = next((imp for imp in imports if 'named' in imp), None)
        self.assertIsNotNone(named_import)
        
        # 检查命名空间导入
        namespace_import = next((imp for imp in imports if 'namespace' in imp), None)
        self.assertIsNotNone(namespace_import)
    
    def test_parse_exports_function(self):
        """测试 parse_exports 函数"""
        test_content = '''
export default MyComponent;
export const Helper = () => {};
export function util() {}
export { Another };
'''
        exports = parse_exports(test_content)
        
        self.assertTrue(len(exports) > 0)
        
        # 检查默认导出
        has_default = any(e.get('type') == 'default' for e in exports)
        self.assertTrue(has_default)
        
        # 检查命名导出
        named_count = sum(1 for e in exports if e.get('type') == 'named')
        self.assertGreaterEqual(named_count, 2)


class TestDependencyGraph(unittest.TestCase):
    """测试依赖图构建"""
    
    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = os.path.join(SCRIPT_DIR, 'fixtures')
    
    def test_analyze_directory(self):
        """测试目录分析功能"""
        result = analyze_directory(self.fixtures_dir)
        
        # 验证返回结构
        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        self.assertIn('cycles', result)
        self.assertIn('entry_point', result)
        
        # 验证节点数量
        self.assertEqual(len(result['nodes']), 3)  # simple, medium, complex
        
        # 验证节点内容
        node_ids = [node['id'] for node in result['nodes']]
        self.assertIn('simple', node_ids)
        self.assertIn('medium', node_ids)
        self.assertIn('complex', node_ids)
    
    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        # 创建一个无循环的图
        simple_graph = {
            'nodes': [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}],
            'edges': [
                {'from': 'A', 'to': 'B'},
                {'from': 'B', 'to': 'C'}
            ]
        }
        cycles = detect_circular_dependencies(simple_graph)
        self.assertEqual(len(cycles), 0)
        
        # 创建一个有循环的图
        cyclic_graph = {
            'nodes': [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}],
            'edges': [
                {'from': 'A', 'to': 'B'},
                {'from': 'B', 'to': 'C'},
                {'from': 'C', 'to': 'A'}
            ]
        }
        cycles = detect_circular_dependencies(cyclic_graph)
        self.assertGreater(len(cycles), 0)


class TestPatternDetector(unittest.TestCase):
    """测试模式检测器"""

    def __init__(self, methodName='runTest'):
        super(TestPatternDetector, self).__init__(methodName)
        self.detector = None

    def setUp(self):
        self.detector = PatternDetector(similarity_threshold=0.7)
    
    def test_similar_props_detection(self):
        """测试相似 props 检测"""
        components = [
            {'name': 'CardA', 'props': ['title', 'image', 'onClick']},
            {'name': 'CardB', 'props': ['title', 'image', 'onClick']},
            {'name': 'CardC', 'props': ['title', 'image']},
        ]
        
        patterns = self.detector.detect_similar_props(components)
        
        # 应该检测到 CardA 和 CardB 的相似性
        self.assertTrue(len(patterns) > 0)
    
    def test_similarity_calculation(self):
        """测试相似度计算"""
        comp_a = {
            'name': 'A',
            'props': ['title', 'image'],
            'jsx_elements': ['div', 'img', 'h3'],
            'uses_css_module': True
        }
        comp_b = {
            'name': 'B',
            'props': ['title', 'image'],
            'jsx_elements': ['div', 'img', 'h3'],
            'uses_css_module': True
        }
        
        similarity = self.detector.calculate_similarity(comp_a, comp_b)
        self.assertGreaterEqual(similarity, 0.9)  # 应该非常相似
        self.assertLessEqual(similarity, 1.0)
    
    def test_detect_patterns_interface(self):
        """测试 detect_patterns 接口函数"""
        components = [
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
        ]
        
        result = detect_patterns(components, threshold=0.5)
        
        self.assertIn('patterns', result)
        self.assertIn('total_components', result)
        self.assertEqual(result['total_components'], 2)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = os.path.join(SCRIPT_DIR, 'fixtures')
    
    def test_full_analysis_pipeline(self):
        """测试完整分析流程"""
        # 步骤 1: 解析组件文件
        simple_result = parse_react_file(os.path.join(self.fixtures_dir, 'simple.jsx'))
        medium_result = parse_react_file(os.path.join(self.fixtures_dir, 'medium.jsx'))
        complex_result = parse_react_file(os.path.join(self.fixtures_dir, 'complex.jsx'))
        
        # 验证解析成功
        for result in [simple_result, medium_result, complex_result]:
            self.assertNotIn('error', result)
            self.assertIsNotNone(result['component_name'])
        
        # 步骤 2: 构建依赖图
        dep_graph = analyze_directory(self.fixtures_dir)
        self.assertEqual(len(dep_graph['nodes']), 3)
        
        # 步骤 3: 准备组件数据用于模式检测
        components_data = [
            {
                'name': simple_result['component_name'],
                'props': simple_result['props'],
                'jsx_elements': [elem.get('type', '') for elem in simple_result['jsx_elements']],
                'uses_css_module': bool(simple_result.get('css_module_import'))
            },
            {
                'name': medium_result['component_name'],
                'props': medium_result['props'],
                'jsx_elements': [elem.get('type', '') for elem in medium_result['jsx_elements']],
                'uses_css_module': bool(medium_result.get('css_module_import'))
            },
            {
                'name': complex_result['component_name'],
                'props': complex_result['props'],
                'jsx_elements': [elem.get('type', '') for elem in complex_result['jsx_elements']],
                'uses_css_module': bool(complex_result.get('css_module_import'))
            }
        ]
        
        # 步骤 4: 检测模式
        patterns_result = detect_patterns(components_data, threshold=0.5)
        self.assertIn('patterns', patterns_result)
        
        print("\n[Ji Cheng] Test completed!")
        print("- Parsed %d components" % len(components_data))
        print("- Dependency graph nodes: %d" % len(dep_graph['nodes']))
        print("- Detected patterns: %d" % patterns_result['pattern_count'])


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""
    
    def test_parse_nonexistent_file(self):
        """测试解析不存在的文件"""
        result = parse_react_file('/nonexistent/file.jsx')
        self.assertIn('error', result)
    
    def test_empty_directory(self):
        """测试空目录分析"""
        empty_dir = os.path.join(SCRIPT_DIR, 'fixtures', 'empty')
        os.makedirs(empty_dir, exist_ok=True)
        
        result = analyze_directory(empty_dir)
        self.assertEqual(len(result['nodes']), 0)
        self.assertEqual(len(result['edges']), 0)
        
        # 清理
        os.rmdir(empty_dir)


def print_test_summary(result):
    """打印测试摘要"""
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print("运行测试数: %d" % result.testsRun)
    print("成功: %d" % (result.testsRun - len(result.failures) - len(result.errors)))
    print("失败: %d" % len(result.failures))
    print("错误: %d" % len(result.errors))
    print("跳过: %d" % len(result.skipped))
    print("=" * 60)

    if result.wasSuccessful():
        print("[PASS] 所有测试通过!")
    else:
        print("[FAIL] 部分测试失败")

    return result.wasSuccessful()


if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestReactASTParser))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyGraph))
    suite.addTests(loader.loadTestsFromTestCase(TestPatternDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印摘要
    success = print_test_summary(result)
    
    # 返回退出码
    sys.exit(0 if success else 1)
