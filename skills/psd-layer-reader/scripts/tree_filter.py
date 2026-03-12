# -*- coding: utf-8 -*-

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
