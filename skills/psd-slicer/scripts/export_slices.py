#!/usr/bin/env python3
"""Export PSD layers as PNG slices."""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from psd_tools import PSDImage

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def sanitize_filename(name):
    """Convert layer name to valid filename."""
    # Replace invalid chars
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, '_')
    # Remove leading/trailing spaces and dots
    name = name.strip('. ')
    return name if name else 'unnamed'


def is_legally_named(name):
    """Check if name contains only alphanumeric, underscore, and hyphen.
    
    Legal definition: [a-zA-Z0-9_-]
    """
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))


def load_name_mapping(json_path):
    """Load name mapping from JSON file.

    Mapping structure: {layer_id: sanitized_name} or {original_name: sanitized_name}
    - 优先使用 layerId 作为 key（精确匹配，支持同名图层）
    - 回退到 originalName（向后兼容旧 JSON）
    - Value: name field from JSON (normalized valid name)

    Returns:
        dict: {layer_id or original_name: sanitized_name}
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("Error: Failed to load mapping file '{}': {}".format(json_path, e))
        sys.exit(1)

    mapping = {}
    has_layer_id = False  # 标记是否使用了 layerId

    def traverse(nodes):
        nonlocal has_layer_id
        for node in nodes:
            sanitized = node.get('name')
            layer_id = node.get('layerId')  # 获取 layerId
            original = node.get('originalName')

            if sanitized:
                if layer_id is not None:
                    # 新方式：使用 layerId 作为 key
                    has_layer_id = True
                    if layer_id in mapping:
                        print("Warning: Duplicate layerId '{}'".format(layer_id))
                    mapping[layer_id] = sanitized
                elif original:
                    # 旧方式：向后兼容（旧 JSON 没有 layerId）
                    if original in mapping:
                        print("Warning: Duplicate originalName '{}'".format(original))
                    mapping[original] = sanitized

            # 递归处理 children（保持不变）
            if 'children' in node:
                traverse(node['children'])

    traverse(data)

    if has_layer_id:
        print("Loaded {} name mappings (using layerId)".format(len(mapping)))
    else:
        print("Loaded {} name mappings (using originalName, legacy mode)".format(len(mapping)))

    return mapping


def has_prefix(name, prefix):
    """Check if layer name starts with the given prefix.
    
    Args:
        name: Layer name
        prefix: Required prefix (case-sensitive)
    
    Returns:
        True if name starts with prefix, False otherwise
    """
    return name.startswith(prefix) if prefix else True


def is_group(layer):
    """Check if layer is a group (has children)."""
    return hasattr(layer, '__iter__') and not isinstance(layer, str)


def export_layer(layer, output_dir, exported_names=None, groups_only=False, 
                 prefix_filter=None, allow_illegal_names=False, name_mapping=None, **kwargs):
    """Export a single layer as PNG.
    
    Args:
        layer: PSD layer object
        output_dir: Output directory path
        exported_names: Set of already exported names (for deduplication)
        groups_only: If True, only export layer groups (skip individual layers)
        prefix_filter: If set, only export layers whose names start with this prefix
        allow_illegal_names: If False (default), skip layers with illegal names
        name_mapping: Optional dict {psd_layer_name: sanitized_name}
                     If provided, layer.name is used as key to lookup sanitized filename.
    """
    if exported_names is None:
        exported_names = set()
    
    # Skip invisible layers
    if not layer.visible:
        return
    
    layer_is_group = is_group(layer)
    
    # If groups_only is True, skip non-group layers
    if groups_only and not layer_is_group:
        return
    
    # MANDATORY: Check legal naming (unless explicitly disabled or mapped)
    # Legal definition: [a-zA-Z0-9_-] only
    # When name_mapping is provided, we skip this check because mapped names are already sanitized
    if name_mapping is None and not allow_illegal_names and not is_legally_named(layer.name):
        return
    
    # If prefix_filter is set, skip layers that don't match the prefix
    if prefix_filter and not has_prefix(layer.name, prefix_filter):
        return

    # Skip text layers if skip_type is True
    if getattr(layer, "kind", None) == "type" and kwargs.get("skip_type"):
        # Still need to recurse if it's a group (rare for type layers, but possible)
        if layer_is_group:
            for child in layer:
                export_layer(child, output_dir, exported_names, groups_only, prefix_filter, allow_illegal_names, name_mapping, **kwargs)
        return
    
    # Try to export the layer
    try:
        # Get layer image
        img = layer.composite()
        if img is None or img.size[0] == 0 or img.size[1] == 0:
            return
        
        # Generate unique filename
        base_name = None

        # 新逻辑：优先使用 layer_id 匹配
        if name_mapping:
            # 首先尝试用 layer_id 匹配（新 JSON）
            layer_id = getattr(layer, 'layer_id', None)
            if layer_id is not None and layer_id in name_mapping:
                base_name = name_mapping[layer_id]
                print("Mapped by ID {} -> '{}.png'".format(layer_id, base_name))
            # 回退：使用 layer.name 匹配（旧 JSON 或无 layer_id 的情况）
            elif layer.name in name_mapping:
                base_name = name_mapping[layer.name]
                print("Mapped by name '{}' -> '{}.png'".format(layer.name, base_name))
            # 如果没有匹配到 mapping，但 mapping 存在且名称不合法，则跳过
            elif not allow_illegal_names and not is_legally_named(layer.name):
                print("Warning: Layer '{}' not in mapping and has illegal name, skipping".format(layer.name))
                return

        # 没有 mapping 或匹配失败，使用默认处理
        if base_name is None:
            base_name = sanitize_filename(layer.name)
        
        filename = base_name
        counter = 1
        while filename in exported_names:
            filename = "{}_{}".format(base_name, counter)
            counter += 1
        
        exported_names.add(filename)
        
        # Save as PNG
        output_path = output_dir / "{}.png".format(filename)
        img.save(output_path, 'PNG')
        layer_type = "Group" if layer_is_group else "Layer"
        print("Exported {}: {}.png".format(layer_type, filename))
        
    except Exception as e:
        print("Warning: Could not export '{}': {}".format(layer.name, e))
    
    # Recursively export children (only for groups)
    if layer_is_group:
        for child in layer:
            export_layer(child, output_dir, exported_names, groups_only, prefix_filter, allow_illegal_names, name_mapping, **kwargs)


def main():
    parser = argparse.ArgumentParser(description="Export PSD layers as PNG slices.")
    parser.add_argument("--psd", help="Path to .psd file")
    parser.add_argument("--output", "-o", default="images", help="Output directory for PNG slices")
    parser.add_argument("--groups-only", "-g", action="store_true", help="Only export layer groups, skip individual layers")
    parser.add_argument("--prefix", "-p", default=None, help="Only export layers whose names start with this prefix (e.g., 'slice-')")
    parser.add_argument("--allow-illegal-names", action="store_true", help="Allow layers with illegal names (contains non-alphanumeric/underscore/hyphen chars). Disabled by default for production safety.")
    parser.add_argument("--mapping-json", "-m", default=None, 
                       help="Path to JSON file from psd-layer-reader for name mapping. "
                            "When provided, uses originalName to match layers and "
                            "name as output filename (useful for Chinese layer names).")
    parser.add_argument("--skip-type", action="store_true", help="Skip text layers (kind == 'type')")
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Open PSD
    print("Opening PSD: {}".format(args.psd))
    modes = []
    if args.groups_only:
        modes.append("groups only")
    modes.append("legal names enforced" if not args.allow_illegal_names else "illegal names allowed")
    if args.prefix:
        modes.append("prefix '{}'".format(args.prefix))
    print("Mode: {}".format(', '.join(modes)))
    
    psd = PSDImage.open(args.psd)
    
    # Load name mapping if provided
    name_mapping = None
    if args.mapping_json:
        print("Loading name mapping from: {}".format(args.mapping_json))
        name_mapping = load_name_mapping(args.mapping_json)
        print("Loaded {} name mappings".format(len(name_mapping)))
    
    # Export all layers
    exported_names = set()
    for layer in psd:
        export_layer(layer, output_dir, exported_names, 
                    groups_only=args.groups_only, 
                    prefix_filter=args.prefix, 
                    allow_illegal_names=args.allow_illegal_names,
                    name_mapping=name_mapping,
                    skip_type=args.skip_type)
    
    mode_str = " ({})".format(', '.join(modes))
    print("\nDone! Exported to: {}{}".format(output_dir.absolute(), mode_str))


if __name__ == "__main__":
    main()
