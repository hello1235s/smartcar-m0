#!/usr/bin/env python3
"""按依赖顺序执行任务，支持失败重试、全局超时和彩色日志。"""

import argparse
from collections import deque
from dataclasses import dataclass
import json
import math
import random
from pathlib import Path
import sys
import time

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


class ConsoleLogger:
    COLORS = {"SUCCESS": 32, "FAILED": 31, "RETRY": 33, "SKIPPED": 34, "TIMEOUT": 31}

    def __init__(self, color="auto"):
        self.color = color == "always" or (color == "auto" and sys.stdout.isatty())

    def __call__(self, status, message):
        label = f"[{status}]"
        if self.color:
            label = f"\033[{self.COLORS[status]}m{label}\033[0m"
        print(f"{label} {message}", flush=True)


class TaskScheduler:
    def __init__(self, tasks, timeout=15, seed=None, *, clock=None, sleep=None,
                 wall_clock=None, rng=None, logger=None):
        self.tasks = tasks
        self.order = topological_order(tasks)
        self.timeout = number(timeout, "timeout", positive=True)
        self.seed = seed
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self.wall_clock = wall_clock or time.time
        self.rng = rng or random.Random(seed)
        self.log = logger or ConsoleLogger()

    def run(self):
        started = self.clock()
        deadline = started + self.timeout
        rows = {task.name: {"name": task.name, "status": "SKIPPED", "attempts": 0,
                "duration": 0.0, "started_at": None, "ended_at": None,
                "reason": "尚未执行"} for task in self.tasks}
        completed = set()
        execution_order = []
        timed_out = False

        def stop_remaining():
            nonlocal timed_out
            timed_out = True
            for row in rows.values():
                if row["name"] not in completed:
                    row.update(status="TIMEOUT", reason="全局超时")
                    if row["started_at"] is not None:
                        row["ended_at"] = self.wall_clock()
            self.log("TIMEOUT", f"达到全局时限 {self.timeout:g} 秒，终止剩余任务")

        for task in self.order:
            if self.clock() >= deadline:
                stop_remaining()
                break
            row = rows[task.name]
            blocked = [name for name in task.dependencies if rows[name]["status"] != "SUCCESS"]
            if blocked:
                row["reason"] = "前置任务未成功：" + ", ".join(blocked)
                completed.add(task.name)
                self.log("SKIPPED", f"{task.name}: {row['reason']}")
                continue
            execution_order.append(task.name)
            for attempt in range(1, 4):
                remaining = deadline - self.clock()
                if remaining <= 0:
                    stop_remaining()
                    break
                row["attempts"] = attempt
                if row["started_at"] is None:
                    row["started_at"] = self.wall_clock()
                attempt_start = self.clock()
                # sleep 最多只等待剩余预算，长任务也能在全局截止时中断。
                self.sleep(min(task.duration, remaining))
                row["duration"] += max(0.0, self.clock() - attempt_start)
                if self.clock() >= deadline:
                    stop_remaining()
                    break
                if self.rng.random() < task.success_rate:
                    row.update(status="SUCCESS", reason="执行成功", ended_at=self.wall_clock())
                    self.log("SUCCESS", f"{task.name} 第 {attempt} 次尝试成功")
                    completed.add(task.name)
                    break
                self.log("FAILED", f"{task.name} 第 {attempt} 次尝试失败")
                if attempt < 3:
                    self.log("RETRY", f"{task.name} 准备第 {attempt + 1} 次尝试")
                else:
                    row.update(status="SKIPPED", reason="首次执行及两次重试均失败",
                               ended_at=self.wall_clock())
                    completed.add(task.name)
                    self.log("SKIPPED", f"{task.name}: 重试耗尽")
            if timed_out:
                break
        return {"timeout": timed_out, "total_duration": max(0.0, self.clock() - started),
                "timeout_seconds": self.timeout, "seed": self.seed,
                "execution_order": execution_order, "tasks": list(rows.values())}


def write_report(path, report):
    path = Path(path)
    with path.open("w", encoding="utf-8") as stream:
        if path.suffix.lower() in {".yaml", ".yml"}:
            yaml.safe_dump(report, stream, allow_unicode=True, sort_keys=False)
        else:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--timeout", type=float, help="覆盖配置中的全局超时秒数")
    parser.add_argument("--report", default="report.json", help=".json / .yaml / .yml")
    parser.add_argument("--seed", type=int, help="固定随机种子，便于复现")
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    args = parser.parse_args(argv)
    try:
        tasks, config_timeout = load_config(args.config)
        report_path = Path(args.report)
        if report_path.resolve() == Path(args.config).resolve():
            raise ValueError("报告路径不能与输入配置相同")
        if report_path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            raise ValueError("报告必须使用 .json、.yaml 或 .yml 扩展名")
        if not report_path.parent.is_dir():
            raise ValueError("报告输出目录不存在")
        timeout = args.timeout if args.timeout is not None else config_timeout
        report = TaskScheduler(tasks, timeout, args.seed, logger=ConsoleLogger(args.color)).run()
        write_report(report_path, report)
        print(f"报告已保存到 {report_path}", flush=True)
        if report["timeout"]:
            return 124
        return 0 if all(task["status"] == "SUCCESS" for task in report["tasks"]) else 1
    except (OSError, UnicodeError, ValueError, yaml.YAMLError, ArithmeticError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
