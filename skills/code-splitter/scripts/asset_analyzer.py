#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源文件分析器 - 扫描目录中的图片资源

用于分析指定目录下的所有图片文件，返回文件名和路径等元数据。
支持 CLI 运行和作为模块导入使用。
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any


# 支持的图片格式扩展名
SUPPORTED_IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'
}


def analyze_assets(directory: str) -> Dict[str, Any]:
    """
    扫描指定目录，返回所有图片文件的信息

    参数:
        directory (str): 要扫描的目录路径

    返回:
        Dict[str, Any]: 包含图片列表和统计信息的字典
            - images: 图片列表，每项包含 filename 和 path
            - count: 图片总数
            - directory: 扫描的目录路径

    示例:
        >>> result = analyze_assets("./assets")
        >>> print(result)
        {
            "images": [
                {"filename": "bg.png", "path": "assets/bg.png"},
                {"filename": "logo.jpg", "path": "assets/logo.jpg"}
            ],
            "count": 2,
            "directory": "./assets"
        }
    """
    # 转换为 Path 对象并解析为绝对路径
    dir_path = Path(directory).resolve()

    # 检查目录是否存在
    if not dir_path.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")

    if not dir_path.is_dir():
        raise NotADirectoryError(f"指定路径不是目录: {directory}")

    # 存储找到的图片文件
    images = []

    # 递归遍历目录
    for file_path in dir_path.rglob('*'):
        # 只处理文件（跳过目录）
        if file_path.is_file():
            # 获取文件扩展名（转换为小写进行比较）
            ext = file_path.suffix.lower()

            # 检查是否支持的图片格式
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                # 计算相对路径（相对于输入目录）
                try:
                    relative_path = file_path.relative_to(dir_path)
                except ValueError:
                    # 如果无法计算相对路径，使用文件名
                    relative_path = file_path.name

                images.append({
                    "filename": file_path.name,
                    "path": str(relative_path).replace('\\', '/'),
                    "full_path": str(file_path).replace('\\', '/'),
                    "extension": ext[1:],  # 去掉前导点号
                    "size": file_path.stat().st_size  # 文件大小（字节）
                })

    # 按文件名排序
    images.sort(key=lambda x: x["filename"])

    return {
        "images": images,
        "count": len(images),
        "directory": str(dir_path).replace('\\', '/')
    }


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    格式化输出结果

    参数:
        result (Dict[str, Any]): analyze_assets 返回的结果
        output_format (str): 输出格式，支持 "json" 或 "text"

    返回:
        str: 格式化后的输出字符串
    """
    if output_format.lower() == "json":
        return json.dumps(result, indent=2, ensure_ascii=False)

    # 文本格式
    lines = [
        f"目录: {result['directory']}",
        f"图片数量: {result['count']}",
        "-" * 50,
    ]

    for img in result["images"]:
        lines.append(f"  [IMG] {img['filename']}")
        lines.append(f"     路径: {img['path']}")
        lines.append(f"     大小: {img['size']:,} 字节")
        lines.append("")

    return "\n".join(lines)


def main():
    """
    CLI 入口函数
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="扫描目录中的图片资源文件",
        epilog="示例: python asset_analyzer.py ./assets"
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="要扫描的目录路径（默认为当前目录）"
    )

    parser.add_argument(
        "-f", "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认为 json）"
    )

    parser.add_argument(
        "-o", "--output",
        help="输出文件路径（默认为标准输出）"
    )

    args = parser.parse_args()

    try:
        # 执行扫描
        result = analyze_assets(args.directory)

        # 格式化输出
        output = format_output(result, args.format)

        # 输出到文件或标准输出
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"结果已保存到: {args.output}")
        else:
            print(output)

        # 返回退出码（找到图片返回 0，未找到返回 1）
        return 0 if result["count"] > 0 else 1

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except NotADirectoryError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
