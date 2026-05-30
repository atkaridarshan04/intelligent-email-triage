#!/usr/bin/env python3

import argparse
import base64
import json
import math
import decimal
import datetime
from pathlib import Path

import pyarrow.parquet as pq


def encode_value(value):
    """Recursively encode values into JSON-safe, loss-preserving representations."""

    if value is None:
        return None

    # Decimal: preserve exact precision
    if isinstance(value, decimal.Decimal):
        return {
            "__type__": "decimal",
            "value": str(value)
        }

    # Datetime/date/time: preserve ISO format
    if isinstance(value, datetime.datetime):
        return {
            "__type__": "datetime",
            "value": value.isoformat()
        }

    if isinstance(value, datetime.date):
        return {
            "__type__": "date",
            "value": value.isoformat()
        }

    if isinstance(value, datetime.time):
        return {
            "__type__": "time",
            "value": value.isoformat()
        }

    # Bytes/binary: preserve exact binary data
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {
            "__type__": "bytes",
            "encoding": "base64",
            "value": base64.b64encode(bytes(value)).decode("ascii")
        }

    # Float special values (JSON doesn't support these)
    if isinstance(value, float):
        if math.isnan(value):
            return {"__type__": "float", "value": "NaN"}
        if math.isinf(value):
            return {
                "__type__": "float",
                "value": "Infinity" if value > 0 else "-Infinity"
            }
        return value

    # Containers
    if isinstance(value, dict):
        return {str(k): encode_value(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [encode_value(v) for v in value]

    # PyArrow scalars sometimes expose .as_py()
    if hasattr(value, "as_py"):
        return encode_value(value.as_py())

    # Primitive JSON-safe values
    if isinstance(value, (str, int, bool)):
        return value

    # Fallback: preserve via string representation
    return {
        "__type__": type(value).__name__,
        "value": str(value)
    }


def parquet_to_jsonl(input_path, output_path, batch_size=10000):
    parquet = pq.ParquetFile(input_path)

    with open(output_path, "w", encoding="utf-8") as out:
        for batch in parquet.iter_batches(batch_size=batch_size):
            records = batch.to_pylist()
            for row in records:
                encoded = encode_value(row)
                out.write(
                    json.dumps(
                        encoded,
                        ensure_ascii=False,
                        separators=(",", ":")
                    )
                )
                out.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Parquet file to JSONL with loss-preserving encoding."
    )
    parser.add_argument("input", help="Input parquet file")
    parser.add_argument("output", help="Output jsonl file")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Rows per batch (default: 10000)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    parquet_to_jsonl(input_path, output_path, args.batch_size)

    print(f"Converted {input_path} -> {output_path}")


if __name__ == "__main__":
    main()