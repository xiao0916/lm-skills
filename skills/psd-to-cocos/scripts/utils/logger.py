"""
PSD to Cocos 日志记录模块

提供统一的日志记录功能，支持：
- 文件日志 + 控制台日志
- 日志级别控制 (DEBUG/INFO/WARNING/ERROR)
- 日志文件轮转
- 工具缺失时的安装指导
"""

import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from functools import wraps


# 日志格式
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
VERBOSE_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'

# 默认日志目录
DEFAULT_LOG_DIR = Path.home() / '.psd-to-cocos' / 'logs'


class Logger:
    """PSD to Cocos 日志记录器
    
    提供统一的日志记录接口，支持文件轮转和控制台输出。
    
    Attributes:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
    """
    
    def __init__(
        self,
        name: str = 'psd_to_cocos',
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        log_dir: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        verbose: bool = False,
        console_output: bool = True
    ):
        """初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别 (logging.DEBUG/INFO/WARNING/ERROR)
            log_file: 日志文件路径，如果为 None 则使用默认路径
            log_dir: 日志目录，如果为 None 则使用 ~/.psd-to-cocos/logs/
            max_bytes: 单个日志文件最大字节数（默认 10MB）
            backup_count: 保留的备份文件数量（默认 5）
            verbose: 是否启用详细格式（包含文件名和行号）
            console_output: 是否输出到控制台
        """
        self.name = name
        self.level = level
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.verbose = verbose
        
        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 清除现有的处理器（避免重复）
        self.logger.handlers.clear()
        
        # 确定日志文件路径
        if log_file:
            self.log_file = Path(log_file)
        else:
            log_directory = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
            self.log_file = log_directory / 'psd-to-cocos.log'
        
        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建格式化器
        formatter = logging.Formatter(
            VERBOSE_LOG_FORMAT if verbose else DEFAULT_LOG_FORMAT
        )
        
        # 文件处理器（带轮转）
        try:
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            # 如果无法写入日志文件，使用 stderr
            print(f"警告: 无法创建日志文件 {self.log_file}: {e}", file=sys.stderr)
        
        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _ensure_dir_exists(self) -> None:
        """确保日志目录存在"""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        except (IOError, OSError) as e:
            self.logger.error(f"无法创建日志目录: {e}")
    
    # 日志级别便捷方法
    def debug(self, message: str, *args, **kwargs) -> None:
        """记录 DEBUG 级别日志"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """记录 INFO 级别日志"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """记录 WARNING 级别日志"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """记录 ERROR 级别日志"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """记录 CRITICAL 级别日志"""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs) -> None:
        """记录异常信息（包含堆栈跟踪）"""
        self.logger.exception(message, *args, **kwargs)
    
    def log_tool_not_found(self, tool_name: str, search_paths: list[str]) -> None:
        """记录工具未找到错误并提供安装指导
        
        Args:
            tool_name: 工具名称
            search_paths: 搜索路径列表
        """
        self.error(f"工具未找到: {tool_name}")
        self.info("搜索路径:")
        for path in search_paths:
            self.info(f"  - {path}")
        
        # 根据工具名称提供特定的安装指导
        if tool_name == 'psd-layer-reader':
            self.info("\n请确保 psd-layer-reader 技能已安装:")
            self.info("  1. 检查 .claude/skills/psd-layer-reader/ 目录是否存在")
            self.info("  2. 或设置 CLAUDE_SKILLS_PATH 环境变量指向技能目录")
        elif tool_name == 'psd-slicer':
            self.info("\n请确保 psd-slicer 技能已安装:")
            self.info("  1. 检查 .claude/skills/psd-slicer/ 目录是否存在")
            self.info("  2. 或设置 CLAUDE_SKILLS_PATH 环境变量指向技能目录")
        else:
            self.info(f"\n请确保 {tool_name} 已正确安装")
    
    def log_dependency_missing(self, package_name: str, install_command: Optional[str] = None) -> None:
        """记录依赖缺失错误并提供安装指导
        
        Args:
            package_name: 缺失的包名称
            install_command: 安装命令，如果为 None 则使用默认命令
        """
        cmd = install_command or f"pip install {package_name}"
        
        self.error(f"缺少必需的依赖: {package_name}")
        self.info(f"请运行: {cmd}")
        
        # 特定包的额外指导
        if package_name == 'psd-tools':
            self.info("\npsd-tools 是处理 PSD 文件的必需依赖")
            self.info("安装命令: pip install psd-tools")
        elif package_name == 'Pillow':
            self.info("\nPillow 是图像处理的必需依赖")
            self.info("安装命令: pip install Pillow")
        elif package_name == 'rich':
            self.info("\nrich 用于提供美观的命令行界面")
            self.info("安装命令: pip install rich")
    
    def log_conversion_start(self, psd_path: str, output_dir: str) -> None:
        """记录转换开始
        
        Args:
            psd_path: PSD 文件路径
            output_dir: 输出目录
        """
        self.info(f"开始转换: {psd_path}")
        self.debug(f"输出目录: {output_dir}")
    
    def log_conversion_success(self, psd_path: str, output_dir: str, element_count: int = 0) -> None:
        """记录转换成功
        
        Args:
            psd_path: PSD 文件路径
            output_dir: 输出目录
            element_count: 导出的元素数量
        """
        self.info(f"转换成功: {psd_path}")
        self.info(f"输出目录: {output_dir}")
        if element_count > 0:
            self.info(f"导出元素数量: {element_count}")
    
    def log_conversion_failure(self, psd_path: str, error: str) -> None:
        """记录转换失败
        
        Args:
            psd_path: PSD 文件路径
            error: 错误信息
        """
        self.error(f"转换失败: {psd_path}")
        self.error(f"错误信息: {error}")
    
    def log_step_start(self, step_name: str) -> None:
        """记录步骤开始
        
        Args:
            step_name: 步骤名称
        """
        self.debug(f"开始步骤: {step_name}")
    
    def log_step_complete(self, step_name: str, success: bool = True) -> None:
        """记录步骤完成
        
        Args:
            step_name: 步骤名称
            success: 是否成功
        """
        if success:
            self.debug(f"步骤完成: {step_name}")
        else:
            self.warning(f"步骤失败: {step_name}")
    
    def set_level(self, level: int) -> None:
        """设置日志级别
        
        Args:
            level: 新的日志级别
        """
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                handler.setLevel(level)
    
    def get_log_file_path(self) -> str:
        """获取日志文件路径
        
        Returns:
            日志文件的绝对路径
        """
        return str(self.log_file.absolute())


# 全局日志记录器实例
_logger_instance: Optional[Logger] = None


def get_logger(
    name: str = 'psd_to_cocos',
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    verbose: bool = False
) -> Logger:
    """获取全局日志记录器实例
    
    这是一个工厂函数，返回 Logger 类的单例实例。
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        verbose: 是否启用详细格式
        
    Returns:
        Logger 实例
        
    Example:
        >>> from src.utils.logger import get_logger
        >>> logger = get_logger(verbose=True)
        >>> logger.info("开始转换")
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = Logger(
            name=name,
            level=level,
            log_file=log_file,
            verbose=verbose
        )
    
    return _logger_instance


def reset_logger() -> None:
    """重置全局日志记录器实例
    
    用于测试或需要重新配置日志记录器的场景。
    """
    global _logger_instance
    _logger_instance = None


def log_execution(logger: Optional[Logger] = None):
    """函数执行日志装饰器
    
    自动记录函数的开始、完成和异常信息。
    
    Args:
        logger: 日志记录器实例，如果为 None 则使用全局实例
        
    Example:
        >>> @log_execution()
        ... def my_function():
        ...     pass
    """
    def decorator(func):
        log = logger or get_logger()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            log.debug(f"调用函数: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                log.debug(f"函数完成: {func.__name__}")
                return result
            except Exception as e:
                log.error(f"函数异常: {func.__name__} - {str(e)}")
                raise
        
        return wrapper
    return decorator
