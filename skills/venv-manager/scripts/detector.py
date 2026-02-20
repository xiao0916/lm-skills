"""Environment detector for skills.

Detects whether a skill needs a virtual environment and checks for existing environments.
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add scripts directory to path for imports
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

parser_module = __import__("parser", fromlist=["parse_skill_dependencies"])
parse_skill_dependencies = parser_module.parse_skill_dependencies


import os

def _get_project_root() -> Path:
    env_root = os.environ.get("PROJECT_ROOT")
    if env_root:
        return Path(env_root)
    current_dir = Path(__file__).resolve()
    return current_dir.parent.parent.parent.parent.parent


def get_venv_path(group_name: str) -> str:
    project_root = _get_project_root()
    venvs_dir = project_root / ".venvs"
    return str(venvs_dir / group_name)


def detect_environment(skill_path: str) -> dict[str, Any]:
    """Detect whether a skill needs a virtual environment.
    
    Args:
        skill_path: Path to the skill directory
        
    Returns:
        dict with keys:
            - needs_venv: bool - True if skill has dependencies
            - existing_env: str|None - Name of existing venv if any
            - env_path: str - Full path to venv directory
    """
    skill_dir = Path(skill_path)
    
    if not skill_dir.exists():
        return {
            "needs_venv": False,
            "existing_env": None,
            "env_path": ""
        }
    
    # Parse dependencies
    deps = parse_skill_dependencies(str(skill_dir))
    packages = deps.get("packages", [])
    group = deps.get("group")
    
    # If no dependencies, no venv needed
    if not packages:
        return {
            "needs_venv": False,
            "existing_env": None,
            "env_path": ""
        }
    
    # Determine venv name (use group if available, otherwise use skill name)
    skill_name = skill_dir.name
    venv_name = group if group else skill_name
    
    # Check for existing environment
    env_path = get_venv_path(venv_name)
    existing_env = None
    
    # Check both .venvs/{group} and .venvs/{skill_name}
    for check_name in [venv_name, skill_name]:
        check_path = get_venv_path(check_name)
        python_path = Path(check_path) / "bin" / "python"
        if python_path.exists():
            existing_env = check_name
            env_path = check_path
            break
    
    return {
        "needs_venv": True,
        "existing_env": existing_env,
        "env_path": env_path
    }


def get_python_executable(env_path: str) -> str:
    """Get the Python executable path for a virtual environment.
    
    Args:
        env_path: Path to the virtual environment
        
    Returns:
        Path to the Python executable
    """
    if os.name == 'nt':
        # Windows
        return str(Path(env_path) / "Scripts" / "python.exe")
    else:
        # Unix-like
        return str(Path(env_path) / "bin" / "python")
