"""
PSD to Cocos CLI 主入口

提供命令行接口，支持：
- 单个 PSD 文件转换
- 批量目录处理
- 交互式选择
- 失败重试
"""

import os
import sys
import argparse
from pathlib import Path

# 添加 scripts 目录到 path
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

from core.batch_processor import (
    BatchProcessor,
    create_batch_processor,
    InputType,
    BatchSummary
)
from exceptions import PSDToCocosError, InvalidInputError


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器
    
    Returns:
        配置好的 ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='psd-to-cocos',
        description='将 Photoshop PSD 文件转换为 Cocos Creator 布局参考',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转换单个 PSD 文件
  python -m psd_to_cocos convert design.psd

  # 批量处理目录（交互式选择）
  python -m psd_to_cocos convert psd-folder/

  # 批量处理目录（全部转换）
  python -m psd_to_cocos convert psd-folder/ --all

  # 递归扫描子目录
  python -m psd_to_cocos convert psd-folder/ --recursive

  # 指定冲突策略
  python -m psd_to_cocos convert psd-folder/ --all --conflict=skip

  # 重试失败的文件
  python -m psd_to_cocos convert psd-folder/ --retry

  # 详细输出
  python -m psd_to_cocos convert design.psd --verbose
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # convert 命令
    convert_parser = subparsers.add_parser(
        'convert',
        help='转换 PSD 文件为 Cocos 布局',
        description='转换一个或多个 PSD 文件'
    )
    
    convert_parser.add_argument(
        'input',
        help='输入路径（PSD 文件或包含 PSD 的目录）'
    )
    
    convert_parser.add_argument(
        '-o', '--output',
        dest='output_dir',
        default='psd-output',
        help='输出基础目录（默认: psd-output）'
    )
    
    convert_parser.add_argument(
        '-a', '--all',
        dest='select_all',
        action='store_true',
        help='处理所有文件，不提示选择'
    )
    
    convert_parser.add_argument(
        '-r', '--recursive',
        dest='recursive',
        action='store_true',
        default=True,
        help='递归扫描子目录中的 PSD 文件（默认启用）'
    )
    
    convert_parser.add_argument(
        '--no-recursive',
        dest='recursive',
        action='store_false',
        help='不递归扫描子目录'
    )
    
    convert_parser.add_argument(
        '--conflict',
        dest='conflict_strategy',
        choices=['overwrite', 'skip', 'rename', 'ask'],
        default='overwrite',
        help='目录冲突处理策略（默认: overwrite）'
    )
    
    convert_parser.add_argument(
        '--retry',
        dest='retry',
        action='store_true',
        help='重试之前失败的文件'
    )
    
    convert_parser.add_argument(
        '--stop-on-error',
        dest='stop_on_error',
        action='store_true',
        help='遇到错误时停止处理'
    )
    
    convert_parser.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        help='显示详细输出'
    )
    
    convert_parser.add_argument(
        '--non-interactive',
        dest='interactive',
        action='store_false',
        default=True,
        help='非交互模式（自动选择所有文件）'
    )
    
    # version 命令
    version_parser = subparsers.add_parser(
        'version',
        help='显示版本信息'
    )
    
    return parser


def detect_input_type_description(path: str) -> str:
    """获取输入类型的描述
    
    Args:
        path: 输入路径
        
    Returns:
        输入类型描述
    """
    input_type = BatchProcessor.detect_input_type(path)
    
    descriptions = {
        InputType.SINGLE_PSD: "单个 PSD 文件",
        InputType.DIRECTORY: "目录",
        InputType.INVALID: "无效路径"
    }
    
    return descriptions.get(input_type, "未知类型")


def handle_convert_command(args) -> int:
    """处理 convert 命令
    
    Args:
        args: 解析后的命令行参数
        
    Returns:
        退出码（0=成功，1=失败）
    """
    input_path = args.input
    
    # 验证输入
    if not os.path.exists(input_path):
        print(f"错误: 输入路径不存在: {input_path}", file=sys.stderr)
        return 1
    
    input_type = BatchProcessor.detect_input_type(input_path)
    
    if input_type == InputType.INVALID:
        print(f"错误: 无效的输入类型: {input_path}", file=sys.stderr)
        print("请提供 PSD 文件或包含 PSD 的目录", file=sys.stderr)
        return 1
    
    # 显示输入信息
    print(f"输入路径: {input_path}")
    print(f"输入类型: {detect_input_type_description(input_path)}")
    print(f"输出目录: {args.output_dir}")
    print(f"冲突策略: {args.conflict_strategy}")
    
    if args.retry:
        print("模式: 重试失败的文件")
    elif input_type == InputType.DIRECTORY:
        if args.select_all or not args.interactive:
            print("模式: 批量处理（全部文件）")
        else:
            print("模式: 批量处理（交互式选择）")
        
        if args.recursive:
            print("扫描: 递归扫描子目录")
    
    print()
    
    try:
        # 创建处理器
        processor = create_batch_processor(
            output_dir=args.output_dir,
            verbose=args.verbose,
            conflict_strategy=args.conflict_strategy,
            interactive=args.interactive
        )
        
        # 执行处理
        summary = processor.process(
            input_path=input_path,
            recursive=args.recursive,
            select_all=args.select_all,
            retry=args.retry,
            stop_on_error=args.stop_on_error
        )
        
        # 打印汇总
        BatchProcessor.print_summary(summary)
        
        # 根据结果返回退出码
        if summary.failed > 0:
            return 1 if summary.success == 0 else 0  # 部分成功也算成功
        
        return 0
        
    except InvalidInputError as e:
        print(f"输入错误: {e}", file=sys.stderr)
        return 1
    except PSDToCocosError as e:
        print(f"转换错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130  # 标准中断退出码
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_version_command(args) -> int:
    """处理 version 命令
    
    Args:
        args: 解析后的命令行参数
        
    Returns:
        退出码
    """
    print("PSD to Cocos Converter")
    print("版本: 1.0.0")
    print()
    print("依赖工具:")
    print("  - psd-layer-reader: 导出 PSD 图层结构")
    print("  - psd-slicer: 导出 PNG 切片")
    print()
    print("更多信息: https://github.com/your-repo/psd-to-cocos")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口

    Args:
        argv: 命令行参数列表，默认为 sys.argv[1:]

    Returns:
        退出码
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        return 0
    
    if args.command == 'convert':
        return handle_convert_command(args)
    elif args.command == 'version':
        return handle_version_command(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
