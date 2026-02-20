import pytest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from parser import (
    parse_skill_dependencies,
    _parse_frontmatter,
    _parse_requirements_txt,
    _parse_pip_install_commands,
    _manual_yaml_parse
)


class TestParser:
    @pytest.fixture
    def temp_skill_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_parse_skill_dependencies_empty(self, temp_skill_dir):
        result = parse_skill_dependencies(str(temp_skill_dir))
        assert result["python_version"] is None
        assert result["packages"] == []
        assert result["group"] is None

    def test_parse_skill_dependencies_nonexistent(self):
        result = parse_skill_dependencies("/nonexistent/path")
        assert result["python_version"] is None
        assert result["packages"] == []
        assert result["group"] is None

    def test_parse_frontmatter_basic(self, temp_skill_dir):
        skill_md = temp_skill_dir / "SKILL.md"
        skill_md.write_text("""---
dependencies:
  packages:
    - package1
    - package2>=1.0
---
# Skill Content
""")
        
        result = _parse_frontmatter(temp_skill_dir)
        assert result["packages"] == ["package1", "package2>=1.0"]
        assert result["python_version"] is None
        assert result["group"] is None

    def test_parse_frontmatter_full(self, temp_skill_dir):
        skill_md = temp_skill_dir / "SKILL.md"
        skill_md.write_text("""---
dependencies:
  python_version: "3.10"
  packages:
    - torch
    - transformers
  group: ml-shared
---
# Skill Content
""")
        
        result = _parse_frontmatter(temp_skill_dir)
        assert result["python_version"] == "3.10"
        assert result["packages"] == ["torch", "transformers"]
        assert result["group"] == "ml-shared"

    def test_parse_frontmatter_no_frontmatter(self, temp_skill_dir):
        skill_md = temp_skill_dir / "SKILL.md"
        skill_md.write_text("# Skill Name\n\nSome content.")
        
        result = _parse_frontmatter(temp_skill_dir)
        assert result["packages"] == []

    def test_parse_requirements_txt(self, temp_skill_dir):
        req_file = temp_skill_dir / "requirements.txt"
        req_file.write_text("""package1>=1.0
# comment
package2==2.0
package3
""")
        
        result = _parse_requirements_txt(temp_skill_dir)
        assert len(result["packages"]) == 3

    def test_parse_requirements_txt_nonexistent(self, temp_skill_dir):
        result = _parse_requirements_txt(temp_skill_dir)
        assert result["packages"] == []

    def test_parse_pip_install_commands(self, temp_skill_dir):
        skill_md = temp_skill_dir / "SKILL.md"
        skill_md.write_text("""# My Skill

Install dependencies:
pip install package1 package2

Or use pip3:
pip3 install package3
""")
        
        result = _parse_pip_install_commands(temp_skill_dir)
        assert "package1" in result["packages"]
        assert "package2" in result["packages"]
        assert "package3" in result["packages"]

    def test_manual_yaml_parse(self):
        yaml_content = """dependencies:
  python_version: "3.8"
  packages:
    - pkg1
    - pkg2
  group: mygroup
"""
        result = _manual_yaml_parse(yaml_content)
        assert result.get("dependencies", {}).get("python_version") == "3.8"
        assert "pkg1" in result.get("dependencies", {}).get("packages", [])


class TestParserPriority:
    def test_priority_frontmatter_first(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
dependencies:
  packages:
    - frontmatter-pkg
---
pip install requirements-txt-pkg
""")
        
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requirements-txt-pkg\n")
        
        result = parse_skill_dependencies(str(tmp_path))
        assert "frontmatter-pkg" in result["packages"]

    def test_priority_requirements_second(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""# My Skill
pip install fuzzy-pkg
""")
        
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requirements-txt-pkg\n")
        
        result = parse_skill_dependencies(str(tmp_path))
        assert "requirements-txt-pkg" in result["packages"]

    def test_priority_fuzzy_last(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""# My Skill
pip install fuzzy-pkg
""")
        
        result = parse_skill_dependencies(str(tmp_path))
        assert "fuzzy-pkg" in result["packages"]
