"""
PSD to Cocos 自定义异常类

定义所有在转换过程中可能抛出的自定义异常，便于错误处理和用户友好的提示。
"""


from typing import List, Optional

class PSDToCocosError(Exception):
    """基础异常类"""
    pass


class ToolNotFoundError(PSDToCocosError):
    """工具未找到异常
    
    当 psd-layer-reader 或 psd-slicer 工具无法找到时抛出。
    """
    
    def __init__(self, tool_name: str, search_paths: List[str] | None = None):
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
