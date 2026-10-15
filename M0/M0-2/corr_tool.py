#!/usr/bin/env python3
"""从 YAML 配置读取两列 CSV 数据，计算 Pearson 相关系数。"""

import argparse
import csv
import math
from pathlib import Path

import yaml


def pearson(xs, ys):
    """手写中心化公式，以 hypot 避免平方和乘积溢出。"""
    n = len(xs)
    mean_x = math.fsum(x / n for x in xs)
    mean_y = math.fsum(y / n for y in ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    scale_x, scale_y = math.hypot(*dx), math.hypot(*dy)
    return max(-1.0, min(1.0, math.fsum(
        (a / scale_x) * (b / scale_y) for a, b in zip(dx, dy)
    )))


def read_columns(path, x_column, y_column):
    xs, ys = [], []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            xs.append(float(row[x_column]))
            ys.append(float(row[y_column]))
    return xs, ys


def analyze(config_path):
    config_path = Path(config_path)
    with config_path.open(encoding="utf-8-sig") as stream:
        config = yaml.safe_load(stream)
    csv_path = config_path.parent / config["input_csv"]
    columns = config["columns"]
    xs, ys = read_columns(csv_path, columns["x"], columns["y"])
    return xs, ys, pearson(xs, ys)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="YAML 配置文件")
    args = parser.parse_args(argv)
    xs, ys, result = analyze(args.config)
    print(f"n = {len(xs)}")
    print(f"mean_x = {sum(xs) / len(xs):.12g}")
    print(f"mean_y = {sum(ys) / len(ys):.12g}")
    print(f"r = {result:.12g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
