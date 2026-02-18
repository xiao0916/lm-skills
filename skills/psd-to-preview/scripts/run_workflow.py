#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSD 到预览页面一键转换脚本

简化版工作流脚本，专为 AI 模型设计，减少理解难度。

使用方法：
  python run_workflow.py <psd文件> <输出目录>

示例：
  python run_workflow.py assets/design.psd verify-flow/verify-028
  
警告说明：
  - 输出目录建议使用语义化名称（如 verify-028, design-v1）
  - 不要在输出目录路径末尾添加 "/preview"
  - 脚本会自动创建 preview/ 子目录
  - 错误示例：verify-030/preview
  - 正确示例：verify-030
  
   这个脚本会自动执行三个步骤：
      1. psd-layer-reader - 图层解析（输出 JSON）
      2. psd-slicer - 切片导出
      3. psd-json-preview - 代码生成（预览 + React + Vue）
"""


import os
import sys
import subprocess
from pathlib import Path


def main():
    # 参数检查
    if len(sys.argv) != 3:
        print("用法: python run_workflow.py <psd文件> <输出目录>")
        print("\n示例:")
        print("  python run_workflow.py assets/design.psd verify-flow/verify-028")
        print("\n注意：不要在输出目录路径末尾添加 '/preview'")
        print("  错误: verify-030/preview")
        print("  正确: verify-030")
        sys.exit(1)
    
    psd_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    # 验证 PSD 文件
    if not psd_file.exists():
        print("PSD 文件不存在: {}".format(psd_file))
        sys.exit(1)
    
    # 智能处理输出目录路径
    # 如果用户指定的路径末尾是 "preview"，自动调整到父目录
    if output_dir.name.lower() == "preview":
        print("检测到输出目录末尾是 'preview'")
        original_output = output_dir
        output_dir = output_dir.parent
        print("自动调整输出目录：{} -> {}".format(original_output, output_dir))
        print("脚本会自动创建 preview/ 子目录，无需在路径中指定")
        print()
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    sliced_dir = output_dir / "sliced-images"
    layer_json = output_dir / "layer-tree.json"
    preview_dir = output_dir / "preview"
    
    # 获取技能脚本路径
    script_base = Path(__file__).parent.parent.parent
    slicer_script = script_base / "psd-slicer/scripts/export_slices.py"
    reader_script = script_base / "psd-layer-reader/scripts/psd_layers.py"
    preview_script = script_base / "psd-json-preview/scripts/generate_preview.py"
    
    print("=" * 60)
    print("PSD 到预览页面转换工作流")
    print("=" * 60)
    print("PSD 文件: {}".format(psd_file))
    print("输出目录: {}".format(output_dir))
    print()
    
    # 步骤 1：图层解析
    print("【步骤 1/3】图层解析 (psd-layer-reader)")
    print("-" * 60)
    cmd1 = [
        sys.executable, str(reader_script),
        "--psd", str(psd_file),
        "--output", str(layer_json)
    ]
    print("执行命令: {}".format(" ".join(cmd1)))
    result1 = subprocess.run(cmd1, capture_output=True, text=True)
    if result1.returncode != 0:
        print("图层解析失败:\n{}".format(result1.stderr))
        sys.exit(1)
    print(result1.stdout)
    print("步骤 1 完成\n")
    
    # 步骤 2：切片导出
    print("【步骤 2/3】切片导出 (psd-slicer)")
    print("-" * 60)
    cmd2 = [
        sys.executable, str(slicer_script),
        "--psd", str(psd_file),
        "--output", str(sliced_dir),
        # "--mapping-json", str(layer_json)
    ]
    print("执行命令: {}".format(" ".join(cmd2)))
    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    if result2.returncode != 0:
        print("切片导出失败:\n{}".format(result2.stderr))
        sys.exit(1)
    print(result2.stdout)
    print("步骤 2 完成\n")
    
    # 步骤 3：代码生成
    print("【步骤 3/3】代码生成 (psd-json-preview)")
    print("-" * 60)
    cmd3 = [
        sys.executable, str(preview_script),
        "--json", str(layer_json),
        "--images", str(sliced_dir),
        "--out", str(preview_dir),
        "--generate-react",
        "--generate-vue",
        "--component-name", "PsdComponent",
        "--preserve-names"
    ]
    print("执行命令: {}".format(" ".join(cmd3)))
    result3 = subprocess.run(cmd3, capture_output=True, text=True)
    if result3.returncode != 0:
        print("预览生成失败:\n{}".format(result3.stderr))
        sys.exit(1)
    print(result3.stdout)
    print("步骤 3: 代码生成完成（HTML预览 + React组件 + Vue组件）\n")
    
    print("=" * 60)
    print("工作流完成！")
    print("=" * 60)
    print("\n输出文件：")
    print("  - 切片图片: {}/".format(sliced_dir))
    print("  - 图层数据: {}".format(layer_json))
    print("  - 预览页面: {}/index.html".format(preview_dir))
    print("  - React 组件: {}/react-component/index.jsx".format(preview_dir))
    print("  - Vue 组件: {}/vue-component/PsdComponent.vue".format(preview_dir))
    print("\n在浏览器中打开预览: {}/index.html".format(preview_dir))
    print("React 组件使用: import PsdComponent from './react-component';")


if __name__ == "__main__":
    main()
