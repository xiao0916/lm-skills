#!/usr/bin/env python3
"""
项目目录结构分析脚本
递归扫描项目目录，生成目录树结构，统计文件类型分布
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

# 关键目录名称（用于识别项目结构）
KEY_DIRECTORIES: Set[str] = {
    "src", "pages", "components", "hooks", "utils", "services", 
    "types", "config", "lib", "models", "views", "layouts", 
    "stores", "api", "assets", "public", "styles", "locales",
    "middleware", "context", "modules", "plugins", "routes"
}

# 配置文件名称
CONFIG_FILES: Set[str] = {
    "package.json", "tsconfig.json", "jsconfig.json",
    "vite.config.js", "vite.config.ts", "vite.config.mjs",
    "webpack.config.js", "webpack.config.ts",
    "rollup.config.js", "rollup.config.ts",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "nuxt.config.js", "nuxt.config.ts",
    "tailwind.config.js", "tailwind.config.ts",
    "postcss.config.js", "postcss.config.ts",
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yaml",
    ".prettierrc", ".prettierrc.js", ".prettierrc.json",
    "babel.config.js", "babel.config.json",
    "jest.config.js", "jest.config.ts", "jest.config.json",
    "pyproject.toml", "setup.py", "setup.cfg",
    "requirements.txt", "Pipfile", "poetry.lock",
    ".env", ".env.local", ".env.development", ".env.production",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", "CMakeLists.txt"
}

# 文件类型映射
FILE_TYPE_MAP: Dict[str, str] = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".svelte": "svelte",
    ".py": "python",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "header",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".md": "markdown",
    ".txt": "text",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "config",
    ".conf": "config",
    ".gitignore": "gitignore",
    ".dockerignore": "dockerignore",
}

# 最大目录树深度
MAX_TREE_DEPTH = 5


def should_skip_directory(dir_name: str) -> bool:
    """判断是否应该跳过该目录"""
    skip_dirs = {
        ".git", ".svn", ".hg", "node_modules", "__pycache__",
        ".pytest_cache", ".mypy_cache", ".tox", ".nox",
        "dist", "build", "out", "target", "coverage", ".nyc_output",
        ".next", ".nuxt", ".output", ".cache", ".temp", "tmp",
        ".vscode", ".idea", ".vs", "*.xcodeproj", "*.xcworkspace",
        "vendor", "venv", ".venv", "env", ".env_virtual",
        "site-packages", "lib64", "node_modules_backup"
    }
    return dir_name in skip_dirs or dir_name.startswith(".")


def get_file_type(file_path: Path) -> str:
    """获取文件类型"""
    suffix = file_path.suffix.lower()
    if file_path.name in CONFIG_FILES or file_path.name.startswith(".") and file_path.is_file():
        return "config"
    return FILE_TYPE_MAP.get(suffix, "other")


def build_directory_tree(root_path: Path, current_depth: int = 0) -> Dict[str, Any]:
    """递归构建目录树结构"""
    tree: Dict[str, Any] = {
        "name": root_path.name,
        "type": "directory",
        "children": []
    }
    
    if current_depth >= MAX_TREE_DEPTH:
        tree["truncated"] = True
        return tree
    
    try:
        # 获取目录下的所有条目
        entries = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        
        for entry in entries:
            # 跳过隐藏文件和目录（除非是配置文件）
            if entry.name.startswith(".") and entry.name not in CONFIG_FILES:
                continue
            
            # 跳过应该忽略的目录
            if entry.is_dir() and should_skip_directory(entry.name):
                continue
            
            if entry.is_dir():
                subtree = build_directory_tree(entry, current_depth + 1)
                # 只添加非空目录
                if subtree.get("children") or subtree.get("truncated"):
                    tree["children"].append(subtree)
            else:
                # 只添加非空文件
                if entry.stat().st_size > 0:
                    file_info = {
                        "name": entry.name,
                        "type": "file",
                        "file_type": get_file_type(entry)
                    }
                    tree["children"].append(file_info)
    
    except PermissionError:
        tree["error"] = "permission denied"
    except Exception as e:
        tree["error"] = str(e)
    
    return tree


def analyze_structure(project_path: str) -> Dict[str, Any]:
    """分析项目结构，返回目录树、文件类型统计和关键目录信息"""
    root_path = Path(project_path).resolve()
    
    if not root_path.exists():
        raise FileNotFoundError(f"路径不存在: {project_path}")
    
    if not root_path.is_dir():
        raise ValueError(f"路径不是目录: {project_path}")
    
    # 1. 构建目录树
    directory_tree = build_directory_tree(root_path)
    
    # 2. 统计文件类型
    file_types: Dict[str, int] = {}
    config_files_found: List[str] = []
    
    for root, dirs, files in os.walk(root_path):
        # 过滤目录
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]
        
        for file_name in files:
            if file_name.startswith("."):
                if file_name in CONFIG_FILES:
                    # 记录配置文件相对路径
                    rel_path = os.path.relpath(os.path.join(root, file_name), root_path)
                    config_files_found.append(rel_path)
                continue
            
            file_path = Path(root) / file_name
            file_type = get_file_type(file_path)
            file_types[file_type] = file_types.get(file_type, 0) + 1
    
    # 3. 识别关键目录
    key_directories_found: Dict[str, Dict[str, Any]] = {}
    
    for key_dir in KEY_DIRECTORIES:
        # 检查根目录下的关键目录
        dir_path = root_path / key_dir
        if dir_path.exists() and dir_path.is_dir():
            key_directories_found[key_dir] = {
                "path": str(dir_path),
                "exists": True
            }
        else:
            # 检查 src 下的关键目录
            src_path = root_path / "src" / key_dir
            if src_path.exists() and src_path.is_dir():
                key_directories_found[key_dir] = {
                    "path": str(src_path),
                    "exists": True,
                    "nested": True
                }
    
    # 构建结果
    result = {
        "project_path": str(root_path),
        "project_name": root_path.name,
        "directory_tree": directory_tree,
        "file_types": file_types,
        "key_directories": key_directories_found,
        "config_files": sorted(config_files_found),
        "summary": {
            "total_file_types": len(file_types),
            "total_key_directories": len(key_directories_found),
            "total_config_files": len(config_files_found)
        }
    }
    
    return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python analyze_structure.py <项目路径>")
        print("示例: python analyze_structure.py /path/to/project")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    try:
        result = analyze_structure(project_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"分析失败: {str(e)}"}, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
