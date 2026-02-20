# Dependency Schema

This document describes the recommended format for declaring dependencies in SKILL.md files.

## Format: YAML Frontmatter

The recommended way to declare dependencies is using YAML frontmatter at the top of your SKILL.md:

```yaml
---
name: my-skill
dependencies:
  python_version: "3.8"
  packages:
    - package1
    - package2>=1.0.0
    - package3[extra]
  group: shared-group-name
---
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `python_version` | string | No | Python version requirement (e.g., "3.8", "3.10") |
| `packages` | list | No | List of package specifications |
| `group` | string | No | Shared group name for reusing environments across skills |

### Examples

**Basic dependencies:**
```yaml
---
name: image-processor
dependencies:
  packages:
    - Pillow
    - opencv-python
---
```

**With Python version:**
```yaml
---
name: ml-toolkit
dependencies:
  python_version: "3.10"
  packages:
    - numpy
    - torch
---
```

**With shared group:**
```yaml
---
name: nlp-tool
dependencies:
  group: ml-shared
  packages:
    - transformers
    - torch
---
```

## Alternative: requirements.txt

You can also place a `requirements.txt` file in the skill directory:

```
Pillow>=10.0.0
numpy>=1.24.0
```

The parser will automatically detect this file.

## Alternative: pip install commands

For quick documentation, you can include pip install commands in your SKILL.md:

```
Install dependencies:
pip install Pillow numpy
```

The parser will extract packages from these commands.
