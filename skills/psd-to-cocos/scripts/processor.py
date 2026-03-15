# -*- coding: utf-8 -*-
"""
核心执行器：负责调用子工具并控制转换流程。
整合了原 core/orchestrator.py 和 core/batch_processor.py 的核心逻辑。
"""

import os
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from utils import logger, normalize_psd_filename, ToolResolver
from converter import (
    extract_canvas_size,
    extract_visible_layers_nested,
    create_element_nested,
    create_cocos_layout_output
)
from exceptions import ToolExecutionError, DirectoryConflictError

class ConversionProcessor:
    """处理转换业务逻辑"""
    
    def __init__(self, output_base_dir: str):
        self.output_base_dir = Path(output_base_dir)
        self.tool_resolver = ToolResolver()

    def process_single_psd(self, psd_path: str, flat: bool = False) -> bool:
        """转换单个 PSD 文件"""
        psd_path = Path(psd_path)
        if not psd_path.exists():
            logger.error(f"文件不存在: {psd_path}")
            return False

        normalized_name = normalize_psd_filename(psd_path.name)
        output_dir = self.output_base_dir / normalized_name
        
        # 简单冲突检查：如果目录已存在，先删除（适度精简策略：直接覆盖）
        if output_dir.exists():
            logger.info(f"清理已存在的输出目录: {output_dir}")
            shutil.rmtree(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        try:
            # 1. 解析图层结构
            layers_json = output_dir / "psd_layers.json"
            reader_path = self.tool_resolver.resolve_reader()
            logger.info(f"正在解析图层: {psd_path.name}")
            # psd_layers.py 使用位置参数 psd
            subprocess.run([sys.executable, str(reader_path), str(psd_path), "-o", str(layers_json)], check=True, capture_output=True)

            # 2. 导出切图
            slicer_path = self.tool_resolver.resolve_slicer()
            logger.info(f"正在导出切图...")
            # export_slices.py 使用可选参数 --psd
            subprocess.run([sys.executable, str(slicer_path), "--psd", str(psd_path), "-o", str(images_dir), "-m", str(layers_json)], check=True, capture_output=True)

            # 3. 生成布局 JSON
            with open(layers_json, 'r', encoding='utf-8') as f:
                psd_data = json.load(f)
            
            canvas_size = extract_canvas_size(psd_data)
            logger.info(f"画布尺寸: {canvas_size[0]}x{canvas_size[1]}")

            visible_root = extract_visible_layers_nested(psd_data)
            elements = []
            if visible_root:
                # 处理根图层列表
                if isinstance(visible_root, list):
                    for layer in visible_root:
                        elements.append(create_element_nested(layer, canvas_size))
                else:
                    elements.append(create_element_nested(visible_root, canvas_size))

            layout_data = create_cocos_layout_output(elements, canvas_size, psd_path.name)
            layout_json = output_dir / "cocos_layout.json"
            with open(layout_json, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✓ 转换成功: {psd_path.name} -> {output_dir}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"子工具执行失败: {e.stderr.decode('utf-8', 'ignore')}")
            return False
        except Exception as e:
            logger.error(f"转换过程中出现异常: {str(e)}")
            return False

    def process_batch(self, input_path: str, recursive: bool = False) -> None:
        """扫描并批量处理 PSD"""
        input_path = Path(input_path)
        psd_files = []
        
        if input_path.is_file():
            psd_files = [input_path]
        else:
            pattern = "**/*.psd" if recursive else "*.psd"
            psd_files = list(input_path.glob(pattern))

        if not psd_files:
            logger.warning(f"在 {input_path} 中未找到 PSD 文件")
            return

        logger.info(f"开始批量处理 {len(psd_files)} 个文件...")
        success_count = 0
        for psd in psd_files:
            if self.process_single_psd(str(psd)):
                success_count += 1
        
        logger.info(f"批量处理完成！成功: {success_count}, 失败: {len(psd_files) - success_count}")

import sys
