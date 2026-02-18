"""
PSD to Cocos 自定义异常类

定义所有在转换过程中可能抛出的自定义异常，便于错误处理和用户友好的提示。
"""


class PSDToCocosError(Exception):
    """基础异常类"""
    pass


class ToolNotFoundError(PSDToCocosError):
    """工具未找到异常
    
    当 psd-layer-reader 或 psd-slicer 工具无法找到时抛出。
    """
    
    def __init__(self, tool_name: str, search_paths: list[str] | None = None):
        self.tool_name = tool_name
        self.search_paths = search_paths or []
        
        paths_str = '\n  - '.join([''] + [str(p) for p in self.search_paths])
        message = (
            f"工具 '{tool_name}' 未找到。\n"
            f"搜索路径:{paths_str}\n\n"
            f"请确保技能已安装在正确位置，或设置 CLAUDE_SKILLS_PATH 环境变量。"
        )
        super().__init__(message)


class ToolExecutionError(PSDToCocosError):
    """工具执行异常
    
    当工具执行失败时抛出（如 psd-layer-reader 返回非零退出码）。
    """
    
    def __init__(self, tool_name: str, returncode: int, stderr: str = ""):
        self.tool_name = tool_name
        self.returncode = returncode
        self.stderr = stderr
        
        message = f"工具 '{tool_name}' 执行失败（退出码: {returncode}）"
        if stderr:
            message += f"\n错误输出: {stderr}"
        super().__init__(message)


class DirectoryConflictError(PSDToCocosError):
    """目录冲突异常
    
    当输出目录已存在且冲突策略无法自动解决时抛出。
    """
    
    def __init__(self, path: str, strategy: str = ""):
        self.path = path
        self.strategy = strategy
        
        message = f"输出目录已存在: {path}"
        if strategy:
            message += f"\n冲突策略 '{strategy}' 无法解决此冲突。"
        super().__init__(message)


class InvalidInputError(PSDToCocosError):
    """无效输入异常
    
    当输入文件不存在、格式不正确或无法访问时抛出。
    """
    
    def __init__(self, message: str, path: str = ""):
        self.path = path
        full_message = message
        if path:
            full_message = f"{message}: {path}"
        super().__init__(full_message)


class AtomicOperationError(PSDToCocosError):
    """原子操作异常
    
    当原子操作（临时目录 + 移动）失败时抛出。
    """
    
    def __init__(self, operation: str, temp_path: str = "", target_path: str = ""):
        self.operation = operation
        self.temp_path = temp_path
        self.target_path = target_path
        
        message = f"原子操作失败: {operation}"
        if temp_path:
            message += f"\n临时路径: {temp_path}"
        if target_path:
            message += f"\n目标路径: {target_path}"
        super().__init__(message)


class ConfigurationError(PSDToCocosError):
    """配置错误异常
    
    当配置无效或缺少必需的配置项时抛出。
    """
    pass


class DependencyError(PSDToCocosError):
    """依赖缺失异常
    
    当必需的 Python 依赖未安装时抛出。
    """
    
    def __init__(self, package_name: str, install_command: str = ""):
        self.package_name = package_name
        self.install_command = install_command or f"pip install {package_name}"
        
        message = (
            f"缺少必需的依赖: {package_name}\n"
            f"请运行: {self.install_command}"
        )
        super().__init__(message)


class InvalidPsdError(PSDToCocosError):
    """PSD 文件损坏或格式不支持
    
    当 PSD 文件无法解析、文件损坏或使用了不支持的 PSD 特性时抛出。
    """
    
    def __init__(self, psd_path: str, reason: str = ""):
        self.psd_path = psd_path
        self.reason = reason
        
        message = f"PSD 文件无效或损坏: {psd_path}"
        if reason:
            message += f"\n原因: {reason}"
        message += "\n\n建议:"
        message += "\n  1. 检查文件是否完整下载/复制"
        message += "\n  2. 尝试在 Photoshop 中打开并重新保存"
        message += "\n  3. 确保文件格式为标准的 PSD 格式"
        
        super().__init__(message)


class DiskFullError(PSDToCocosError):
    """磁盘空间不足
    
    当输出目录所在磁盘空间不足时抛出。
    """
    
    def __init__(self, path: str, required_bytes: int = 0, available_bytes: int = 0):
        self.path = path
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes
        
        message = f"磁盘空间不足: {path}"
        
        if required_bytes > 0 and available_bytes > 0:
            required_mb = required_bytes / (1024 * 1024)
            available_mb = available_bytes / (1024 * 1024)
            message += f"\n需要空间: {required_mb:.1f} MB"
            message += f"\n可用空间: {available_mb:.1f} MB"
        
        message += "\n\n建议:"
        message += "\n  1. 清理磁盘空间"
        message += "\n  2. 选择其他输出目录"
        message += "\n  3. 使用 --flat 选项减少输出文件数量"
        
        super().__init__(message)
