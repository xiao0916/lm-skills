# -*- coding: utf-8 -*-
"""
PSD to Cocos Creator 布局转换工具

这是技能的唯一入口，支持单文件转换和目录批量扫描。
支持递归搜索 PSD 文件并自动命名输出目录。
"""

import os
import sys
import argparse
from pathlib import Path

# 将 scripts 目录加入搜索路径以便导入本地模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processor import ConversionProcessor
from utils import logger

def main():
    parser = argparse.ArgumentParser(
        description='将 PSD 设计稿转换为 Cocos Creator 布局参考',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python psd_to_cocos.py design.psd
  python psd_to_cocos.py ./designs/ -o ./output/ -r
        """
    )
    parser.add_argument('input', help='输入 PSD 文件路径或包含 PSD 的目录路径')
    parser.add_argument('-o', '--output', default='./output/', help='输出根目录 (默认为 ./output/)')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归搜索子目录中的 PSD 文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细调试信息')
    
    args = parser.parse_args()

    if args.verbose:
        import logging
        logger.setLevel(logging.DEBUG)

    input_path = os.path.abspath(args.input)
    output_base_dir = os.path.abspath(args.output)

    if not os.path.exists(input_path):
        logger.error(f"找不到输入路径: {input_path}")
        sys.exit(1)

    processor = ConversionProcessor(output_base_dir)
    
    if os.path.isfile(input_path):
        # 处理单文件
        processor.process_single_psd(input_path)
    else:
        # 批量处理
        processor.process_batch(input_path, recursive=args.recursive)

if __name__ == "__main__":
    main()
