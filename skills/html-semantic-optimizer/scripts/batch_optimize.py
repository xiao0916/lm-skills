#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量HTML语义化优化脚本

批量处理多个HTML文件或整个目录。
"""

import argparse
import sys
import os
import io
import subprocess
from multiprocessing import Pool


def find_html_files(directory, recursive=False):
    """查找HTML文件"""
    html_files = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            if file.endswith('.html'):
                html_files.append(os.path.join(directory, file))
    return sorted(html_files)


def optimize_single_file(args):
    """优化单个文件"""
    input_file, output_dir, rules_path, dry_run = args
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    optimize_script = os.path.join(script_dir, 'optimize.py')
    
    # 确定输出路径
    if output_dir:
        output_path = os.path.join(output_dir, os.path.basename(input_file))
    else:
        output_path = None
    
    # 构建命令
    cmd = [sys.executable, optimize_script, input_file]
    
    if output_path:
        cmd.extend(['-o', output_path])
    if rules_path:
        cmd.extend(['-r', rules_path])
    if dry_run:
        cmd.append('-d')
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, input_file, result.stdout.strip()
        else:
            return False, input_file, result.stderr.strip()
    except Exception as e:
        return False, input_file, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='批量HTML语义化优化',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 处理单个目录
  python batch_optimize.py /path/to/html/files/
  
  # 递归处理目录
  python batch_optimize.py /path/to/html/files/ --recursive
  
  # 指定输出目录
  python batch_optimize.py /input/dir/ -o /output/dir/
  
  # 并行处理
  python batch_optimize.py /input/dir/ -o /output/dir/ --workers 4
        '''
    )
    
    parser.add_argument('input', help='输入目录或文件')
    parser.add_argument('-o', '--output', help='输出目录（默认覆盖原文件）')
    parser.add_argument('-r', '--rules', help='自定义规则JSON文件')
    parser.add_argument('-d', '--dry-run', action='store_true', help='试运行模式')
    parser.add_argument('--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('-w', '--workers', type=int, default=1, help='并行工作数（默认1）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细输出')
    
    args = parser.parse_args()
    
    input_path = args.input
    
    # 收集要处理的文件
    if os.path.isfile(input_path):
        files = [input_path]
    elif os.path.isdir(input_path):
        files = find_html_files(input_path, args.recursive)
        if not files:
            print('错误: 目录中未找到HTML文件: ' + input_path)
            sys.exit(1)
    else:
        print('错误: 路径不存在: ' + input_path)
        sys.exit(1)
    
    # 创建输出目录
    if args.output:
        os.makedirs(args.output, exist_ok=True)
    
    print('找到 ' + str(len(files)) + ' 个HTML文件')
    print('开始处理...\n')
    
    # 准备任务参数
    task_args = [(f, args.output, args.rules, args.dry_run) for f in files]
    
    # 处理文件
    success_count = 0
    fail_count = 0
    
    if args.workers > 1:
        # 并行处理
        with Pool(args.workers) as pool:
            results = pool.map(optimize_single_file, task_args)
    else:
        # 串行处理
        results = [optimize_single_file(arg) for arg in task_args]
    
    # 输出结果
    for success, file_path, message in results:
        if success:
            success_count += 1
            if args.verbose:
                print('[成功] ' + file_path + ': ' + message)
            else:
                print('[成功] ' + file_path)
        else:
            fail_count += 1
            print('[失败] ' + file_path + ': ' + message)
    
    # 输出统计
    print('\n处理完成: 成功 ' + str(success_count) + ' 个, 失败 ' + str(fail_count) + ' 个')
    
    if fail_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
