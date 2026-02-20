import pytest
import tempfile
import shutil
from pathlib import Path
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import venv_manager


class TestCLI:
    @pytest.fixture
    def venv_manager_script(self):
        return str(Path(__file__).parent.parent / "scripts" / "venv_manager.py")

    def test_help_command(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "venv-manager" in result.stdout
        assert "detect" in result.stdout
        assert "ensure" in result.stdout
        assert "run" in result.stdout
        assert "status" in result.stdout
        assert "clean" in result.stdout

    def test_detect_help(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "detect", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_ensure_help(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "ensure", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_run_help(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "run", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_status_help(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "status", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_clean_help(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "clean", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_detect_nonexistent_skill(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "detect", "nonexistent-skill-xyz"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "not found" in result.stdout.lower() or "not found" in result.stderr.lower()

    def test_status_empty(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "status"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_clean_dry_run(self, venv_manager_script):
        result = subprocess.run(
            [sys.executable, venv_manager_script, "clean", "--dry-run"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0


class TestCLIIntegration:
    @pytest.fixture
    def temp_skill(self, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
dependencies:
  packages:
    - requests
---
# Test Skill
""")
        
        return skill_dir

    def test_detect_with_skill(self, temp_skill, venv_manager_script, monkeypatch):
        def mock_get_skills_dir():
            return temp_skill.parent
        
        monkeypatch.setattr(venv_manager, "get_skills_dir", mock_get_skills_dir)
        
        result = subprocess.run(
            [sys.executable, venv_manager_script, "detect", "test-skill"],
            capture_output=True,
            text=True,
            cwd=str(temp_skill.parent.parent.parent)
        )
        assert result.returncode == 0
        assert "test-skill" in result.stdout.lower()
