#!/usr/bin/env python3
import sys
import json
from collections import defaultdict


def infer_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def merge_schema(schema, obj, prefix=""):
    for key, value in obj.items():
        field = f"{prefix}.{key}" if prefix else key
        t = infer_type(value)
        schema[field].add(t)

        if isinstance(value, dict):
            merge_schema(schema, value, field)

        elif isinstance(value, list) and value:
            elem_types = {infer_type(v) for v in value}
            schema[f"{field}[]"].update(elem_types)

            for v in value:
                if isinstance(v, dict):
                    merge_schema(schema, v, f"{field}[]")


def print_schema(jsonl_path, sample_limit=None):
    schema = defaultdict(set)
    total = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            obj = json.loads(line)

            if not isinstance(obj, dict):
                print(f"Skipping non-object JSON at line {total + 1}")
                continue

            merge_schema(schema, obj)
            total += 1

            if sample_limit and total >= sample_limit:
                break

    print(f"Scanned {total} records\n")
    print("Schema:")
    for field in sorted(schema):
        print(f"{field}: {' | '.join(sorted(schema[field]))}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file.jsonl> [sample_limit]")
        sys.exit(1)

    jsonl_file = sys.argv[1]
    sample_limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    print_schema(jsonl_file, sample_limit)