"""Index observed failure evidence without inferring an unmeasured root cause."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--main', type=Path, required=True)
parser.add_argument('--extended', type=Path, required=True)
args = parser.parse_args()
records = []
for manifest in [args.main, args.extended]:
    for group in json.loads(manifest.read_text()):
        for folder in group['result_dirs']:
            for path in sorted((ROOT / folder).glob('run_*/result.json')):
                result = json.loads(path.read_text())
                if result['success']:
                    continue
                lines = (path.parent / 'navigation.log').read_text(errors='replace').splitlines()
                predicates = {
                    'feasible_arc_collision_warning': lambda s: 'controller_server' in s and 'detected collision' in s.lower(),
                    'planner_start_in_lethal_space': lambda s: 'Starting point in lethal space' in s,
                    'planner_goal_occupied': lambda s: bool(re.search(r'goal.*(?:occupied|lethal)', s, re.I)),
                    'tf_or_transform_warning': lambda s: bool(re.search(r'\[(?:WARN|ERROR)\]', s) and re.search(r'extrapolat|transform.*(?:fail|timeout)|TF.*(?:fail|timeout)', s, re.I)),
                    'goal_failed': lambda s: 'bt_navigator' in s and 'Goal failed' in s,
                }
                observations = {}
                for name, predicate in predicates.items():
                    matches = [line for line in lines if predicate(line)]
                    observations[name] = dict(count=len(matches), first=matches[0] if matches else None)
                runtime = json.loads((path.parent / 'native_runtime.json').read_text())
                records.append(dict(group=group['label'], source=str(path.parent.relative_to(ROOT)),
                    action_status=result['status'], action_success=result['action_success'], accepted=result['goal_accepted'],
                    qualification_failures=result['qualification_failures'],
                    world_endpoint=result['endpoint_error_world_truth'], estimated_endpoint=result['endpoint_error_map_estimate'],
                    final_measured_speed=result['final_measured_speed'],
                    minimum_clearance_m=result['minimum_geometric_clearance_m'],
                    overlap_samples=result['geometric_overlap_samples'],
                    fixed_tf2_runtime_verified=runtime['status']=='PASS', observations=observations))

out = ROOT / 'M3/optimization/report'
(out / 'failure_cases.json').write_text(json.dumps(dict(cases=records,
    method='Observable log patterns and measured outcomes only; counts are repeated messages, not independent failures. Missing TF warnings do not prove that all TF timing was ideal.'), indent=2))
markdown = ['# 最终批次失败逐例证据', '',
    '这里只索引最终主对照和额外场景中的全部未到达记录；历史候选另在experiment_audit.json。日志计数是重复消息数，不是独立故障次数。模式匹配只描述观察，不替代根因证明。', '']
for row in records:
    relative = '../' + Path(row['source']).relative_to('M3/optimization').as_posix()
    markdown += [f"## {row['group']} / {Path(row['source']).name}", '',
        f"[原始结果]({relative}/result.json) · [导航日志]({relative}/navigation.log) · [原生TF2加载]({relative}/native_runtime.json)", '',
        f"Action状态{row['action_status']}；未通过项：{', '.join(row['qualification_failures'])}。真值终点误差：位置{row['world_endpoint']['position_m']:.4f}m、朝向{row['world_endpoint']['yaw_rad']:.4f}rad。最终实测速度{row['final_measured_speed']}；最小几何间距{row['minimum_clearance_m']:.4f}m，重叠采样{row['overlap_samples']}；修复TF2实际加载核验{row['fixed_tf2_runtime_verified']}。", '']
    if row['action_success']:
        markdown += [f"Action虽然成功，独立物理验收仍失败。停车后地图估计终点误差为{row['estimated_endpoint']['position_m']:.4f}m；它与世界真值是不同数据源，不能用估计合格替代真值合格，也不能为跨过门槛而四舍五入。", '']
    for name, observation in row['observations'].items():
        if observation['count']:
            markdown += [f"- `{name}`：{observation['count']}条；首条原文：`{observation['first']}`"]
    markdown += ['', 'Action未到达仍计入成功率分母。目标被箱体覆盖属于预期不可达，需另核对停车与间距，不能计作避障到达。', '']
(out / 'failure_cases.md').write_text('\n'.join(markdown) + '\n')
print('FAILURE_CASES_INDEXED', len(records))
