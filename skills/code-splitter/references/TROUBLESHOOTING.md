# 故障排查

## 常见问题

### 问题 1：找不到模块

**错误信息**：
```
错误：无法导入 analyzer 模块
```

**原因**：
Python 路径问题，脚本无法找到依赖模块。

**解决方案**：
1. 确保从项目根目录运行命令
2. 检查脚本目录结构是否正确
3. 手动设置 PYTHONPATH：
   ```bash
   export PYTHONPATH="${PYTHONPATH}:.claude/skills/code-splitter/scripts"
   ```

### 问题 2：没有检测到候选组件

**错误信息**：
```
未检测到高价值拆分点
```

**原因**：
- 组件结构过于简单
- 缺乏语义化 className
- 置信度阈值设置过高

**解决方案**：
1. 手动添加语义化 className：
   ```jsx
   // 修改前
   <div className={styles["wrapper"]}>
   
   // 修改后
   <div className={styles["card-wrapper"]}>
   ```

2. 降低置信度阈值：
   ```bash
   py -3 scripts/split_component.py --input ./comp/ --min-score 0.2
   ```

3. 检查 JSX 语法是否符合要求

### 问题 3：生成的组件缺少样式

**现象**：
生成的组件没有对应的 CSS 样式。

**原因**：
- CSS 规则未匹配
- 使用非 CSS Modules
- className 格式不正确

**解决方案**：
1. 确保使用 CSS Modules：
   ```css
   /* 正确 */
   .rs-card { ... }
   
   /* 错误 - 全局样式 */
   rs-card { ... }
   ```

2. 检查 className 格式：
   ```jsx
   // 支持的格式
   className={styles["rs-card"]}
   
   // 不支持的格式
   className={styles.rsCard}
   className={`rs-card ${styles.active}`}
   ```

### 问题 4：中文乱码

**现象**：
Windows 控制台输出中文乱码。

**原因**：
Windows 控制台默认编码不是 UTF-8。

**解决方案**：
1. 设置控制台编码：
   ```cmd
   chcp 65001
   ```

2. 或在脚本中设置：
   ```python
   import sys
   import io
   sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
   ```

### 问题 5：依赖安装失败

**错误信息**：
```
ModuleNotFoundError: No module named 'cssutils'
```

**解决方案**：
```bash
py -3 -m pip install cssutils
```

## 调试技巧

### 启用详细日志

```bash
py -3 scripts/split_component.py --input ./comp/ --dry-run -v
py -3 scripts/component_generator.py --input ./comp/ --output ./split/ -v
```

### 检查解析结果

```bash
# 查看 JSX 解析结果
py -3 scripts/jsx_parser.py ./comp/index.jsx --json

# 查看 CSS 解析结果
py -3 scripts/css_parser.py ./comp/index.module.css --json
```

### 保存分析结果

```bash
# Suggestion Mode 保存报告
py -3 scripts/split_component.py --input ./comp/ --dry-run --output report.md

# Generate Mode 自动生成 generation-report.json
py -3 scripts/component_generator.py --input ./comp/ --output ./split/
cat ./split/generation-report.json
```

## 联系与支持

如遇到无法解决的问题，请记录以下信息：
1. 完整的错误信息
2. 运行命令
3. 组件目录结构
4. 相关文件内容（可脱敏）
