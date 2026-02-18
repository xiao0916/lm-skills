"""
结果报告模块

提供美观的结果汇总展示，包括表格、目录树等，基于 Rich 库。
"""

import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.box import ROUNDED, SIMPLE_HEAD, DOUBLE_EDGE
from rich.progress_bar import ProgressBar


@dataclass
class FileResult:
    """单个文件处理结果"""
    filename: str
    status: str  # success, failed, skipped
    output_dir: Optional[str] = None
    error_message: str = ""
    duration_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SummaryStats:
    """汇总统计数据"""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率百分比"""
        if self.total == 0:
            return 0.0
        return (self.success / self.total) * 100
    
    @property
    def failed_rate(self) -> float:
        """失败率百分比"""
        if self.total == 0:
            return 0.0
        return (self.failed / self.total) * 100


class ResultReporter:
    """结果报告类
    
    提供美观的结果汇总展示，包括表格、目录树等。
    """
    
    def __init__(self, console: Optional[Console] = None):
        """初始化结果报告器
        
        Args:
            console: Rich Console 实例，如果为 None 则创建默认实例
        """
        self.console = console or Console()
    
    def print_summary_table(
        self,
        stats: SummaryStats,
        title: str = "处理汇总"
    ) -> Table:
        """打印汇总统计表格
        
        Args:
            stats: 汇总统计数据
            title: 表格标题
            
        Returns:
            Rich Table 实例
        """
        table = Table(
            title=f"[bold cyan]{title}[/bold cyan]",
            box=ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        
        table.add_column("指标", style="cyan", justify="left")
        table.add_column("数值", style="green", justify="right")
        table.add_column("占比", style="yellow", justify="right")
        
        # 添加数据行
        table.add_row(
            "总计",
            str(stats.total),
            "100%"
        )
        table.add_row(
            "[green]成功[/green]",
            f"[green]{stats.success}[/green]",
            f"[green]{stats.success_rate:.1f}%[/green]"
        )
        table.add_row(
            "[red]失败[/red]",
            f"[red]{stats.failed}[/red]",
            f"[red]{stats.failed_rate:.1f}%[/red]"
        )
        if stats.skipped > 0:
            table.add_row(
                "[yellow]跳过[/yellow]",
                f"[yellow]{stats.skipped}[/yellow]",
                f"[yellow]{(stats.skipped / stats.total * 100):.1f}%[/yellow]" if stats.total > 0 else "0%"
            )
        
        # 添加分隔线
        table.add_row("─" * 10, "─" * 10, "─" * 10, style="dim")
        
        # 添加耗时
        duration_str = self._format_duration(stats.duration_seconds)
        table.add_row(
            "[bold]总耗时[/bold]",
            f"[bold]{duration_str}[/bold]",
            ""
        )
        
        self.console.print()
        self.console.print(table)
        
        return table
    
    def print_results_table(
        self,
        results: List[FileResult],
        show_success: bool = True,
        show_errors: bool = True,
        max_rows: int = 50
    ) -> Table:
        """打印详细结果表格
        
        Args:
            results: 文件结果列表
            show_success: 是否显示成功项
            show_errors: 是否显示错误详情
            max_rows: 最大显示行数
            
        Returns:
            Rich Table 实例
        """
        if not results:
            return Table()
        
        # 过滤结果
        filtered_results = []
        for r in results:
            if r.status == "success" and show_success:
                filtered_results.append(r)
            elif r.status in ("failed", "skipped"):
                filtered_results.append(r)
        
        if not filtered_results:
            return Table()
        
        table = Table(
            title="[bold cyan]详细结果[/bold cyan]",
            box=SIMPLE_HEAD,
            show_header=True,
            header_style="bold magenta",
        )
        
        table.add_column("序号", style="dim", justify="center", width=4)
        table.add_column("文件名", style="cyan", min_width=20, max_width=40)
        table.add_column("状态", style="bold", justify="center", width=8)
        table.add_column("耗时", style="yellow", justify="right", width=8)
        table.add_column("详情", style="white", min_width=20, max_width=50)
        
        # 限制行数
        display_results = filtered_results[:max_rows]
        if len(filtered_results) > max_rows:
            remaining = len(filtered_results) - max_rows
        else:
            remaining = 0
        
        for i, result in enumerate(display_results, 1):
            status_icon, status_color = self._get_status_style(result.status)
            status_text = f"[{status_color}]{status_icon} {result.status.upper()}[/{status_color}]"
            
            duration_str = self._format_duration(result.duration_seconds, short=True)
            
            # 详情列
            if result.status == "failed" and show_errors:
                detail = f"[red]{result.error_message[:40]}[/red]"
                if len(result.error_message) > 40:
                    detail += "..."
            elif result.status == "skipped":
                detail = f"[yellow]{result.error_message[:40] if result.error_message else 'Skipped'}[/yellow]"
            elif result.output_dir:
                detail = f"[dim]{result.output_dir}[/dim]"
            else:
                detail = ""
            
            table.add_row(
                str(i),
                result.filename,
                status_text,
                duration_str,
                detail
            )
        
        if remaining > 0:
            table.add_row(
                "...",
                f"[dim]还有 {remaining} 个结果未显示[/dim]",
                "",
                "",
                "",
                style="dim"
            )
        
        self.console.print()
        self.console.print(table)
        
        return table
    
    def print_directory_tree(
        self,
        root_dir: str,
        max_depth: int = 3,
        max_files: int = 20
    ) -> Tree:
        """打印目录树结构
        
        Args:
            root_dir: 根目录路径
            max_depth: 最大深度
            max_files: 最大文件数
            
        Returns:
            Rich Tree 实例
        """
        if not os.path.exists(root_dir):
            self.console.print(f"[red]目录不存在: {root_dir}[/red]")
            return Tree("")
        
        root_name = os.path.basename(root_dir) or root_dir
        tree = Tree(
            f"[bold cyan]📁 {root_name}/[/bold cyan]",
            guide_style="dim"
        )
        
        self._add_tree_nodes(tree, root_dir, current_depth=0, max_depth=max_depth, max_files=max_files)
        
        self.console.print()
        self.console.print(Panel(tree, title="[bold]输出目录结构[/bold]", border_style="green"))
        
        return tree
    
    def _add_tree_nodes(
        self,
        tree: Tree,
        directory: str,
        current_depth: int,
        max_depth: int,
        max_files: int
    ):
        """递归添加树节点
        
        Args:
            tree: 父树节点
            directory: 当前目录
            current_depth: 当前深度
            max_depth: 最大深度
            max_files: 最大文件数
        """
        if current_depth >= max_depth:
            return
        
        try:
            entries = list(os.scandir(directory))
        except (PermissionError, OSError):
            return
        
        # 排序：目录在前，文件在后
        dirs = [e for e in entries if e.is_dir()]
        files = [e for e in entries if e.is_file()]
        dirs.sort(key=lambda x: x.name)
        files.sort(key=lambda x: x.name)
        
        # 添加目录
        for entry in dirs[:max_files]:
            dir_tree = tree.add(f"[blue]📁 {entry.name}/[/blue]")
            self._add_tree_nodes(dir_tree, entry.path, current_depth + 1, max_depth, max_files)
        
        # 添加文件
        for entry in files[:max_files]:
            icon = self._get_file_icon(entry.name)
            color = self._get_file_color(entry.name)
            tree.add(f"[{color}]{icon} {entry.name}[/{color}]")
        
        # 如果文件太多，显示省略
        total_entries = len(dirs) + len(files)
        if total_entries > max_files:
            remaining = total_entries - max_files
            tree.add(f"[dim]... 还有 {remaining} 个文件[/dim]")
    
    def _get_file_icon(self, filename: str) -> str:
        """根据文件名获取图标
        
        Args:
            filename: 文件名
            
        Returns:
            图标字符串
        """
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        icons = {
            'json': '📄',
            'png': '🖼',
            'jpg': '🖼',
            'jpeg': '🖼',
            'psd': '🎨',
            'txt': '📝',
            'md': '📝',
            'py': '🐍',
            'js': '📜',
            'ts': '📜',
        }
        
        return icons.get(ext, '📄')
    
    def _get_file_color(self, filename: str) -> str:
        """根据文件名获取颜色
        
        Args:
            filename: 文件名
            
        Returns:
            颜色名称
        """
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        colors = {
            'json': 'yellow',
            'png': 'magenta',
            'jpg': 'magenta',
            'jpeg': 'magenta',
            'psd': 'blue',
            'txt': 'white',
            'md': 'white',
            'py': 'green',
            'js': 'yellow',
            'ts': 'blue',
        }
        
        return colors.get(ext, 'white')
    
    def print_batch_summary(
        self,
        stats: SummaryStats,
        results: List[FileResult],
        output_dir: Optional[str] = None,
        failed_record_path: Optional[str] = None,
        show_tree: bool = True
    ):
        """打印完整的批量处理汇总
        
        Args:
            stats: 汇总统计数据
            results: 文件结果列表
            output_dir: 输出目录路径
            failed_record_path: 失败记录文件路径
            show_tree: 是否显示目录树
        """
        # 打印主汇总表
        self.print_summary_table(stats)
        
        # 打印详细结果表
        if results:
            self.print_results_table(results)
        
        # 打印目录树
        if show_tree and output_dir and os.path.exists(output_dir):
            self.print_directory_tree(output_dir)
        
        # 打印失败记录提示
        if failed_record_path and stats.failed > 0:
            self.console.print()
            self.console.print(Panel(
                f"[yellow]失败记录已保存[/yellow]: [cyan]{failed_record_path}[/cyan]\n"
                f"使用 [bold]--retry[/bold] 参数重试失败的文件",
                border_style="yellow",
                title="[bold yellow]重试提示[/bold yellow]"
            ))
        
        # 打印完成信息
        self.console.print()
        if stats.failed == 0:
            self.console.print(Panel(
                "[bold green]✓ 所有文件处理成功！[/bold green]",
                border_style="green"
            ))
        elif stats.success == 0:
            self.console.print(Panel(
                "[bold red]✗ 所有文件处理失败[/bold red]",
                border_style="red"
            ))
        else:
            self.console.print(Panel(
                f"[bold yellow]⚠ 部分文件处理失败 ({stats.failed}/{stats.total})[/bold yellow]",
                border_style="yellow"
            ))
    
    def print_conversion_result(
        self,
        psd_path: str,
        output_dir: str,
        success: bool,
        message: str = "",
        element_count: int = 0
    ):
        """打印单个转换结果
        
        Args:
            psd_path: PSD 文件路径
            output_dir: 输出目录路径
            success: 是否成功
            message: 状态消息
            element_count: 元素数量
        """
        if success:
            panel_content = f"""
