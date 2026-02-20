"""Parser for skill dependencies.

Supports 3 parsing formats:
1. Standard frontmatter: Parse YAML `dependencies` field from SKILL.md
2. requirements.txt: Read and parse requirements.txt file  
3. Fuzzy parsing: Regex extract `pip install xxx` from SKILL.md
"""

import re
from pathlib import Path
from typing import Any


def parse_skill_dependencies(skill_path: str) -> dict[str, Any]:
    """Parse Python dependencies from a skill directory.
    
    Args:
        skill_path: Path to the skill directory
        
    Returns:
        dict with keys:
            - python_version: str|None - Python version requirement
            - packages: list - List of package names
            - group: str|None - Dependency group/category
    """
    skill_dir = Path(skill_path)
    
    if not skill_dir.exists():
        return {"python_version": None, "packages": [], "group": None}
    
    # Priority 1: Parse YAML frontmatter from SKILL.md
    result = _parse_frontmatter(skill_dir)
    if result["packages"]:
        return result
    
    # Priority 2: Parse requirements.txt
    result = _parse_requirements_txt(skill_dir)
    if result["packages"]:
        return result
    
    # Priority 3: Fuzzy parse pip install commands from SKILL.md
    result = _parse_pip_install_commands(skill_dir)
    if result["packages"]:
        return result
    
    # No dependencies found
    return {"python_version": None, "packages": [], "group": None}


def _parse_frontmatter(skill_dir: Path) -> dict[str, Any]:
    """Parse YAML frontmatter with dependencies field from SKILL.md.
    
    Expected format in frontmatter:
    ---
    name: skill-name
    dependencies:
      python_version: "3.8"
      packages:
        - package1
        - package2>=1.0
      group: optional
    ---
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"python_version": None, "packages": [], "group": None}
    
    try:
        content = skill_md.read_text(encoding='utf-8')
        
        # Check if file has frontmatter
        if not content.startswith('---'):
            return {"python_version": None, "packages": [], "group": None}
        
        # Extract frontmatter
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return {"python_version": None, "packages": [], "group": None}
        
        frontmatter = content[3:3 + end_match.start()]
        
        # Try to import yaml, fallback to manual parsing if not available
        try:
            import yaml
            data = yaml.safe_load(frontmatter) or {}
        except ImportError:
            # Manual YAML-like parsing for dependencies
            data = _manual_yaml_parse(frontmatter)
        
        deps = data.get('dependencies', {})
        if not deps:
            return {"python_version": None, "packages": [], "group": None}
        
        packages = deps.get('packages', [])
        if isinstance(packages, str):
            packages = [packages]
        
        return {
            "python_version": deps.get('python_version'),
            "packages": packages,
            "group": deps.get('group')
        }
        
    except Exception:
        return {"python_version": None, "packages": [], "group": None}


def _manual_yaml_parse(frontmatter: str) -> dict[str, Any]:
    """Simple YAML parser for dependencies structure.
    
    Handles basic YAML structure:
    dependencies:
      python_version: "3.8"
      packages:
        - package1
        - package2
      group: name
    """
    lines = frontmatter.split('\n')
    result: dict = {}
    pending_key = None
    stack: list = [result]
    pending_indent = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        indent = len(line) - len(line.lstrip())
        
        while len(stack) > 1 and indent < len(stack) - 1:
            stack.pop()
        
        if stripped.startswith('- '):
            item = stripped[2:].strip()
            current = stack[-1]
            if isinstance(current, dict):
                if pending_key:
                    current[pending_key] = [item]
                    pending_key = None
                else:
                    current.setdefault('packages', []).append(item)
            continue
        
        if ':' not in stripped:
            continue
        
        if pending_key:
            stack[-1][pending_key] = {}
            stack.append(stack[-1][pending_key])
            pending_key = None
        
        key, value = stripped.split(':', 1)
        key = key.strip()
        value = value.strip()
        
        if value and value[0] in '"\'' and value[-1] in '"\'':
            value = value[1:-1]
        
        current = stack[-1]
        
        if not value:
            pending_key = key
            pending_indent = indent
        else:
            current[key] = value
    
    if pending_key:
        stack[-1][pending_key] = {}
    
    return result


def _parse_requirements_txt(skill_dir: Path) -> dict[str, Any]:
    """Parse packages from requirements.txt file."""
    req_file = skill_dir / "requirements.txt"
    if not req_file.exists():
        # Also check scripts subdirectory
        req_file = skill_dir / "scripts" / "requirements.txt"
    
    if not req_file.exists():
        return {"python_version": None, "packages": [], "group": None}
    
    try:
        content = req_file.read_text(encoding='utf-8')
        packages = []
        
        for line in content.split('\n'):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Skip options like -r, -e, --index-url
            if line.startswith('-') or line.startswith('--'):
                continue
            packages.append(line)
        
        return {
            "python_version": None,
            "packages": packages,
            "group": None
        }
        
    except Exception:
        return {"python_version": None, "packages": [], "group": None}


def _parse_pip_install_commands(skill_dir: Path) -> dict[str, Any]:
    """Fuzzy parse pip install commands from SKILL.md content.
    
    Extracts packages from patterns like:
    - pip install package1 package2
    - pip3 install package1
    - python -m pip install package
    - $ pip install package
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"python_version": None, "packages": [], "group": None}
    
    try:
        content = skill_md.read_text(encoding='utf-8')
        packages = []
        
        # Pattern to match pip install commands in code blocks or inline
        # Handles: pip install, pip3 install, python -m pip install
        pip_patterns = [
            # pip install package1 package2
            r'(?:^|\n|\$\s*)pip(?:3)?\s+install\s+([a-zA-Z0-9_\-\[\],>=<.~!\s]+)',
            # python -m pip install package
            r'python(?:3)?\s+-m\s+pip\s+install\s+([a-zA-Z0-9_\-\[\],>=<.~!\s]+)',
        ]
        
        for pattern in pip_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                pkg_str = match.group(1).strip()
                # Split by whitespace but preserve version specifiers
                for pkg in re.split(r'\s+(?![^\[]*\])', pkg_str):
                    pkg = pkg.strip()
                    if pkg and not pkg.startswith('-') and not pkg.endswith('.txt'):
                        packages.append(pkg)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_packages = []
        for pkg in packages:
            pkg_key = pkg.lower()
            if pkg_key not in seen:
                seen.add(pkg_key)
                unique_packages.append(pkg)
        
        return {
            "python_version": None,
            "packages": unique_packages,
            "group": None
        }
        
    except Exception:
        return {"python_version": None, "packages": [], "group": None}
