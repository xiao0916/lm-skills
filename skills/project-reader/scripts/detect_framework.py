#!/usr/bin/env python3
"""
前端项目框架检测脚本
检测项目的框架、UI库、构建工具、包管理器和入口文件
"""

import json
import sys
from pathlib import Path
from typing import Any


FRAMEWORKS = {
    "React": {
        "dependencies": ["react", "react-dom"],
        "files": ["src/App.js", "src/App.jsx", "src/App.tsx", "src/index.js", "src/index.tsx"],
        "keywords": ["react", "react-dom"]
    },
    "Vue": {
        "dependencies": ["vue"],
        "files": ["src/main.js", "src/main.ts", "src/App.vue"],
        "keywords": ["vue"]
    },
    "Angular": {
        "dependencies": ["@angular/core"],
        "files": ["src/main.ts", "src/app/app.component.ts"],
        "keywords": ["@angular"]
    },
    "Next.js": {
        "dependencies": ["next"],
        "files": ["src/app/page.js", "src/app/page.tsx", "pages/index.js", "pages/index.tsx"],
        "keywords": ["next"]
    },
    "Nuxt": {
        "dependencies": ["nuxt"],
        "files": ["nuxt.config.js", "nuxt.config.ts", "app.vue"],
        "keywords": ["nuxt"]
    },
    "Svelte": {
        "dependencies": ["svelte"],
        "files": ["src/main.js", "src/App.svelte"],
        "keywords": ["svelte"]
    },
    "SvelteKit": {
        "dependencies": ["@sveltejs/kit"],
        "files": ["src/routes/+page.svelte", "src/app.html"],
        "keywords": ["@sveltejs"]
    },
    "Gatsby": {
        "dependencies": ["gatsby"],
        "files": ["gatsby-config.js", "src/pages/index.js"],
        "keywords": ["gatsby"]
    },
    "Remix": {
        "dependencies": ["@remix-run/react"],
        "files": ["app/root.tsx", "app/routes/_index.tsx"],
        "keywords": ["@remix-run"]
    }
}

UI_LIBRARIES = {
    "Material UI": {
        "dependencies": ["@mui/material", "@material-ui/core"],
        "keywords": ["@mui", "@material-ui"]
    },
    "Ant Design": {
        "dependencies": ["antd"],
        "keywords": ["antd", "ant-design"]
    },
    "Radix UI": {
        "dependencies": ["@radix-ui/react"],
        "keywords": ["@radix-ui"]
    },
    "Chakra UI": {
        "dependencies": ["@chakra-ui/react"],
        "keywords": ["@chakra-ui"]
    },
    "Element Plus": {
        "dependencies": ["element-plus"],
        "keywords": ["element-plus"]
    },
    "Vuetify": {
        "dependencies": ["vuetify"],
        "keywords": ["vuetify"]
    },
    "Tailwind CSS": {
        "dependencies": ["tailwindcss"],
        "keywords": ["tailwindcss", "tailwind"],
        "files": ["tailwind.config.js", "tailwind.config.ts", "postcss.config.js"]
    },
    "Styled Components": {
        "dependencies": ["styled-components"],
        "keywords": ["styled-components"]
    }
}

BUILD_TOOLS = {
    "Vite": {
        "dependencies": ["vite"],
        "files": ["vite.config.js", "vite.config.ts", "vite.config.mjs"],
        "keywords": ["vite"]
    },
    "Webpack": {
        "dependencies": ["webpack"],
        "files": ["webpack.config.js", "webpack.config.ts"],
        "keywords": ["webpack"]
    },
    "Turbopack": {
        "dependencies": ["@next/turbopack"],
        "keywords": ["turbopack"]
    },
    "Rollup": {
        "dependencies": ["rollup"],
        "files": ["rollup.config.js", "rollup.config.mjs"],
        "keywords": ["rollup"]
    },
    "Parcel": {
        "dependencies": ["parcel"],
        "files": [".parcelrc"],
        "keywords": ["parcel"]
    },
    "esbuild": {
        "dependencies": ["esbuild"],
        "keywords": ["esbuild"]
    }
}

PACKAGE_MANAGERS = {
    "npm": {
        "files": ["package-lock.json"]
    },
    "yarn": {
        "files": ["yarn.lock"]
    },
    "pnpm": {
        "files": ["pnpm-lock.yaml"]
    },
    "bun": {
        "files": ["bun.lockb"]
    }
}

ENTRY_PATTERNS = {
    "React": ["src/index.js", "src/index.tsx", "src/index.jsx", "src/main.js", "src/main.tsx"],
    "Vue": ["src/main.js", "src/main.ts", "main.js", "main.ts"],
    "Angular": ["src/main.ts", "main.ts"],
    "Next.js": ["src/app/layout.js", "src/app/layout.tsx", "pages/_app.js", "pages/_app.tsx"],
    "Nuxt": ["nuxt.config.js", "nuxt.config.ts"],
    "Svelte": ["src/main.js", "src/main.ts"],
    "SvelteKit": ["src/routes/+page.svelte", "src/app.html"],
    "Gatsby": ["gatsby-browser.js", "gatsby-ssr.js"],
    "Remix": ["remix.config.js", "app/root.tsx"]
}


