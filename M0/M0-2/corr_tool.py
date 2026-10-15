#!/usr/bin/env python3
"""从 YAML 配置读取两列 CSV 数据，计算 Pearson 相关系数。"""

import argparse
import csv
import math
import sys
from pathlib import Path

import yaml


def pearson(xs, ys):
    """手写中心化公式，以 hypot 避免平方和乘积溢出。"""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("两列必须长度一致，并至少包含两条数据")
    if not all(math.isfinite(v) for v in [*xs, *ys]):
        raise ValueError("数据必须是有限数值，不接受 NaN 或 Infinity")
    n = len(xs)
    mean_x = math.fsum(x / n for x in xs)
    mean_y = math.fsum(y / n for y in ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    scale_x, scale_y = math.hypot(*dx), math.hypot(*dy)
    if scale_x == 0 or scale_y == 0:
        raise ValueError("某列方差为零，相关系数无定义")
    if not math.isfinite(scale_x) or not math.isfinite(scale_y):
        raise ValueError("数据数值范围过大，无法可靠计算")
    return max(-1.0, min(1.0, math.fsum(
        (a / scale_x) * (b / scale_y) for a, b in zip(dx, dy)
    )))


def read_columns(path, x_column, y_column):
    xs, ys = [], []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not reader.fieldnames:
            raise ValueError("CSV 为空或缺少表头")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV 表头包含重复列名")
        for column in (x_column, y_column):
            if column not in reader.fieldnames:
                raise ValueError(f"CSV 缺少列：{column}")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV 第 {reader.line_num} 行的列数与表头不一致")
            try:
                xs.append(float(row[x_column]))
                ys.append(float(row[y_column]))
            except (ValueError, TypeError) as error:
                raise ValueError(f"CSV 第 {reader.line_num} 行存在非数值或空值") from error
    return xs, ys


def analyze(config_path):
    config_path = Path(config_path)
    with config_path.open(encoding="utf-8-sig") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError("YAML 顶层必须是配置字典")
    if not isinstance(config.get("input_csv"), str) or not config["input_csv"].strip():
        raise ValueError("配置需要非空字符串 input_csv")
    columns = config.get("columns")
    if not isinstance(columns, dict) or any(
        not isinstance(columns.get(key), str) or not columns[key].strip()
        for key in ("x", "y")
    ):
        raise ValueError("配置需要 columns.x 和 columns.y 两个非空列名")
    csv_path = config_path.parent / config["input_csv"]
    columns = config["columns"]
    xs, ys = read_columns(csv_path, columns["x"], columns["y"])
    return xs, ys, pearson(xs, ys)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="YAML 配置文件")
    args = parser.parse_args(argv)
    try:
        xs, ys, result = analyze(args.config)
    except (OSError, UnicodeError, ValueError, csv.Error, yaml.YAMLError, ArithmeticError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    print(f"n = {len(xs)}")
    print(f"mean_x = {math.fsum(x / len(xs) for x in xs):.12g}")
    print(f"mean_y = {math.fsum(y / len(ys) for y in ys):.12g}")
    print(f"r = {result:.12g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
