#!/usr/bin/env python3
import argparse
import json
from psd_tools import PSDImage


def node_from_layer(layer):
    bbox = layer.bbox
    return {
        "name": layer.name,
        "kind": layer.kind,
        "visible": bool(layer.visible),
        "bbox": [bbox[0], bbox[1], bbox[2], bbox[3]] if bbox is not None else None,
        "children": [node_from_layer(child) for child in layer] if layer.is_group() else [],
    }


def match_name(name, target, mode):
    if mode == "exact":
        return name == target
    if mode == "contains":
        return target in name
    return False


def filter_tree(node, target, mode):
    matched = match_name(node["name"], target, mode)
    if matched:
        return node
    filtered_children = [
        child_filtered
        for child in node["children"]
        for child_filtered in [filter_tree(child, target, mode)]
        if child_filtered is not None
    ]
    if filtered_children:
        return {**node, "children": filtered_children}
    return None


def main():
    parser = argparse.ArgumentParser(description="Export PSD layer tree to JSON.")
    parser.add_argument("psd_path", help="Path to .psd file")
    parser.add_argument("--output", "-o", default="psd_layers.json", help="Output JSON path")
    parser.add_argument("--name", help="Filter by layer name")
    parser.add_argument("--match", choices=["exact", "contains"], default="exact", help="Match mode")
    args = parser.parse_args()

    psd = PSDImage.open(args.psd_path)
    tree = [node_from_layer(layer) for layer in psd]

    if args.name:
        filtered = []
        for node in tree:
            filtered_node = filter_tree(node, args.name, args.match)
            if filtered_node is not None:
                filtered.append(filtered_node)
        tree = filtered

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
