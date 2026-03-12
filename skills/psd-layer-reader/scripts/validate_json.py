#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import argparse
import sys

def validate_node(node, path=""):
    errors = []
    required_fields = ["name", "originalName", "kind", "visible", "bbox", "children"]
    
    current_path = f"{path}/{node.get('name', 'unnamed')}"
    
    for field in required_fields:
        if field not in node:
            errors.append(f"Missing field '{field}' at {current_path}")
            
    if "children" in node and isinstance(node["children"], list):
        for child in node["children"]:
            errors.extend(validate_node(child, current_path))
            
    return errors

def main():
    parser = argparse.ArgumentParser(description="Validate PSD layer JSON output.")
    parser.add_argument("file", help="Path to JSON file to validate")
    args = parser.parse_args()

    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            print("Error: Root of JSON must be a list (array of top-level layers).")
            sys.exit(1)
            
        all_errors = []
        for i, node in enumerate(data):
            all_errors.extend(validate_node(node, f"root[{i}]"))
            
        if all_errors:
            print(f"Validation failed with {len(all_errors)} errors:")
            for err in all_errors[:20]: # Show first 20 errors
                print(f"  - {err}")
            if len(all_errors) > 20:
                print(f"  ... and {len(all_errors) - 20} more.")
            sys.exit(1)
        else:
            print("Validation successful! JSON structure is correct.")
            
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
