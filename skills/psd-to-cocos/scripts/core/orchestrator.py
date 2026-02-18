"""
PSD to Cocos 核心协调器

提供目录管理、工具调用协调、原子操作等功能。
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from utils.tool_resolver import ToolPathResolver
from utils.progress import RichProgressDisplay, StepProgressController
from utils.reporter import ResultReporter, create_reporter
from utils.logger import Logger, get_logger
from utils.filename_normalizer import normalize_psd_filename
from converter import bbox_to_cocos_position, validate_bbox
from common.layer_utils import extract_visible_layers_nested
from common.element_builder import create_element_nested
from common.json_utils import create_cocos_layout_output
from exceptions import (
    PSDToCocosError,
    ToolNotFoundError,
    ToolExecutionError,
    DirectoryConflictError,
    InvalidInputError,
    AtomicOperationError,
    InvalidPsdError,
    DiskFullError,
)


class ConflictStrategy(Enum):
    """目录冲突处理策略
    
    - OVERWRITE: 删除现有目录并重新创建
    - SKIP: 跳过，如果目录已存在则直接返回成功
    - RENAME: 重命名现有目录（添加时间戳后缀）
    - ASK: 抛出异常，要求用户手动处理
    """
    OVERWRITE = auto()
    SKIP = auto()
    RENAME = auto()
    ASK = auto()


@dataclass
class ConversionResult:
    """转换结果数据类
    
    Attributes:
        success: 转换是否成功
        output_dir: 输出目录路径
        psd_layers_json: psd_layers.json 文件路径
        images_dir: images 目录路径
        cocos_layout_json: cocos_layout.json 文件路径
        message: 状态消息
    """
    success: bool
    output_dir: str
    psd_layers_json: Optional[str] = None
    images_dir: Optional[str] = None
    cocos_layout_json: Optional[str] = None
    message: str = ""


class Orchestrator:
    """PSD to Cocos 核心协调器
    
    负责：
    - 工具路径发现和验证
    - 输出目录管理和冲突处理
    - 原子操作（临时目录 + 移动）
    - 协调 psd-layer-reader 和 psd-slicer 的执行
    """
    
    def __init__(
        self,
        tool_resolver: Optional[ToolPathResolver] = None,
        verbose: bool = False,
        conflict_strategy: ConflictStrategy = ConflictStrategy.OVERWRITE,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        enable_progress: bool = True,
        console = None,
        logger: Optional[Logger] = None
    ):
        """初始化协调器

        Args:
            tool_resolver: 工具路径解析器，如果为 None 则使用默认实例
            verbose: 是否输出详细日志
            conflict_strategy: 目录冲突处理策略
            progress_callback: 进度回调函数 (step_name, current_step, total_steps)
            enable_progress: 是否启用 Rich 进度显示（默认 True，非交互环境自动禁用）
            console: Rich Console 实例，用于进度显示
            logger: 日志记录器实例，如果为 None 则使用默认实例
        """
        self.tool_resolver = tool_resolver or ToolPathResolver()
        self.verbose = verbose
        self.conflict_strategy = conflict_strategy
        self.progress_callback = progress_callback
        self.enable_progress = enable_progress

        # 初始化日志记录器
        import logging
        self.logger = logger or get_logger(
            level=logging.DEBUG if verbose else logging.INFO,
            verbose=verbose
        )
        self.logger.debug("Orchestrator 初始化完成")

        # 初始化进度显示和报告器
        self.progress_display = RichProgressDisplay(console=console, enabled=enable_progress)
        self.reporter = create_reporter(console=console)

        self._cached_tools: dict[str, Path] = {}
    
    def _log(self, message: str) -> None:
        """输出日志（兼容性方法，委托给 logger）

        Args:
            message: 要输出的消息
        """
        self.logger.debug(message)
    
    def _report_progress(self, step_name: str, current: int, total: int) -> None:
        """报告进度
        
        Args:
            step_name: 步骤名称
            current: 当前步骤（从1开始）
            total: 总步骤数
        """
        if self.progress_callback:
            self.progress_callback(step_name, current, total)
    
    def validate_input(self, psd_path: str) -> None:
        """验证输入文件

        Args:
            psd_path: PSD 文件路径

        Raises:
            InvalidInputError: 当文件不存在或格式不正确时
        """
        self.logger.debug(f"验证输入文件: {psd_path}")

        if not os.path.exists(psd_path):
            self.logger.error(f"PSD 文件不存在: {psd_path}")
            raise InvalidInputError("PSD 文件不存在", psd_path)

        if not os.path.isfile(psd_path):
            self.logger.error(f"路径不是文件: {psd_path}")
            raise InvalidInputError("路径不是文件", psd_path)

        if not psd_path.lower().endswith('.psd'):
            self.logger.error(f"文件不是 PSD 格式: {psd_path}")
            raise InvalidInputError("文件不是 PSD 格式（扩展名应为 .psd）", psd_path)

        self.logger.debug(f"输入文件验证通过: {psd_path}")
    
    def resolve_tools(self) -> tuple[Path, Path]:
        """解析所有工具路径

        Returns:
            (psd_layer_reader_path, psd_slicer_path) 元组

        Raises:
            ToolNotFoundError: 当任一工具未找到时
        """
        self.logger.debug("开始解析工具路径")

        try:
            if 'psd_layer_reader' not in self._cached_tools:
                self.logger.debug("解析 psd-layer-reader 路径")
                self._cached_tools['psd_layer_reader'] = self.tool_resolver.resolve_psd_layer_reader()
                self.logger.debug(f"psd-layer-reader 路径: {self._cached_tools['psd_layer_reader']}")

            if 'psd_slicer' not in self._cached_tools:
                self.logger.debug("解析 psd-slicer 路径")
                self._cached_tools['psd_slicer'] = self.tool_resolver.resolve_psd_slicer()
                self.logger.debug(f"psd-slicer 路径: {self._cached_tools['psd_slicer']}")

            return (
                self._cached_tools['psd_layer_reader'],
                self._cached_tools['psd_slicer']
            )
        except ToolNotFoundError as e:
            self.logger.log_tool_not_found(e.tool_name, e.search_paths)
            raise
    
    def handle_directory_conflict(self, output_dir: str) -> str:
        """处理输出目录冲突

        Args:
            output_dir: 目标输出目录

        Returns:
            最终使用的输出目录路径

        Raises:
            DirectoryConflictError: 当策略为 ASK 且目录存在时，
                                   或策略为 RENAME 但重命名失败时
        """
        self.logger.debug(f"检查输出目录冲突: {output_dir}")

        if not os.path.exists(output_dir):
            self.logger.debug(f"输出目录不存在，无需处理: {output_dir}")
            return output_dir

        if self.conflict_strategy == ConflictStrategy.SKIP:
            self.logger.info(f"目录已存在，跳过: {output_dir}")
            return output_dir

        elif self.conflict_strategy == ConflictStrategy.OVERWRITE:
            self.logger.info(f"删除现有目录: {output_dir}")
            try:
                shutil.rmtree(output_dir)
                self.logger.debug(f"目录删除成功: {output_dir}")
            except Exception as e:
                self.logger.error(f"删除目录失败: {output_dir} - {str(e)}")
                raise DirectoryConflictError(output_dir, strategy="OVERWRITE") from e
            return output_dir

        elif self.conflict_strategy == ConflictStrategy.RENAME:
            import time
            timestamp = int(time.time())
            new_dir = f"{output_dir}_bak_{timestamp}"
            self.logger.info(f"重命名现有目录: {output_dir} -> {new_dir}")

            try:
                shutil.move(output_dir, new_dir)
                self.logger.debug(f"目录重命名成功")
                return output_dir
            except Exception as e:
                self.logger.error(f"重命名目录失败: {str(e)}")
                raise DirectoryConflictError(
                    output_dir,
                    strategy="RENAME"
                ) from e

        else:  # ASK
            self.logger.error(f"目录冲突，策略为 ASK: {output_dir}")
            raise DirectoryConflictError(output_dir, strategy="ASK")
    
    def run_psd_layer_reader(
        self,
        psd_path: str,
        output_dir: str,
        reader_script: Path
    ) -> str:
        """运行 psd-layer-reader 工具

        Args:
            psd_path: PSD 文件路径
            output_dir: 输出目录
            reader_script: psd_layers.py 脚本路径

        Returns:
            生成的 psd_layers.json 文件路径

        Raises:
            ToolExecutionError: 当工具执行失败时
        """
        output_file = os.path.join(output_dir, "psd_layers.json")

        self.logger.info(f"运行 psd-layer-reader: {psd_path}")
        self.logger.debug(f"输出文件: {output_file}")
        self.logger.debug(f"使用脚本: {reader_script}")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(reader_script),
                    "--psd", psd_path,
                    "-o", output_file
                ],
                capture_output=True,
                text=True,
                check=True
            )

            if result.stdout:
                self.logger.debug(f"psd-layer-reader 输出:\n{result.stdout}")

            self.logger.info(f"psd-layer-reader 执行成功: {output_file}")
            return output_file

        except subprocess.CalledProcessError as e:
            self.logger.error(f"psd-layer-reader 执行失败 (退出码: {e.returncode})")
            if e.stderr:
                self.logger.error(f"错误输出: {e.stderr}")

            # 检查是否是 PSD 文件损坏
            if "invalid" in e.stderr.lower() or "corrupt" in e.stderr.lower():
                self.logger.error("PSD 文件可能损坏或格式不支持")

            raise ToolExecutionError(
                tool_name="psd-layer-reader",
                returncode=e.returncode,
                stderr=e.stderr
            ) from e
    
    def run_psd_slicer(
        self,
        psd_path: str,
        output_dir: str,
        mapping_json: str,
        slicer_script: Path
    ) -> str:
        """运行 psd-slicer 工具

        Args:
            psd_path: PSD 文件路径
            output_dir: 输出目录
            mapping_json: psd_layers.json 文件路径
            slicer_script: export_slices.py 脚本路径

        Returns:
            生成的 images 目录路径

        Raises:
            ToolExecutionError: 当工具执行失败时
        """
        images_dir = os.path.join(output_dir, "images")

        self.logger.info(f"运行 psd-slicer: {psd_path}")
        self.logger.debug(f"输出目录: {images_dir}")
        self.logger.debug(f"使用脚本: {slicer_script}")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(slicer_script),
                    "--psd", psd_path,
                    "-o", images_dir,
                    "--mapping-json", mapping_json
                ],
                capture_output=True,
                text=True,
                check=True
            )

            if result.stdout:
                self.logger.debug(f"psd-slicer 输出:\n{result.stdout}")

            self.logger.info(f"psd-slicer 执行成功: {images_dir}")
            return images_dir

        except subprocess.CalledProcessError as e:
            self.logger.error(f"psd-slicer 执行失败 (退出码: {e.returncode})")
            if e.stderr:
                self.logger.error(f"错误输出: {e.stderr}")

            # 检查是否是磁盘空间不足
            if "no space left" in e.stderr.lower() or "disk full" in e.stderr.lower():
                self.logger.error("磁盘空间不足，无法导出图片")

            raise ToolExecutionError(
                tool_name="psd-slicer",
                returncode=e.returncode,
                stderr=e.stderr
            ) from e
    
    def _extract_canvas_size(self, data):
        """从图层数据智能提取画布尺寸（优先原点图层）"""
        candidates = []
        
        def collect_layers(item):
            if isinstance(item, list):
                for child in item:
                    collect_layers(child)
            elif isinstance(item, dict):
                if item.get("visible", True) and "bbox" in item:
                    bbox = item["bbox"]
                    if validate_bbox(bbox):
                        x1, y1, x2, y2 = bbox
                        width = x2 - x1
                        height = y2 - y1
                        area = width * height
                        is_origin = abs(x1) < 10 and abs(y1) < 10
                        candidates.append({
                            "width": width,
                            "height": height,
                            "area": area,
                            "is_origin": is_origin
                        })
                if "children" in item:
                    collect_layers(item["children"])
        
        collect_layers(data)
        
        if not candidates:
            return None
        
        # 优先选择原点图层
        origin_candidates = [c for c in candidates if c["is_origin"]]
        if origin_candidates:
            best = max(origin_candidates, key=lambda x: x["area"])
            return [best["width"], best["height"]]
        
        # 否则选面积最大的
        best = max(candidates, key=lambda x: x["area"])
        return [best["width"], best["height"]]
    
    def generate_cocos_layout(
        self,
        psd_layers_json: str,
        temp_output: str,
        psd_name: str,
        final_output_dir: str
    ) -> str:
        """生成 Cocos 布局 JSON

        使用改进的逻辑（正确处理 visible=false）将 psd_layers.json 转换为 cocos_layout.json

        Args:
            psd_layers_json: psd_layers.json 文件路径
            temp_output: 临时输出目录（用于保存文件）
            psd_name: PSD 文件名（用于元数据）
            final_output_dir: 最终输出目录（用于生成 legal_name 字段）

        Returns:
            生成的 cocos_layout.json 文件路径
        """
        self.logger.info("生成 Cocos 布局 JSON")
        
        # 读取 psd_layers.json
        with open(psd_layers_json, 'r', encoding='utf-8') as f:
            psd_data = json.load(f)
        
        # 智能提取画布尺寸
        canvas_size = self._extract_canvas_size(psd_data)
        
        if not canvas_size:
            self.logger.warning("无法从可见图层提取画布尺寸，使用默认 1920x1080")
            canvas_size = [1920, 1080]
        
        # 提取可见图层（保留嵌套结构）
        visible_layers = extract_visible_layers_nested(psd_data)
        
        # 转换为 Cocos 元素
        elements = []
        for layer_info in visible_layers:
            element = create_element_nested(layer_info, canvas_size, bbox_to_cocos_position,
                                          center_coordinates=True, parent_cocos_pos=None)
            elements.append(element)
        
        # 转换完成后构建输出
        # 计算 normalized_name
        normalized_name = normalize_psd_filename(psd_name)

        # 构建输出
        output_data = create_cocos_layout_output(elements, psd_name, canvas_size, 
                                                 normalized_name)

        # 保存输出到临时目录
        output_file = os.path.join(temp_output, "cocos_layout.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Cocos 布局已生成: {output_file}")
        self.logger.info(f"包含 {len(output_data['elements'])} 个元素")
        
        return output_file
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳字符串
        
        Returns:
            ISO 格式的时间戳字符串
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _count_elements(self, data) -> int:
        """统计元素数量
        
        Args:
            data: psd_layers.json 数据结构
            
        Returns:
            可见元素数量
        """
        count = 0
        
        def count_recursive(item):
            nonlocal count
            if isinstance(item, list):
                for child in item:
                    count_recursive(child)
            elif isinstance(item, dict):
                if item.get("visible", True):
                    count += 1
                if "children" in item:
                    count_recursive(item["children"])
        
        count_recursive(data)
        return count
    
    def convert(
        self,
        psd_path: str,
        output_dir: str,
        flat: bool = False
    ) -> ConversionResult:
        """执行完整的 PSD to Cocos 转换流程

        使用原子操作：在临时目录中完成所有操作，最后原子移动。

        Args:
            psd_path: PSD 文件路径
            output_dir: 目标输出目录
            flat: 是否使用平铺结构

        Returns:
            ConversionResult 对象
        """
        psd_name = os.path.basename(psd_path)

        self.logger.log_conversion_start(psd_path, output_dir)

        # 定义转换步骤
        steps = ["验证输入", "解析工具路径", "导出图层结构", "导出 PNG 切片", "生成 Cocos 布局", "移动到最终位置"]

        try:
            with self.progress_display.step_progress(steps) as step_controller:
                # Step 0: 验证输入
                step_controller.start_step("验证输入")
                self._report_progress("验证输入", 0, 4)
                self.logger.log_step_start("验证输入")
                self.validate_input(psd_path)
                self.logger.log_step_complete("验证输入", success=True)
                step_controller.complete_step("验证输入", success=True)

                # Step 1: 解析工具路径
                step_controller.start_step("解析工具路径")
                self._report_progress("解析工具路径", 1, 4)
                self.logger.log_step_start("解析工具路径")
                reader_script, slicer_script = self.resolve_tools()
                self.logger.debug(f"使用工具: psd-layer-reader={reader_script}, psd-slicer={slicer_script}")
                self.logger.log_step_complete("解析工具路径", success=True)
                step_controller.complete_step("解析工具路径", success=True)

                # 处理目录冲突
                final_output_dir = self.handle_directory_conflict(output_dir)

                # Step 2-4: 原子操作
                step_controller.start_step("导出图层结构")
                self._report_progress("执行转换（原子操作）", 2, 4)

                with tempfile.TemporaryDirectory() as temp_dir:
                    self.logger.debug(f"创建临时目录: {temp_dir}")
                    temp_output = os.path.join(temp_dir, 'output')
                    os.makedirs(temp_output, exist_ok=True)

                    # Step 2: 运行 psd-layer-reader
                    self.logger.info("步骤 1/3: 导出图层结构...")
                    self.logger.log_step_start("导出图层结构")
                    psd_layers_json = self.run_psd_layer_reader(
                        psd_path, temp_output, reader_script
                    )
                    self.logger.log_step_complete("导出图层结构", success=True)
                    step_controller.complete_step("导出图层结构", success=True)

                    # Step 3: 运行 psd-slicer
                    step_controller.start_step("导出 PNG 切片")
                    self.logger.info("步骤 2/3: 导出 PNG 切片...")
                    self.logger.log_step_start("导出 PNG 切片")
                    images_dir = self.run_psd_slicer(
                        psd_path, temp_output, psd_layers_json, slicer_script
                    )
                    self.logger.log_step_complete("导出 PNG 切片", success=True)
                    step_controller.complete_step("导出 PNG 切片", success=True)

                    # Step 4: 生成 Cocos 布局
                    step_controller.start_step("生成 Cocos 布局")
                    self.logger.info("步骤 3/3: 生成 Cocos 布局...")
                    self.logger.log_step_start("生成 Cocos 布局")
                    cocos_layout_json = self.generate_cocos_layout(
                        psd_layers_json, temp_output, psd_name, final_output_dir
                    )
                    self.logger.log_step_complete("生成 Cocos 布局", success=True)
                    step_controller.complete_step("生成 Cocos 布局", success=True)

                    # Step 5: 原子移动
                    step_controller.start_step("移动到最终位置")
                    self._report_progress("移动到最终位置", 3, 4)
                    self.logger.info(f"原子移动: {temp_output} -> {final_output_dir}")

                    try:
                        shutil.move(temp_output, final_output_dir)
                        self.logger.debug("原子移动成功")
                        step_controller.complete_step("移动到最终位置", success=True)
                    except Exception as e:
                        self.logger.error(f"原子移动失败: {str(e)}")
                        step_controller.complete_step("移动到最终位置", success=False, message=str(e))
                        raise AtomicOperationError(
                            operation="move",
                            temp_path=temp_output,
                            target_path=final_output_dir
                        ) from e

            # 完成
            self._report_progress("完成", 4, 4)

            psd_layers_json_path = os.path.join(final_output_dir, "psd_layers.json")
            element_count = self._count_elements_from_json(psd_layers_json_path)

            self.logger.log_conversion_success(psd_path, final_output_dir, element_count)

            result = ConversionResult(
                success=True,
                output_dir=final_output_dir,
                psd_layers_json=psd_layers_json_path,
                images_dir=os.path.join(final_output_dir, "images"),
                cocos_layout_json=os.path.join(final_output_dir, "cocos_layout.json"),
                message="转换成功完成"
            )

            # 打印转换结果
            self.reporter.print_conversion_result(
                psd_path=psd_path,
                output_dir=final_output_dir,
                success=True,
                message="转换成功完成",
                element_count=element_count
            )

            return result

        except PSDToCocosError as e:
            self.logger.log_conversion_failure(psd_path, str(e))
            # 打印失败结果
            self.reporter.print_conversion_result(
                psd_path=psd_path,
                output_dir=output_dir,
                success=False,
                message=str(e)
            )
            raise
        except Exception as e:
            error_msg = f"转换失败: {str(e)}"
            self.logger.exception(f"转换过程发生异常: {error_msg}")
            # 打印失败结果
            self.reporter.print_conversion_result(
                psd_path=psd_path,
                output_dir=output_dir,
                success=False,
                message=error_msg
            )
            return ConversionResult(
                success=False,
                output_dir=output_dir,
                message=error_msg
            )
    
    def _count_elements_from_json(self, psd_layers_json: str) -> int:
        """从 JSON 文件统计元素数量
        
        Args:
            psd_layers_json: psd_layers.json 文件路径
            
        Returns:
            元素数量
        """
        try:
            with open(psd_layers_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._count_elements(data)
        except Exception:
            return 0
