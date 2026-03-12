#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
from psd_tools import PSDImage

import os
import sys

# 添加当前脚本所在目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from layer_parser import node_from_layer
from tree_filter import filter_tree

def main():
    parser = argparse.ArgumentParser(description="Export PSD layer tree to JSON.")
    parser.add_argument("psd", help="Path to .psd file")
    parser.add_argument("--output", "-o", default="psd_layers.json", help="Output JSON path")
    parser.add_argument("--name", help="Filter by layer name")
    parser.add_argument("--match", choices=["exact", "contains"], default="exact", help="Match mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        print(f"[*] Opening PSD: {args.psd}")
    
    psd = PSDImage.open(args.psd)
    
    if args.verbose:
        print(f"[*] Extracting layers...")

    # Bug 修复：创建全局共享的命名集合
    # 之前每个顶层图层有自己的命名空间，导致跨顶层图层重名未检测
    global_used_names = set()
    tree = [node_from_layer(layer, global_used_names) for layer in psd]

    if args.name:
        if args.verbose:
            print(f"[*] Filtering by name: {args.name} (mode: {args.match})")
        filtered = []
        for node in tree:
            filtered_node = filter_tree(node, args.name, args.match)
            if filtered_node is not None:
                filtered.append(filtered_node)
        tree = filtered

    if args.verbose:
        print(f"[*] Saving output to: {args.output}")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    if args.verbose:
        print("[+] Done.")


if __name__ == "__main__":
    main()
