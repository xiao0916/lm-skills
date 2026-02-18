#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检查脚本
验证运行环境是否满足 code-splitter 技能的要求

使用方法:
    py -3 scripts/check_env.py

返回:
    退出码 0 - 环境检查通过
    退出码 1 - 环境检查失败
"""

import sys
import os
import json

# 设置 stdout 编码以支持中文输出（兼容 Windows）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def check_python_version():
    """检查 Python 版本是否 >= 3.6"""
    version = sys.version_info
    version_str = "{}.{}.{}".format(version.major, version.minor, version.micro)
    
    if version.major >= 3 and version.minor >= 6:
        return {
            "ok": True,
            "message": "[OK] Python 版本检查通过 ({})".format(version_str),
            "version": version_str
        }
    else:
        return {
            "ok": False,
            "message": "[FAIL] Python 版本过低: {}，需要 >= 3.6".format(version_str),
            "version": version_str
        }


def check_directory_structure():
    """检查必要的目录结构是否存在"""
    # 获取脚本所在目录的上级目录（code-splitter 根目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(script_dir)
    
    required_dirs = [
        (skill_root, "技能根目录"),
        (os.path.join(skill_root, "scripts"), "脚本目录"),
    ]
    
    missing_dirs = []
    for dir_path, dir_name in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_name)
    
    if not missing_dirs:
        return {
            "ok": True,
            "message": "[OK] 目录结构检查通过",
            "missing": []
        }
    else:
        return {
            "ok": False,
            "message": "[FAIL] 缺少必要目录: {}".format(", ".join(missing_dirs)),
            "missing": missing_dirs
        }


def main():
    """主函数：执行环境检查并输出报告"""
    # 执行各项检查
    python_check = check_python_version()
    dir_check = check_directory_structure()
    
    # 汇总检查结果
    all_checks = {
        "python_version": python_check,
        "directory_structure": dir_check
    }
    
    # 判断整体状态
    all_ok = all(check["ok"] for check in all_checks.values())
    errors = [check["message"] for check in all_checks.values() if not check["ok"]]
    
    # 构建报告
    report = {
        "status": "ok" if all_ok else "error",
        "python_version": python_check.get("version", "unknown"),
        "checks": all_checks,
        "errors": errors
    }
    
    # 输出到控制台
    print("=" * 50)
    print("Code-Splitter 环境检查报告")
    print("=" * 50)
    print()
    
    for check_name, check_result in all_checks.items():
        print(check_result["message"])
    
    print()
    
    if all_ok:
        print("[OK] 环境检查全部通过")
        print()
        print("JSON 报告:")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    else:
        print("[FAIL] 环境检查未通过")
        print()
        print("问题详情:")
        for error in errors:
            print("  - {}".format(error))
        print()
        print("安装指导:")
        print("  1. 确保已安装 Python 3.6 或更高版本")
        print("  2. 访问 https://www.python.org/ 下载最新版 Python")
        print("  3. 重新运行此脚本验证环境")
        print()
        print("JSON 报告:")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
