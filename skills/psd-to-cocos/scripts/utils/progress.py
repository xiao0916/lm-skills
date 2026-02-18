"""
进度显示模块

提供进度条、spinner 和步骤进度显示功能，基于 Rich 库。
支持交互式和非交互式模式。
"""

import os
import sys
from typing import Optional, Callable, List, Dict, Any, Set
from contextlib import contextmanager
from dataclasses import dataclass

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TaskID,
)
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout


@dataclass
class StepInfo:
    """步骤信息"""
    name: str
    description: str
    status: str = "pending"  # pending, running, completed, failed


class RichProgressDisplay:
    """Rich 进度显示类
    
    提供美观的进度条、spinner 和步骤进度显示。
    支持批量处理进度和单个步骤进度。
    """
    
    def __init__(self, console: Optional[Console] = None, enabled: bool = True):
        """初始化进度显示
        
        Args:
            console: Rich Console 实例，如果为 None 则创建默认实例
            enabled: 是否启用进度显示（非交互模式下应设为 False）
        """
        self.console = console or Console()
        self.enabled = enabled and self._is_interactive()
        self._progress: Optional[Progress] = None
        self._current_task: Optional[TaskID] = None
        self._steps: List[StepInfo] = []
        self._live: Optional[Live] = None
    
    @staticmethod
    def _is_interactive() -> bool:
        """检测是否在交互式终端中运行
        
        Returns:
            True 如果是交互式终端，False  otherwise
        """
        # 检查是否是非交互式环境
        if os.environ.get('CI') or os.environ.get('CONTINUOUS_INTEGRATION'):
            return False
        if not sys.stdout.isatty():
            return False
        return True
    
    def create_progress(self, description: str = "处理中...") -> Progress:
        """创建 Rich Progress 实例
        
        Args:
            description: 进度条描述文本
            
        Returns:
            Progress 实例
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True,
        )
    
    @contextmanager
    def step_progress(self, steps: List[str]):
        """步骤进度上下文管理器
        
        显示多个步骤的执行进度，带 spinner 动画。
        
        Args:
            steps: 步骤名称列表
            
        Yields:
            StepProgressController 控制器实例
        """
        if not self.enabled:
            yield StepProgressController(None, steps, self.console, enabled=False)
            return
        
        self._steps = [StepInfo(name=name, description=name) for name in steps]
        
        with self.create_progress() as progress:
            self._progress = progress
            controller = StepProgressController(progress, steps, self.console)
            yield controller
    
    @contextmanager
    def batch_progress(self, total_files: int, description: str = "批量处理"):
        """批量处理进度上下文管理器
        
        显示批量处理的进度条。
        
        Args:
            total_files: 总文件数
            description: 进度描述
            
        Yields:
            BatchProgressController 控制器实例
        """
        if not self.enabled:
            yield BatchProgressController(None, total_files, self.console, enabled=False)
            return
        
        with self.create_progress() as progress:
            self._progress = progress
            task = progress.add_task(f"[cyan]{description}", total=total_files)
            controller = BatchProgressController(progress, total_files, self.console, task)
            yield controller
    
    @contextmanager
    def spinner(self, message: str = "处理中..."):
        """Spinner 上下文管理器
        
        显示单个任务的 spinner 动画。
        
        Args:
            message: 显示的消息
            
        Yields:
            None
        """
        if not self.enabled:
            yield
            return
        
        with self.create_progress() as progress:
            task = progress.add_task(f"[cyan]{message}", total=None)
            try:
                yield
            finally:
                progress.update(task, completed=True, visible=False)
    
    def print_step_complete(self, step_name: str, success: bool = True, message: str = ""):
        """打印步骤完成状态
        
        Args:
            step_name: 步骤名称
            success: 是否成功
            message: 附加消息
        """
        if not self.enabled:
            return
        
        icon = "✓" if success else "✗"
        color = "green" if success else "red"
        msg = f" {message}" if message else ""
        self.console.print(f"[{color}]{icon}[/{color}] {step_name}{msg}")
    
    def print_info(self, message: str):
        """打印信息消息
        
        Args:
            message: 消息内容
        """
        self.console.print(f"[blue]ℹ[/blue] {message}")
    
    def print_success(self, message: str):
        """打印成功消息
        
        Args:
            message: 消息内容
        """
        self.console.print(f"[green]✓[/green] {message}")
    
    def print_error(self, message: str):
        """打印错误消息
        
        Args:
            message: 消息内容
        """
        self.console.print(f"[red]✗[/red] {message}")
    
    def print_warning(self, message: str):
        """打印警告消息
        
        Args:
            message: 消息内容
        """
        self.console.print(f"[yellow]⚠[/yellow] {message}")


class StepProgressController:
    """步骤进度控制器"""
    
    def __init__(
        self,
        progress: Optional[Progress],
        steps: List[str],
        console: Console,
        enabled: bool = True
    ):
        """初始化步骤进度控制器
        
        Args:
            progress: Rich Progress 实例
            steps: 步骤名称列表
            console: Rich Console 实例
            enabled: 是否启用
        """
        self.progress = progress
        self.steps = steps
        self.console = console
        self.enabled = enabled
        self._current_step = 0
        self._task: Optional[TaskID] = None
        self._completed_steps: Set[str] = set()
    
    def start_step(self, step_name: str):
        """开始一个步骤
        
        Args:
            step_name: 步骤名称
        """
        if not self.enabled or step_name not in self.steps:
            return
        
        step_index = self.steps.index(step_name)
        self._current_step = step_index
        
        if self.progress:
            # 如果有之前的任务，标记为完成
            if self._task is not None:
                self.progress.update(self._task, completed=True, visible=False)
            
            # 创建新任务
            step_num = step_index + 1
            total_steps = len(self.steps)
            self._task = self.progress.add_task(
                f"[cyan]步骤 {step_num}/{total_steps}: {step_name}...",
                total=None
            )
    
    def complete_step(self, step_name: str, success: bool = True, message: str = ""):
        """完成一个步骤
        
        Args:
            step_name: 步骤名称
            success: 是否成功
            message: 附加消息
        """
        if not self.enabled:
            return
        
        self._completed_steps.add(step_name)
        
        if self.progress and self._task is not None:
            status = "[green]✓[/green]" if success else "[red]✗[/red]"
            msg = f" {message}" if message else ""
            self.progress.update(
                self._task,
                description=f"{status} {step_name}{msg}",
                completed=True
            )
    
    def get_step_status(self, step_name: str) -> str:
        """获取步骤状态
        
        Args:
            step_name: 步骤名称
            
        Returns:
            状态字符串: pending, running, completed, failed
        """
        if step_name in self._completed_steps:
            return "completed"
        if step_name == self.steps[self._current_step]:
            return "running"
        return "pending"


class BatchProgressController:
    """批量处理进度控制器"""
    
    def __init__(
        self,
        progress: Optional[Progress],
        total_files: int,
        console: Console,
        task: Optional[TaskID] = None,
        enabled: bool = True
    ):
        """初始化批量处理进度控制器
        
        Args:
            progress: Rich Progress 实例
            total_files: 总文件数
            console: Rich Console 实例
            task: 当前任务 ID
            enabled: 是否启用
        """
        self.progress = progress
        self.total_files = total_files
        self.console = console
        self._task = task
        self.enabled = enabled
        self._current_file = 0
        self._success_count = 0
        self._failed_count = 0
        self._skipped_count = 0
    
    def start_file(self, filename: str):
        """开始处理一个文件
        
        Args:
            filename: 文件名
        """
        if not self.enabled:
            return
        
        self._current_file += 1
        
        if self.progress and self._task is not None:
            self.progress.update(
                self._task,
                description=f"[cyan]处理 [{self._current_file}/{self.total_files}]: {filename}..."
            )
    
    def complete_file(self, filename: str, success: bool = True, skipped: bool = False, message: str = ""):
        """完成一个文件的处理
        
        Args:
            filename: 文件名
            success: 是否成功
            skipped: 是否跳过
            message: 附加消息
        """
        if not self.enabled:
            return
        
        if skipped:
            self._skipped_count += 1
            icon = "⏭"
            color = "yellow"
        elif success:
            self._success_count += 1
            icon = "✓"
            color = "green"
        else:
            self._failed_count += 1
            icon = "✗"
            color = "red"
        
        if self.progress and self._task is not None:
            self.progress.advance(self._task)
        
        # 打印完成状态
        msg = f" {message}" if message else ""
        self.console.print(f"[{color}]{icon}[/{color}] {filename}{msg}")
    
    def update_description(self, description: str):
        """更新进度描述
        
        Args:
            description: 新的描述文本
        """
        if not self.enabled or not self.progress or self._task is None:
            return
        
        self.progress.update(self._task, description=description)
    
    @property
    def success_count(self) -> int:
        """成功文件数"""
        return self._success_count
    
    @property
    def failed_count(self) -> int:
        """失败文件数"""
        return self._failed_count
    
    @property
    def skipped_count(self) -> int:
        """跳过文件数"""
        return self._skipped_count


class ProgressCallback:
    """进度回调接口类
    
    提供与现有代码兼容的回调接口。
    """
    
    def __init__(self, progress_display: Optional[RichProgressDisplay] = None):
        """初始化回调接口
        
        Args:
            progress_display: RichProgressDisplay 实例
        """
        self.progress_display = progress_display
        self._step_controller: Optional[StepProgressController] = None
        self._batch_controller: Optional[BatchProgressController] = None
    
    def on_step_start(self, step_name: str, total_steps: int, current_step: int):
        """步骤开始回调
        
        Args:
            step_name: 步骤名称
            total_steps: 总步骤数
            current_step: 当前步骤（从1开始）
        """
        if self._step_controller:
            self._step_controller.start_step(step_name)
    
    def on_step_complete(self, step_name: str, success: bool, message: str = ""):
        """步骤完成回调
        
        Args:
            step_name: 步骤名称
            success: 是否成功
            message: 附加消息
        """
        if self._step_controller:
            self._step_controller.complete_step(step_name, success, message)
    
    def on_file_start(self, filename: str, total_files: int, current_file: int):
        """文件开始回调
        
        Args:
            filename: 文件名
            total_files: 总文件数
            current_file: 当前文件索引（从1开始）
        """
        if self._batch_controller:
            self._batch_controller.start_file(filename)
    
    def on_file_complete(self, filename: str, success: bool, message: str = ""):
        """文件完成回调
        
        Args:
            filename: 文件名
            success: 是否成功
            message: 附加消息
        """
        if self._batch_controller:
            self._batch_controller.complete_file(filename, success, False, message)
    
    def set_step_controller(self, controller: StepProgressController):
        """设置步骤控制器
        
        Args:
            controller: StepProgressController 实例
        """
        self._step_controller = controller
    
    def set_batch_controller(self, controller: BatchProgressController):
        """设置批量处理控制器
        
        Args:
            controller: BatchProgressController 实例
        """
        self._batch_controller = controller


def create_progress_display(console: Optional[Console] = None, enabled: bool = True) -> RichProgressDisplay:
    """创建进度显示实例的工厂函数
    
    Args:
        console: Rich Console 实例
        enabled: 是否启用
        
    Returns:
        RichProgressDisplay 实例
    """
    return RichProgressDisplay(console=console, enabled=enabled)
