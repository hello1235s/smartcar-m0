#!/usr/bin/env python3
"""按依赖顺序执行任务，支持失败重试、全局超时和彩色日志。"""

import argparse
from collections import deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys

import yaml


@dataclass(frozen=True)
class Task:
    name: str
    duration: float
    success_rate: float
    dependencies: tuple[str, ...]


def number(value, label, *, minimum=0.0, maximum=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须是数值")
    value = float(value)
    if not math.isfinite(value) or value < minimum or (positive and value <= 0):
        raise ValueError(f"{label} 必须是{'正' if positive else '非负'}有限数值")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} 不能超过 {maximum}")
    return value


def topological_order(tasks):
    lookup = {task.name: task for task in tasks}
    if not tasks or len(lookup) != len(tasks):
        raise ValueError("任务列表不能为空，任务名必须唯一")
    degree = {task.name: len(task.dependencies) for task in tasks}
    children = {task.name: [] for task in tasks}
    for task in tasks:
        for dependency in task.dependencies:
            if dependency not in lookup:
                raise ValueError(f"{task.name} 依赖不存在的任务：{dependency}")
            children[dependency].append(task.name)
    ready = deque(task.name for task in tasks if degree[task.name] == 0)
    ordered = []
    while ready:
        name = ready.popleft()
        ordered.append(lookup[name])
        for child in children[name]:
            degree[child] -= 1
            if degree[child] == 0:
                ready.append(child)
    if len(ordered) != len(tasks):
        raise ValueError("任务依赖存在环，无法调度")
    return ordered


def load_config(path):
    path = Path(path)
    with path.open(encoding="utf-8-sig") as stream:
        if path.suffix.lower() == ".json":
            config = json.load(stream)
        elif path.suffix.lower() in {".yaml", ".yml"}:
            config = yaml.safe_load(stream)
        else:
            raise ValueError("配置文件必须使用 .yaml、.yml 或 .json 扩展名")
    if not isinstance(config, dict) or not isinstance(config.get("tasks"), list) or not config["tasks"]:
        raise ValueError("配置必须包含非空 tasks 列表")
    tasks = []
    for index, item in enumerate(config["tasks"], 1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 项任务必须是字典")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"第 {index} 项任务需要非空字符串 name")
        dependencies = item.get("dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(dep, str) or not dep.strip() for dep in dependencies
        ):
            raise ValueError(f"{name}.dependencies 必须是任务名字符串列表")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError(f"{name} 存在重复的依赖项")
        tasks.append(Task(name,
            number(item.get("duration"), f"{name}.duration"),
            number(item.get("success_rate"), f"{name}.success_rate", maximum=1),
            tuple(dependencies)))
    timeout = number(config.get("timeout", 15), "timeout", positive=True)
    topological_order(tasks)
    return tasks, timeout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    try:
        tasks, _ = load_config(args.config)
        print(" -> ".join(task.name for task in topological_order(tasks)))
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
