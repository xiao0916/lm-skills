"""
工具路径解析器

提供多级搜索策略来发现 psd-layer-reader 和 psd-slicer 工具。
"""

import os
from pathlib import Path
from typing import Optional, Callable, List
from exceptions import ToolNotFoundError


class ToolPathResolver:
    """工具路径解析器
    
    使用多级搜索策略来发现技能工具的路径。
    搜索顺序：
    1. 开发模式（当前文件所在位置的 .claude/skills）
    2. 项目根目录（当前工作目录的 .claude/skills）
    3. 用户主目录（~/.claude/skills）
    4. 环境变量（CLAUDE_SKILLS_PATH）
    """
    
    SKILL_SEARCH_PATHS: List[Callable[[], Path]] = [
        lambda: Path(__file__).parent.parent.parent.parent / '.claude' / 'skills',
        lambda: Path.cwd() / '.claude' / 'skills',
        lambda: Path.home() / '.claude' / 'skills',
        lambda: Path(os.environ.get('CLAUDE_SKILLS_PATH', '')),
    ]
    
    def __init__(self, custom_search_paths: Optional[List[Path]] = None):
        """初始化工具路径解析器
        
        Args:
            custom_search_paths: 可选的自定义搜索路径列表
        """
        self.search_paths = self.SKILL_SEARCH_PATHS.copy()
        if custom_search_paths:
            self.search_paths.extend(lambda p=path: p for path in custom_search_paths)
    
    def resolve(self, skill_name: str, script_name: str) -> Path:
        """解析工具脚本路径
        
        Args:
            skill_name: 技能名称（如 'psd-layer-reader'）
            script_name: 脚本名称（如 'psd_layers.py'）
            
        Returns:
            完整的脚本路径
            
        Raises:
            ToolNotFoundError: 当工具在所有搜索路径中都未找到时
        """
        searched = []
        
        for path_factory in self.search_paths:
            try:
                base_path = path_factory()
            except Exception:
                continue
                
            if not base_path or not base_path.exists():
                searched.append(base_path)
                continue
            
            script_path = base_path / skill_name / 'scripts' / script_name
            
            if script_path.exists():
                return script_path
            
            searched.append(base_path)
        
        raise ToolNotFoundError(
            tool_name=f"{skill_name}/{script_name}",
            search_paths=searched
        )
    
    def resolve_psd_layer_reader(self) -> Path:
        """解析 psd-layer-reader 脚本路径
        
        Returns:
            psd_layers.py 的完整路径
        """
        return self.resolve('psd-layer-reader', 'psd_layers.py')
    
    def resolve_psd_slicer(self) -> Path:
        """解析 psd-slicer 脚本路径
        
        Returns:
            export_slices.py 的完整路径
        """
        return self.resolve('psd-slicer', 'export_slices.py')
    
    def get_all_search_paths(self) -> List[Path]:
        """获取所有搜索路径
        
        Returns:
            当前使用的所有搜索路径列表（不存在的路径也包含）
        """
        paths = []
        for factory in self.search_paths:
            try:
                path = factory()
                if path:
                    paths.append(path)
            except Exception:
                pass
        return paths
    
    @staticmethod
    def get_env_path() -> Optional[Path]:
        """获取环境变量配置的技能路径
        
        Returns:
            CLAUDE_SKILLS_PATH 环境变量指向的路径，如果未设置则返回 None
        """
        env_path = os.environ.get('CLAUDE_SKILLS_PATH', '')
        if env_path:
            return Path(env_path)
        return None
