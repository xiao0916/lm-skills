import pytest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from detector import detect_environment, get_venv_path, get_python_executable


class TestDetector:
    @pytest.fixture
    def temp_skill_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_detect_environment_no_dependencies(self, temp_skill_dir):
        skill_md = temp_skill_dir / "SKILL.md"
        skill_md.write_text("# My Skill\n\nNo dependencies.")
        
        result = detect_environment(str(temp_skill_dir))
        assert result["needs_venv"] is False
        assert result["existing_env"] is None

    def test_detect_environment_with_dependencies(self, temp_skill_dir):
        skill_md = temp_skill_dir / "SKILL.md"
        skill_md.write_text("""---
dependencies:
  packages:
    - some-package
---
# My Skill
""")
        
        result = detect_environment(str(temp_skill_dir))
        assert result["needs_venv"] is True
        assert result["existing_env"] is None

    def test_detect_environment_nonexistent(self):
        result = detect_environment("/nonexistent/path")
        assert result["needs_venv"] is False
        assert result["existing_env"] is None


class TestGetVenvPath:
    def test_get_venv_path_format(self):
        path = get_venv_path("test-skill")
        assert ".venvs" in path
        assert path.endswith("test-skill")

    def test_get_venv_path_special_chars(self):
        path = get_venv_path("my_skill-123")
        assert "my_skill-123" in path


class TestGetPythonExecutable:
    def test_get_python_executable_unix(self):
        path = get_python_executable("/fake/path")
        assert "python" in path

    def test_get_python_executable_format(self):
        path = get_python_executable("/some/venv")
        assert path.endswith("bin/python") or "Scripts" in path


class TestEnvironmentDetection:
    def test_with_group(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
dependencies:
  packages:
    - torch
  group: ml-shared
---
# My Skill
""")
        
        result = detect_environment(str(tmp_path))
        assert result["needs_venv"] is True
        assert "ml-shared" in result["env_path"] or "ml-shared" in str(result["env_path"])

    def test_priority_with_existing_venv(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
dependencies:
  packages:
    - some-package
---
# My Skill
""")
        
        skill_name = tmp_path.name
        venv_path = get_venv_path(skill_name)
        
        result = detect_environment(str(tmp_path))
        assert "needs_venv" in result
        assert "existing_env" in result
