"""
PSD to Cocos 批量处理器

处理目录级别的 PSD 批量转换，支持：
- 输入类型检测（单个 PSD vs 目录）
- 递归扫描目录中的 PSD 文件
- 交互式选择界面
- 批量执行转换并显示进度
- 失败记录和重试机制
"""

import os
import json
import sys
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

from core.orchestrator import Orchestrator, ConflictStrategy, ConversionResult
from utils.filename_normalizer import normalize_psd_filename
from utils.progress import RichProgressDisplay, BatchProgressController
from utils.reporter import ResultReporter, SummaryStats, FileResult, create_reporter
from utils.logger import Logger, get_logger
from exceptions import PSDToCocosError, InvalidInputError


class InputType(Enum):
    """输入类型枚举"""
    SINGLE_PSD = "single_psd"      # 单个 PSD 文件
    DIRECTORY = "directory"         # 包含 PSD 文件的目录
    INVALID = "invalid"             # 无效输入


class ProcessingStatus(Enum):
    """处理状态枚举"""
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class ProcessingResult:
    """单个文件处理结果"""
    file_path: str
    status: ProcessingStatus
    output_dir: Optional[str] = None
    error_message: str = ""
    retry_count: int = 0


@dataclass
class BatchSummary:
    """批量处理汇总结果"""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[ProcessingResult] = field(default_factory=list)
    failed_files_path: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        """计算处理持续时间"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class BatchProcessor:
    """批量处理器
    
    负责：
    - 检测输入类型（单个 PSD vs 目录）
    - 扫描目录中的所有 PSD 文件
    - 批量执行转换
    - 显示进度和汇总结果
    - 记录失败的文件并支持重试
    """
    
    # 默认输出目录名
    DEFAULT_OUTPUT_DIR = "psd-output"
    
    # 失败记录文件名
    FAILED_RECORD_FILENAME = ".failed.json"
    
    def __init__(
        self,
        orchestrator: Optional[Orchestrator] = None,
        output_base_dir: Optional[str] = None,
        verbose: bool = False,
        conflict_strategy: ConflictStrategy = ConflictStrategy.OVERWRITE,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
        interactive: bool = True,
        enable_progress: bool = True,
        console = None,
        logger: Optional[Logger] = None
    ):
        """初始化批量处理器

        Args:
            orchestrator: 转换协调器实例
            output_base_dir: 输出基础目录
            verbose: 是否输出详细日志
            conflict_strategy: 目录冲突处理策略
            progress_callback: 进度回调函数 (step_name, current_step, total_steps)
            interactive: 是否启用交互式选择（默认 True）
            enable_progress: 是否启用 Rich 进度显示
            console: Rich Console 实例
            logger: 日志记录器实例，如果为 None 则使用默认实例
        """
        # 初始化日志记录器
        import logging
        self.logger = logger or get_logger(
            level=logging.DEBUG if verbose else logging.INFO,
            verbose=verbose
        )
        self.logger.debug("BatchProcessor 初始化完成")

        self.orchestrator = orchestrator or Orchestrator(
            verbose=verbose,
            conflict_strategy=conflict_strategy,
            enable_progress=enable_progress,
            console=console,
            logger=self.logger
        )
        self.output_base_dir = output_base_dir or self.DEFAULT_OUTPUT_DIR
        self.verbose = verbose
        self.conflict_strategy = conflict_strategy
        self.progress_callback = progress_callback
        self.interactive = interactive
        self.enable_progress = enable_progress

        # 初始化进度显示和报告器
        self.progress_display = RichProgressDisplay(console=console, enabled=enable_progress)
        self.reporter = create_reporter(console=console)
    
    def _log(self, message: str) -> None:
        """输出日志（兼容性方法，委托给 logger）"""
        self.logger.debug(message)
    
    def _report_progress(self, file_name: str, current: int, total: int, status: str) -> None:
        """报告进度
        
        Args:
            file_name: 当前处理的文件名
            current: 当前文件索引（从1开始）
            total: 总文件数
            status: 当前状态
        """
        if self.progress_callback:
            self.progress_callback(file_name, current, total, status)
    
    @staticmethod
    def detect_input_type(path: str) -> InputType:
        """检测输入类型
        
        Args:
            path: 输入路径
            
        Returns:
            InputType 枚举值
        """
        if not os.path.exists(path):
            return InputType.INVALID
        
        if os.path.isfile(path) and path.lower().endswith('.psd'):
            return InputType.SINGLE_PSD
        
        if os.path.isdir(path):
            return InputType.DIRECTORY
        
        return InputType.INVALID
    
    @staticmethod
    def find_psd_files(directory: str, recursive: bool = True) -> List[str]:
        """扫描目录中的所有 PSD 文件
        
        Args:
            directory: 要扫描的目录
            recursive: 是否递归扫描子目录
            
        Returns:
            PSD 文件路径列表（按字母顺序排序）
        """
        psd_files = []
        directory = os.path.abspath(directory)
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.psd'):
                        psd_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if file.lower().endswith('.psd'):
                    psd_files.append(os.path.join(directory, file))
        
        # 按字母顺序排序
        psd_files.sort()
        return psd_files
    
    def _get_output_dir(self, psd_path: str) -> str:
        """根据 PSD 文件路径生成输出目录
        
        Args:
            psd_path: PSD 文件路径
            
        Returns:
            输出目录路径
        """
        psd_filename = os.path.basename(psd_path)
        normalized_name = normalize_psd_filename(psd_filename)
        return os.path.join(self.output_base_dir, normalized_name)
    
    def _interactive_select(self, psd_files: List[str]) -> List[str]:
        """交互式选择要处理的文件
        
        Args:
            psd_files: 所有可用的 PSD 文件列表
            
        Returns:
            用户选择的文件列表
        """
        if not psd_files:
            return []
        
        print("\n发现以下 PSD 文件：")
        print("-" * 60)
        
        for i, file_path in enumerate(psd_files, 1):
            file_name = os.path.basename(file_path)
            rel_path = os.path.relpath(file_path)
            print(f"  [{i}] {file_name}")
            if self.verbose:
                print(f"      路径: {rel_path}")
        
        print("-" * 60)
        print("选择要处理的文件：")
        print("  [a] 全部处理")
        print("  [q] 取消")
        print("  [数字] 输入数字选择特定文件（如：1,3,5 或 1-3）")
        
        while True:
            try:
                choice = input("\n请输入选择: ").strip().lower()
                
                if choice == 'q':
                    print("操作已取消")
                    return []
                
                if choice == 'a':
                    return psd_files
                
                # 解析选择
                selected_indices = self._parse_selection(choice, len(psd_files))
                if selected_indices:
                    return [psd_files[i - 1] for i in selected_indices]
                
                print("无效选择，请重新输入")
                
            except (KeyboardInterrupt, EOFError):
                print("\n操作已取消")
                return []
    
    def _parse_selection(self, choice: str, max_count: int) -> List[int]:
        """解析用户的选择字符串
        
        Args:
            choice: 用户输入的选择字符串
            max_count: 最大文件数
            
        Returns:
            选中的索引列表（1-based）
        """
        selected = set()
        
        for part in choice.split(','):
            part = part.strip()
            
            # 处理范围（如：1-3）
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    start = int(start.strip())
                    end = int(end.strip())
                    
                    if start < 1 or end > max_count or start > end:
                        continue
                    
                    selected.update(range(start, end + 1))
                except ValueError:
                    continue
            else:
                # 处理单个数字
                try:
                    num = int(part)
                    if 1 <= num <= max_count:
                        selected.add(num)
                except ValueError:
                    continue
        
        return sorted(list(selected))
    
    def _load_failed_record(self, directory: str) -> Dict[str, Any]:
        """加载失败记录文件
        
        Args:
            directory: 包含失败记录文件的目录
            
        Returns:
            失败记录数据
        """
        record_path = os.path.join(directory, self.FAILED_RECORD_FILENAME)
        
        if os.path.exists(record_path):
            try:
                with open(record_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return {"timestamp": datetime.now().isoformat(), "failed_files": []}
    
    def _save_failed_record(self, directory: str, failed_results: List[ProcessingResult]) -> str:
        """保存失败记录文件
        
        Args:
            directory: 保存失败记录文件的目录
            failed_results: 失败的处理结果列表
            
        Returns:
            保存的文件路径
        """
        record_path = os.path.join(directory, self.FAILED_RECORD_FILENAME)

        # 确保目录存在
        os.makedirs(directory, exist_ok=True)

        record = {
            "timestamp": datetime.now().isoformat(),
            "failed_files": [
                {
                    "path": result.file_path,
                    "error": result.error_message,
                    "retry_count": result.retry_count
                }
                for result in failed_results
            ]
        }
        
        with open(record_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        return record_path
    
    def process_single(self, psd_path: str) -> ProcessingResult:
        """处理单个 PSD 文件

        Args:
            psd_path: PSD 文件路径

        Returns:
            ProcessingResult 处理结果
        """
        file_name = os.path.basename(psd_path)
        output_dir = self._get_output_dir(psd_path)

        self.logger.info(f"处理文件: {file_name}")
        self.logger.debug(f"输出目录: {output_dir}")

        try:
            # 检查输出目录是否已存在（SKIP 策略）
            if self.conflict_strategy == ConflictStrategy.SKIP and os.path.exists(output_dir):
                self.logger.info(f"输出目录已存在，跳过: {output_dir}")
                return ProcessingResult(
                    file_path=psd_path,
                    status=ProcessingStatus.SKIPPED,
                    output_dir=output_dir,
                    error_message="输出目录已存在"
                )

            # 执行转换
            self.logger.log_step_start(f"转换 {file_name}")
            result = self.orchestrator.convert(psd_path, output_dir)

            if result.success:
                self.logger.log_step_complete(f"转换 {file_name}", success=True)
                return ProcessingResult(
                    file_path=psd_path,
                    status=ProcessingStatus.SUCCESS,
                    output_dir=output_dir
                )
            else:
                self.logger.error(f"转换失败: {file_name} - {result.message}")
                return ProcessingResult(
                    file_path=psd_path,
                    status=ProcessingStatus.FAILED,
                    error_message=result.message
                )

        except PSDToCocosError as e:
            self.logger.error(f"处理失败: {file_name} - {str(e)}")
            return ProcessingResult(
                file_path=psd_path,
                status=ProcessingStatus.FAILED,
                error_message=str(e)
            )
        except Exception as e:
            self.logger.exception(f"处理时发生异常: {file_name} - {str(e)}")
            return ProcessingResult(
                file_path=psd_path,
                status=ProcessingStatus.FAILED,
                error_message=f"未知错误: {str(e)}"
            )
    
    def process_batch(
        self,
        psd_files: List[str],
        stop_on_error: bool = False
    ) -> BatchSummary:
        """批量处理 PSD 文件

        Args:
            psd_files: 要处理的 PSD 文件列表
            stop_on_error: 遇到错误时是否停止

        Returns:
            BatchSummary 汇总结果
        """
        self.logger.info(f"开始批量处理，共 {len(psd_files)} 个文件")

        summary = BatchSummary(
            total=len(psd_files),
            start_time=datetime.now()
        )

        # 准备 FileResult 列表用于报告
        file_results: List[FileResult] = []

        with self.progress_display.batch_progress(len(psd_files), "批量处理 PSD") as batch_controller:
            for i, psd_path in enumerate(psd_files, 1):
                file_name = os.path.basename(psd_path)

                self.logger.info(f"处理进度 [{i}/{len(psd_files)}]: {file_name}")

                # 报告进度
                self._report_progress(file_name, i, len(psd_files), "processing")
                batch_controller.start_file(file_name)

                # 记录开始时间
                file_start_time = datetime.now()

                # 处理文件
                result = self.process_single(psd_path)
                summary.results.append(result)

                # 计算耗时
                file_duration = (datetime.now() - file_start_time).total_seconds()

                # 更新统计
                status = "success"
                if result.status == ProcessingStatus.SUCCESS:
                    summary.success += 1
                    self._report_progress(file_name, i, len(psd_files), "success")
                    batch_controller.complete_file(file_name, success=True, message=f"→ {result.output_dir}")
                elif result.status == ProcessingStatus.SKIPPED:
                    summary.skipped += 1
                    status = "skipped"
                    self._report_progress(file_name, i, len(psd_files), "skipped")
                    batch_controller.complete_file(file_name, skipped=True, message=result.error_message)
                else:  # FAILED
                    summary.failed += 1
                    status = "failed"
                    self._report_progress(file_name, i, len(psd_files), "failed")
                    batch_controller.complete_file(file_name, success=False, message=result.error_message)

                    if stop_on_error:
                        self.logger.error("遇到错误，停止批量处理")
                        self.progress_display.print_error("遇到错误，停止处理")
                        break

                # 添加到 FileResult 列表
                file_results.append(FileResult(
                    filename=file_name,
                    status=status,
                    output_dir=result.output_dir,
                    error_message=result.error_message,
                    duration_seconds=file_duration
                ))

        summary.end_time = datetime.now()

        self.logger.info(f"批量处理完成: 成功={summary.success}, 失败={summary.failed}, 跳过={summary.skipped}")

        # 保存失败记录
        failed_results = [r for r in summary.results if r.status == ProcessingStatus.FAILED]
        if failed_results:
            record_path = self._save_failed_record(self.output_base_dir, failed_results)
            summary.failed_files_path = record_path
            self.logger.info(f"失败记录已保存: {record_path}")

        # 使用 Rich 打印汇总
        stats = SummaryStats(
            total=summary.total,
            success=summary.success,
            failed=summary.failed,
            skipped=summary.skipped,
            duration_seconds=summary.duration_seconds
        )

        self.reporter.print_batch_summary(
            stats=stats,
            results=file_results,
            output_dir=self.output_base_dir if os.path.exists(self.output_base_dir) else None,
            failed_record_path=summary.failed_files_path,
            show_tree=False  # 批量处理不显示每个文件的目录树
        )

        return summary
    
    def process_directory(
        self,
        directory: str,
        recursive: bool = True,
        select_all: bool = False,
        stop_on_error: bool = False
    ) -> BatchSummary:
        """处理整个目录

        Args:
            directory: 要处理的目录
            recursive: 是否递归扫描子目录
            select_all: 是否自动选择所有文件（跳过交互式选择）
            stop_on_error: 遇到错误时是否停止

        Returns:
            BatchSummary 汇总结果
        """
        from rich.panel import Panel

        self.logger.info(f"扫描目录: {directory} (递归={recursive})")

        # 扫描 PSD 文件
        psd_files = self.find_psd_files(directory, recursive)

        if not psd_files:
            self.logger.warning(f"在目录 '{directory}' 中未找到 PSD 文件")
            self.progress_display.print_warning(f"在目录 '{directory}' 中未找到 PSD 文件")
            return BatchSummary(total=0)

        self.logger.info(f"发现 {len(psd_files)} 个 PSD 文件")

        self.reporter.console.print(Panel(
            f"[bold cyan]目录:[/bold cyan] {directory}\n"
            f"[bold green]发现:[/bold green] {len(psd_files)} 个 PSD 文件",
            title="[bold]扫描结果[/bold]",
            border_style="cyan"
        ))

        # 选择要处理的文件
        if select_all or not self.interactive:
            selected_files = psd_files
            self.logger.info(f"自动选择全部 {len(selected_files)} 个文件")
        else:
            selected_files = self._interactive_select(psd_files)

        if not selected_files:
            self.logger.info("用户取消选择，未处理任何文件")
            return BatchSummary(total=0)

        self.logger.info(f"开始处理 {len(selected_files)} 个文件...")
        self.progress_display.print_info(f"开始处理 {len(selected_files)} 个文件...")

        # 批量处理
        return self.process_batch(selected_files, stop_on_error)
    
    def retry_failed(self, directory: str, stop_on_error: bool = False) -> BatchSummary:
        """重试之前失败的文件

        Args:
            directory: 包含失败记录文件的目录
            stop_on_error: 遇到错误时是否停止

        Returns:
            BatchSummary 汇总结果
        """
        from rich.panel import Panel

        self.logger.info(f"加载失败记录: {directory}")

        record = self._load_failed_record(directory)
        failed_files = record.get("failed_files", [])

        if not failed_files:
            self.logger.info("没有失败的文件需要重试")
            self.progress_display.print_info("没有失败的文件需要重试")
            return BatchSummary(total=0)

        self.logger.info(f"找到 {len(failed_files)} 个失败的文件记录")

        # 提取文件路径
        psd_files = [item["path"] for item in failed_files if os.path.exists(item["path"])]

        if not psd_files:
            self.logger.warning("失败记录中的文件已不存在或已被移动")
            self.progress_display.print_warning("失败记录中的文件已不存在或已被移动")
            return BatchSummary(total=0)

        self.logger.info(f"{len(psd_files)} 个文件可以重试")

        # 显示重试列表
        file_list = "\n".join([f"  [{i}] {os.path.basename(path)}" for i, path in enumerate(psd_files, 1)])
        self.reporter.console.print(Panel(
            f"[bold yellow]找到 {len(psd_files)} 个需要重试的文件[/bold yellow]\n\n{file_list}",
            title="[bold]重试模式[/bold]",
            border_style="yellow"
        ))

        # 批量处理
        return self.process_batch(psd_files, stop_on_error)
    
    def process(
        self,
        input_path: str,
        recursive: bool = True,
        select_all: bool = False,
        retry: bool = False,
        stop_on_error: bool = False
    ) -> BatchSummary:
        """主处理入口

        根据输入类型自动选择合适的处理方式。

        Args:
            input_path: 输入路径（PSD 文件或目录）
            recursive: 是否递归扫描子目录
            select_all: 是否自动选择所有文件
            retry: 是否重试之前失败的文件
            stop_on_error: 遇到错误时是否停止

        Returns:
            BatchSummary 汇总结果

        Raises:
            InvalidInputError: 当输入无效时
        """
        self.logger.info(f"开始处理: {input_path}")
        self.logger.debug(f"参数: recursive={recursive}, select_all={select_all}, retry={retry}, stop_on_error={stop_on_error}")

        # 检测输入类型
        input_type = self.detect_input_type(input_path)

        if input_type == InputType.INVALID:
            self.logger.error(f"输入路径无效: {input_path}")
            raise InvalidInputError("输入路径无效或不存在", input_path)

        self.logger.debug(f"输入类型: {input_type.value}")

        # 重试模式
        if retry:
            self.logger.info("进入重试模式")
            if input_type == InputType.DIRECTORY:
                return self.retry_failed(input_path, stop_on_error)
            else:
                # 对于单个文件，尝试重试失败记录
                directory = os.path.dirname(input_path) or "."
                return self.retry_failed(directory, stop_on_error)

        # 处理单个 PSD 文件
        if input_type == InputType.SINGLE_PSD:
            self.logger.info("处理单个 PSD 文件")
            summary = BatchSummary(total=1, start_time=datetime.now())
            result = self.process_single(input_path)
            summary.results.append(result)

            if result.status == ProcessingStatus.SUCCESS:
                summary.success = 1
                self.logger.info("单个文件处理成功")
            elif result.status == ProcessingStatus.SKIPPED:
                summary.skipped = 1
                self.logger.info("单个文件被跳过")
            else:
                summary.failed = 1
                self.logger.error("单个文件处理失败")
                # 保存失败记录
                record_path = self._save_failed_record(self.output_base_dir, [result])
                summary.failed_files_path = record_path

            summary.end_time = datetime.now()
            return summary

        # 处理目录
        if input_type == InputType.DIRECTORY:
            self.logger.info(f"处理目录: {input_path}")
            return self.process_directory(
                input_path,
                recursive=recursive,
                select_all=select_all,
                stop_on_error=stop_on_error
            )

        # 不应该到达这里
        self.logger.error(f"无法处理的输入类型: {input_path}")
        raise InvalidInputError("无法处理的输入类型", input_path)
    
    def print_summary(self, summary: BatchSummary) -> None:
        """打印处理汇总（使用 Rich）
        
        Args:
            summary: 批量处理汇总结果
        """
        stats = SummaryStats(
            total=summary.total,
            success=summary.success,
            failed=summary.failed,
            skipped=summary.skipped,
            duration_seconds=summary.duration_seconds
        )
        
        # 转换结果列表
        file_results = [
            FileResult(
                filename=os.path.basename(r.file_path),
                status="success" if r.status == ProcessingStatus.SUCCESS else 
                       "skipped" if r.status == ProcessingStatus.SKIPPED else "failed",
                output_dir=r.output_dir,
                error_message=r.error_message
            )
            for r in summary.results
        ]
        
        self.reporter.print_batch_summary(
            stats=stats,
            results=file_results,
            output_dir=self.output_base_dir if os.path.exists(self.output_base_dir) else None,
            failed_record_path=summary.failed_files_path
        )


def create_batch_processor(
    output_dir: Optional[str] = None,
    verbose: bool = False,
    conflict_strategy: str = "overwrite",
    interactive: bool = True,
    enable_progress: bool = True,
    console = None,
    logger: Optional[Logger] = None
) -> BatchProcessor:
    """创建批量处理器的工厂函数

    Args:
        output_dir: 输出基础目录
        verbose: 是否输出详细日志
        conflict_strategy: 冲突处理策略（overwrite/skip/rename/ask）
        interactive: 是否启用交互式选择
        enable_progress: 是否启用 Rich 进度显示
        console: Rich Console 实例
        logger: 日志记录器实例，如果为 None 则使用默认实例

    Returns:
        BatchProcessor 实例
    """
    strategy_map = {
        "overwrite": ConflictStrategy.OVERWRITE,
        "skip": ConflictStrategy.SKIP,
        "rename": ConflictStrategy.RENAME,
        "ask": ConflictStrategy.ASK,
    }

    strategy = strategy_map.get(conflict_strategy.lower(), ConflictStrategy.OVERWRITE)

    return BatchProcessor(
        output_base_dir=output_dir,
        verbose=verbose,
        conflict_strategy=strategy,
        interactive=interactive,
        enable_progress=enable_progress,
        console=console,
        logger=logger
    )