def read_package_json(project_path: Path) -> dict[str, Any] | None:
    package_json_path = project_path / "package.json"
    if not package_json_path.exists():
        return None
    
    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_dependencies(package_json: dict[str, Any]) -> list[str]:
    deps = []
    
    for dep_type in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
        if dep_type in package_json:
            deps.extend(list(package_json[dep_type].keys()))
    
    return deps


def detect_framework(dependencies: list[str], project_path: Path) -> str | None:
    for framework, config in FRAMEWORKS.items():
        for dep in config.get("dependencies", []):
            if dep in dependencies:
                return framework
    
    for framework, config in FRAMEWORKS.items():
        for file_path in config.get("files", []):
            if (project_path / file_path).exists():
                return framework
    
    return None


def detect_ui_library(dependencies: list[str]) -> str | None:
    for ui_lib, config in UI_LIBRARIES.items():
        for dep in config.get("dependencies", []):
            if dep in dependencies:
                return ui_lib
    
    return None


def detect_build_tool(dependencies: list[str], project_path: Path) -> str | None:
    for tool, config in BUILD_TOOLS.items():
        for dep in config.get("dependencies", []):
            if dep in dependencies:
                return tool
    
    for tool, config in BUILD_TOOLS.items():
        for file_path in config.get("files", []):
            if (project_path / file_path).exists():
                return tool
    
    if "next" in dependencies:
        package_json = read_package_json(project_path)
        if package_json:
            scripts = package_json.get("scripts", {})
            for script in scripts.values():
                if "turbopack" in str(script):
                    return "Turbopack"
    
    return None


def detect_package_manager(project_path: Path) -> str | None:
    for pm, config in PACKAGE_MANAGERS.items():
        for file_path in config.get("files", []):
            if (project_path / file_path).exists():
                return pm
    
    return None


def detect_entry_points(framework: str | None, project_path: Path) -> list[str]:
    if not framework:
        common_entries = [
            "src/index.js", "src/index.ts", "src/index.tsx", "src/index.jsx",
            "src/main.js", "src/main.ts", "src/main.tsx", "src/main.jsx",
            "index.js", "index.ts", "main.js", "main.ts"
        ]
        return [f for f in common_entries if (project_path / f).exists()]
    
    patterns = ENTRY_PATTERNS.get(framework, [])
    found = [f for f in patterns if (project_path / f).exists()]
    
    if not found:
        common_entries = [
            "src/index.js", "src/index.ts", "src/index.tsx", "src/index.jsx",
            "src/main.js", "src/main.ts", "src/main.tsx", "src/main.jsx"
        ]
        found = [f for f in common_entries if (project_path / f).exists()]
    
    return found


def detect_tailwind_config(project_path: Path) -> bool:
    config_files = [
        "tailwind.config.js",
        "tailwind.config.ts",
        "tailwind.config.mjs",
        "tailwind.config.cjs",
        "postcss.config.js",
        "postcss.config.ts"
    ]
    
    for config_file in config_files:
        config_path = project_path / config_file
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "tailwind" in content.lower():
                        return True
            except IOError:
                pass
    
    return False


def detect_project(project_path: str) -> dict[str, Any]:
    project_path_resolved = Path(project_path).resolve()
    path_str = str(project_path_resolved)
    
    if not project_path_resolved.exists():
        return {"error": f"项目路径不存在: {path_str}"}
    
    if not project_path_resolved.is_dir():
        return {"error": f"路径不是目录: {path_str}"}
    
    package_json = read_package_json(project_path_resolved)
    dependencies = get_dependencies(package_json) if package_json else []
    
    framework = detect_framework(dependencies, project_path_resolved)
    ui_library = detect_ui_library(dependencies)
    build_tool = detect_build_tool(dependencies, project_path_resolved)
    package_manager = detect_package_manager(project_path_resolved)
    entry_points = detect_entry_points(framework, project_path_resolved)
    
    if not ui_library and detect_tailwind_config(project_path_resolved):
        ui_library = "Tailwind CSS"
    
    result: dict[str, Any] = {
        "framework": framework,
        "ui_library": ui_library,
        "build_tool": build_tool,
        "package_manager": package_manager,
        "dependencies": dependencies,
        "entry_points": entry_points
    }
    
    if package_json:
        result["project_name"] = package_json.get("name")
        result["project_version"] = package_json.get("version")
        result["project_description"] = package_json.get("description")
        
        if "scripts" in package_json:
            result["scripts"] = package_json["scripts"]
    
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python detect_framework.py <项目路径>")
        print("示例: python detect_framework.py /path/to/project")
        sys.exit(1)
    
    project_path = sys.argv[1]
    result = detect_project(project_path)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
