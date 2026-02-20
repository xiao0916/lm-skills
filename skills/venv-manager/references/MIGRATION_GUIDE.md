# Migration Guide

This guide helps you add dependency declarations to existing skills.

## Why Add Dependencies?

Adding dependency declarations allows venv-manager to:
- Automatically create isolated virtual environments
- Install required packages
- Run scripts with the correct Python environment

## Step-by-Step Migration

### 1. Identify Dependencies

List all Python packages your skill uses:

```python
# Check imports in your scripts
import package1
import package2
```

Common sources:
- `import` statements in Python files
- Requirements files (requirements.txt, setup.py)
- Documentation (pip install commands)

### 2. Choose a Format

**Option A: Add to SKILL.md (Recommended)**

Add frontmatter to your SKILL.md:

```yaml
---
name: your-skill
dependencies:
  packages:
    - package1
    - package2>=1.0
---
```

**Option B: Create requirements.txt**

Create `requirements.txt` in your skill root:

```
package1
package2>=1.0
```

### 3. Test Detection

Run the detect command to verify:

```bash
python venv_manager.py detect your-skill
```

You should see your packages listed.

### 4. Create Environment

```bash
python venv_manager.py ensure your-skill
```

### 5. Test Execution

```bash
python venv_manager.py run your-skill scripts/your_script.py
```

## Backward Compatibility

The venv-manager supports multiple detection methods:

1. **YAML frontmatter** (preferred)
2. **requirements.txt** (fallback)
3. **pip install commands** in documentation (last resort)

Existing skills without dependency declarations will work as before - they'll simply skip virtual environment creation.

## Grouping Multiple Skills

If you have multiple skills that share dependencies, use the `group` field:

```yaml
---
name: ml-tool-1
dependencies:
  group: ml-shared
  packages:
    - torch
---
```

```yaml
---
name: ml-tool-2
dependencies:
  group: ml-shared
  packages:
    - transformers
---
```

Both skills will use the same virtual environment at `.venvs/ml-shared/`.

## Common Issues

**Missing dependencies**: If a script fails with `ModuleNotFoundError`, add the missing package to your dependencies.

**Version conflicts**: Use separate environments (different group names) for skills with conflicting dependencies.

**Platform-specific packages**: Add platform-specific packages with version specifiers, e.g., `opencv-python-headless` for Linux servers.
