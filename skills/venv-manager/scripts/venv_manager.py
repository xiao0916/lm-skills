"""venv-manager CLI - Virtual environment manager for skills.

Commands:
    detect <skill>   - Detect skill environment requirements
    ensure <skill>  - Ensure environment exists (create + install)
    run <skill> <script> [args...] - Run skill script
    status           - View all environment status
    clean            - Clean up unused environments
"""

import argparse
import os
import sys
import subprocess
import venv
from pathlib import Path
from typing import Optional, List

# Add scripts directory to path for imports
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

parser_module = __import__("parser", fromlist=["parse_skill_dependencies"])
detector_module = __import__("detector", fromlist=["detect_environment", "get_venv_path", "get_python_executable"])

parse_skill_dependencies = parser_module.parse_skill_dependencies
detect_environment = detector_module.detect_environment
get_venv_path = detector_module.get_venv_path
get_python_executable = detector_module.get_python_executable


def create_environment(skill_path: Path, group_name: Optional[str] = None) -> bool:
    """Create a virtual environment for a skill.
    
    Args:
        skill_path: Path to the skill directory
        group_name: Optional group name for the venv
        
    Returns:
        True if successful, False otherwise
    """
    skill_name = skill_path.name
    venv_name = group_name if group_name else skill_name
    env_path = get_venv_path(venv_name)
    
    print(f"Creating virtual environment: {venv_name}")
    print(f"Path: {env_path}")
    
    try:
        venv.create(env_path, with_pip=False)
        print("Virtual environment created.")
    except Exception as e:
        print(f"Error creating environment: {e}")
        return False
    
    python_exe = get_python_executable(env_path)
    
    try:
        result = subprocess.run(
            [python_exe, "-m", "ensurepip", "--upgrade"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            print("Warning: ensurepip failed, attempting alternative method...")
            try:
                import urllib.request
                import hashlib
                
                url = "https://bootstrap.pypa.io/get-pip.py"
                tmp_path = "/tmp/get-pip.py"
                
                urllib.request.urlretrieve(url, tmp_path)
                
                subprocess.run([python_exe, tmp_path], capture_output=True, timeout=120)
            except Exception as e:
                print(f"Warning: Could not install pip: {e}")
                print("You may need to install pip manually.")
    except Exception as e:
        print(f"Warning: Could not ensure pip: {e}")
    
    deps = parse_skill_dependencies(str(skill_path))
    packages = deps.get("packages", [])
    
    if packages:
        success = install_dependencies(env_path, packages)
        if not success:
            return False
        
        print("Verifying installation...")
        if not verify_installation(env_path):
            print("Warning: pip check found issues, but installation may still work.")
    
    print(f"Environment ready: {venv_name}")
    return True


def install_dependencies(env_path: str, packages: List[str]) -> bool:
    """Install packages into a virtual environment.
    
    Args:
        env_path: Path to the virtual environment
        packages: List of package specifications
        
    Returns:
        True if successful, False otherwise
    """
    python_exe = get_python_executable(env_path)
    
    print(f"Installing {len(packages)} package(s)...")
    
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            print(f"Warning: pip upgrade failed: {result.stderr}")
    except Exception as e:
        print(f"Warning: Could not upgrade pip: {e}")
    
    for pkg in packages:
        print(f"  Installing: {pkg}")
        try:
            result = subprocess.run(
                [python_exe, "-m", "pip", "install", pkg],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                print(f"Error installing {pkg}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"Error: Timeout installing {pkg}")
            return False
        except Exception as e:
            print(f"Error installing {pkg}: {e}")
            return False
    
    print(f"Installed {len(packages)} package(s) successfully.")
    return True


def verify_installation(env_path: str) -> bool:
    """Verify package installation with pip check.
    
    Args:
        env_path: Path to the virtual environment
        
    Returns:
        True if verification passes, False otherwise
    """
    python_exe = get_python_executable(env_path)
    
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "check"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("Verification passed: no broken dependencies.")
            return True
        else:
            print(f"Warning: pip check found issues:\n{result.stdout}")
            return False
    except Exception as e:
        print(f"Warning: Could not run pip check: {e}")
        return True


def _get_project_root() -> Path:
    env_root = os.environ.get("PROJECT_ROOT")
    if env_root:
        return Path(env_root)
    current_dir = Path(__file__).resolve()
    return current_dir.parent.parent.parent.parent.parent


def get_skills_dir() -> Path:
    """Get the skills directory path."""
    project_root = _get_project_root()
    return project_root / ".claude" / "skills"


def get_venvs_dir() -> Path:
    """Get the .venvs directory path."""
    project_root = _get_project_root()
    venvs_dir = project_root / ".venvs"
    venvs_dir.mkdir(exist_ok=True)
    return venvs_dir


def find_skill(skill_name: str) -> Optional[Path]:
    """Find a skill directory by name."""
    skills_dir = get_skills_dir()
    
    # Direct match
    skill_path = skills_dir / skill_name
    if skill_path.exists():
        return skill_path
    
    # Search for skill (case-insensitive)
    for item in skills_dir.iterdir():
        if item.is_dir() and item.name.lower() == skill_name.lower():
            return item
    
    return None


def cmd_detect(args: argparse.Namespace) -> int:
    """Detect skill environment requirements."""
    skill_name = args.skill
    skill_path = find_skill(skill_name)
    
    if not skill_path:
        print(f"Error: Skill '{skill_name}' not found in {get_skills_dir()}")
        return 1
    
    # Parse dependencies
    deps = parse_skill_dependencies(str(skill_path))
    
    # Detect environment
    env_info = detect_environment(str(skill_path))
    
    # Output results
    print(f"Skill: {skill_path.name}")
    print(f"Path: {skill_path}")
    print()
    print("Dependencies:")
    if deps["packages"]:
        print(f"  Python Version: {deps['python_version'] or 'default'}")
        print(f"  Packages: {', '.join(deps['packages'])}")
        print(f"  Group: {deps['group'] or 'none'}")
    else:
        print("  None")
    print()
    print("Environment:")
    print(f"  Needs venv: {env_info['needs_venv']}")
    print(f"  Existing env: {env_info['existing_env'] or 'none'}")
    print(f"  Env path: {env_info['env_path'] or 'n/a'}")
    
    return 0


def cmd_ensure(args: argparse.Namespace) -> int:
    """Ensure environment exists (create + install)."""
    skill_name = args.skill
    skill_path = find_skill(skill_name)
    
    if not skill_path:
        print(f"Error: Skill '{skill_name}' not found in {get_skills_dir()}")
        return 1
    
    # Detect environment status
    env_info = detect_environment(str(skill_path))
    
    if env_info["existing_env"]:
        print(f"Environment already exists: {env_info['existing_env']}")
        print(f"Path: {env_info['env_path']}")
        return 0
    
    if not env_info["needs_venv"]:
        print("No dependencies found. No venv needed.")
        return 0
    
    deps = parse_skill_dependencies(str(skill_path))
    group_name = deps.get("group")
    
    success = create_environment(skill_path, group_name)
    if not success:
        print("Failed to create environment.")
        return 1
    
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run skill script with proper environment."""
    skill_name = args.skill
    script_name = args.script
    
    skill_path = find_skill(skill_name)
    if not skill_path:
        print(f"Error: Skill '{skill_name}' not found in {get_skills_dir()}")
        return 1
    
    # Check environment
    env_info = detect_environment(str(skill_path))
    
    if not env_info["existing_env"]:
        print(f"Error: Environment for '{skill_name}' does not exist.")
        print(f"Run 'venv-manager.py ensure {skill_name}' first.")
        return 1
    
    # Resolve script path
    script_path = skill_path / script_name
    if not script_path.exists():
        # Try scripts subdirectory
        script_path = skill_path / "scripts" / script_name
    
    if not script_path.exists():
        print(f"Error: Script '{script_name}' not found")
        return 1
    
    # Get Python executable from venv
    python_exe = get_python_executable(env_info["env_path"])
    
    cmd = [python_exe, str(script_path)] + args.args
    
    return subprocess.call(cmd)


def cmd_status(args: argparse.Namespace) -> int:
    """View all environment status."""
    venvs_dir = get_venvs_dir()
    
    if not venvs_dir.exists() or not any(venvs_dir.iterdir()):
        print("No virtual environments found.")
        return 0
    
    print("Virtual Environments:")
    print("-" * 50)
    
    for venv in sorted(venvs_dir.iterdir()):
        if venv.is_dir():
            python_path = venv / "bin" / "python"
            if os.name == 'nt':
                python_path = venv / "Scripts" / "python.exe"
            
            exists = python_path.exists()
            status = "✓ Ready" if exists else "✗ Incomplete"
            print(f"  {venv.name}: {status}")
            if exists:
                print(f"    Path: {venv}")
    
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean up unused environments."""
    venvs_dir = get_venvs_dir()
    dry_run = args.dry_run
    
    if not venvs_dir.exists() or not any(venvs_dir.iterdir()):
        print("No virtual environments to clean.")
        return 0
    
    # Get list of skills
    skills_dir = get_skills_dir()
    skill_names = set()
    if skills_dir.exists():
        for item in skills_dir.iterdir():
            if item.is_dir():
                skill_names.add(item.name.lower())
                deps = parse_skill_dependencies(str(item))
                if deps.get("group"):
                    skill_names.add(deps["group"].lower())
    
    # Find orphan environments
    orphans = []
    for venv in venvs_dir.iterdir():
        if venv.is_dir() and venv.name.lower() not in skill_names:
            orphans.append(venv)
    
    if not orphans:
        print("No orphaned environments found.")
        return 0
    
    print(f"Found {len(orphans)} orphaned environment(s):")
    for venv in orphans:
        print(f"  - {venv.name}")
    
    if dry_run:
        print("\nDry run - no changes made.")
        return 0
    
    if not args.force:
        if not sys.stdin.isatty():
            print("\nNot in interactive mode. Use --force to skip confirmation.")
            return 1
        response = input("\nDelete these environments? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0
    
    # Delete orphans
    import shutil
    for venv in orphans:
        shutil.rmtree(venv)
        print(f"Deleted: {venv.name}")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="venv-manager: Virtual environment manager for skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # detect command
    detect_parser = subparsers.add_parser("detect", help="Detect skill environment requirements")
    detect_parser.add_argument("skill", help="Skill name")
    detect_parser.set_defaults(func=cmd_detect)
    
    # ensure command
    ensure_parser = subparsers.add_parser("ensure", help="Ensure environment exists")
    ensure_parser.add_argument("skill", help="Skill name")
    ensure_parser.set_defaults(func=cmd_ensure)
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run skill script")
    run_parser.add_argument("skill", help="Skill name")
    run_parser.add_argument("script", help="Script path (relative to skill root)")
    run_parser.add_argument("args", nargs="*", help="Script arguments")
    run_parser.set_defaults(func=cmd_run)
    
    # status command
    status_parser = subparsers.add_parser("status", help="View all environment status")
    status_parser.set_defaults(func=cmd_status)
    
    # clean command
    clean_parser = subparsers.add_parser("clean", help="Clean up unused environments")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    clean_parser.add_argument("-f", "--force", action="store_true", help="Force deletion without prompting")
    clean_parser.set_defaults(func=cmd_clean)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
