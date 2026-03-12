#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import shutil
from pathlib import Path

# 从 utils.shared_psd_utils 引入，假设在 generate_preview.py 加入路径的工作已经或者通过调用方处理好
from utils.shared_psd_utils import ensure_dir, collect_all_images_hierarchical

IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

def _clone_layers_hierarchical(layers):
    """浅拷贝图层树（保留 Path 等对象），避免影响 HTML 预览的 class_name"""
    cloned = []
    for layer in layers:
        new_layer = dict(layer)
        children = layer.get("children")
        if children:
            new_layer["children"] = _clone_layers_hierarchical(children)
        cloned.append(new_layer)
    return cloned

def copy_images(layers, out_images, copy_all, images_dir):
    """Copy images to output directory"""
    ensure_dir(out_images)
    
    if copy_all:
        for path in images_dir.iterdir():
            if path.suffix.lower() in IMAGE_EXTS and path.is_file():
                shutil.copy2(path, out_images / path.name)
        return
    
    copied = set()
    all_images = collect_all_images_hierarchical(layers)
    for img_path in all_images:
        src = Path(img_path)
        if src.name in copied:
            continue
        try:
            shutil.copy2(src, out_images / src.name)
        except Exception as e:
            print(f"Warning: could not copy {src}: {e}")
        copied.add(src.name)