[green]✓ 转换成功[/green]

[bold]PSD 文件:[/bold] {psd_path}
[bold]输出目录:[/bold] {output_dir}
[bold]元素数量:[/bold] {element_count}
            """.strip()
            border_style = "green"
            title = "[bold green]转换完成[/bold green]"
        else:
            panel_content = f"""
[red]✗ 转换失败[/red]

[bold]PSD 文件:[/bold] {psd_path}
[bold]错误信息:[/bold] [red]{message}[/red]
            """.strip()
            border_style = "red"
            title = "[bold red]转换失败[/bold red]"
        
        self.console.print()
        self.console.print(Panel(
            panel_content,
            title=title,
            border_style=border_style
        ))
        
        # 如果成功，显示目录树
        if success and os.path.exists(output_dir):
            self.print_directory_tree(output_dir, max_depth=2)
    
    def _get_status_style(self, status: str) -> Tuple[str, str]:
        """获取状态样式
        
        Args:
            status: 状态字符串
            
        Returns:
            (图标, 颜色) 元组
        """
        styles = {
            "success": ("✓", "green"),
            "failed": ("✗", "red"),
            "skipped": ("⏭", "yellow"),
            "pending": ("○", "dim"),
            "running": ("◐", "blue"),
        }
        return styles.get(status, ("?", "white"))
    
    def _format_duration(self, seconds: float, short: bool = False) -> str:
        """格式化时间
        
        Args:
            seconds: 秒数
            short: 是否使用短格式
            
        Returns:
            格式化后的时间字符串
        """
        if seconds < 1:
            if short:
                return f"{seconds*1000:.0f}ms"
            return f"{seconds*1000:.1f} 毫秒"
        elif seconds < 60:
            if short:
                return f"{seconds:.1f}s"
            return f"{seconds:.1f} 秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            if short:
                return f"{minutes}m{secs:.0f}s"
            return f"{minutes} 分 {secs:.0f} 秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if short:
                return f"{hours}h{minutes}m"
            return f"{hours} 小时 {minutes} 分"


def create_reporter(console: Optional[Console] = None) -> ResultReporter:
    """创建结果报告器实例的工厂函数
    
    Args:
        console: Rich Console 实例
        
    Returns:
        ResultReporter 实例
    """
    return ResultReporter(console=console)
