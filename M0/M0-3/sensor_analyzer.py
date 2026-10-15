#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sensor_analyzer.py  —— 上一届学长留下的"能用"的脚本

注释（学长原话）：
    "处理一下传感器数据就能用"

原本意图：
    1. 读取 sensor_data.csv（列：time, value）
    2. 计算 value 的平均值、标准差
    3. 剔除离群值（|value - mean| > 2 * std）
    4. 把清洗后的数据保存为 cleaned_data.csv
    5. 打印一份统计摘要

现状：跑不通 / 跑出来数不对。就交给你了。
"""

import argparse
import csv
import math
import sys
from pathlib import Path


def read_records(path):
    """保留时间与数值的对应关系，并在计算之前检查整个输入。"""
    records = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not reader.fieldnames or not {"time", "value"}.issubset(reader.fieldnames):
            raise ValueError("CSV 必须包含 time 和 value 列")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV 表头存在重复列名")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"第 {reader.line_num} 行的列数与表头不一致")
            try:
                time_value, value = float(row["time"]), float(row["value"])
            except (ValueError, TypeError) as error:
                raise ValueError(f"第 {reader.line_num} 行包含非数值或空值") from error
            if not math.isfinite(time_value) or not math.isfinite(value):
                raise ValueError(f"第 {reader.line_num} 行包含 NaN 或 Infinity")
            records.append((time_value, value))
    if not records:
        raise ValueError("CSV 没有数据行，无法计算统计量")
    return records


def clean_records(records):
    """以原始全集计算总体标准差，仅执行一次双侧 2σ 筛选。"""
    if not records:
        raise ValueError("不能分析空数据集")
    count = len(records)
    mean = math.fsum(value / count for _, value in records)
    std = math.hypot(*(value - mean for _, value in records)) / math.sqrt(count)
    if not math.isfinite(mean) or not math.isfinite(std):
        raise ValueError("数据数值范围过大，无法可靠计算")
    cleaned = [(t, value) for t, value in records if abs(value - mean) <= 2 * std]
    return mean, std, cleaned


def analyze(input_path, output_path):
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("输入输出路径不能相同，以免覆盖原始数据")
    records = read_records(input_path)
    mean, std, cleaned = clean_records(records)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", "value"])
        writer.writerows(cleaned)
    return len(records), mean, std, cleaned


def main(argv=None):
    parser = argparse.ArgumentParser(description="传感器 CSV 双侧 2σ 离群值清洗")
    parser.add_argument("--input", default="sensor_data.csv")
    parser.add_argument("--output", default="cleaned_data.csv")
    args = parser.parse_args(argv)
    try:
        count, mean, std, cleaned = analyze(args.input, args.output)
    except (OSError, UnicodeError, ValueError, csv.Error, ArithmeticError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    print("=== 传感器数据分析 ===")
    print(f"共读取 {count} 条数据")
    print(f"均值 mean = {mean:.12g}")
    print(f"标准差 std = {std:.12g}")
    print(f"清洗后剩余 {len(cleaned)} 条；剔除 {count - len(cleaned)} 条")
    print(f"已保存到 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
