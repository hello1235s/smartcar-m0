"""Publish standard task entry files after completed and reviewed experiments."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(); p.add_argument('--main',type=Path,required=True); p.add_argument('--extended',type=Path,required=True); p.add_argument('--timed',type=Path,required=True); a=p.parse_args()
a.timed=a.timed.resolve()
a.main=a.main.resolve(); a.extended=a.extended.resolve()
report=ROOT/'M3/optimization/report'
method=json.loads((report/'method.json').read_text())
assert (ROOT/method['manifest']).resolve()==a.main,'Use the analyzed combined manifest, not a different batch'
summary={r['group']:r for r in json.loads((report/'summary.json').read_text())}
records=list(csv.DictReader((report/'all_attempts.csv').open()))
f=lambda v:'N/A' if v is None else f'{v:.4f}'
dynamic=[r for r in records if r['group'].startswith('formal_dynamic_')]
assert len(dynamic)==30
task4=ROOT/'M3/M3-4/results'
with (task4/'benchmark.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(dynamic[0])); writer.writeheader(); writer.writerows(dynamic)
for name in ['metrics.png','trajectories.png']:
    shutil.copy2(report/name,task4/name)
selected=None
for row in dynamic:
    if row['profile']!='B_tuned' or row['success']!='True': continue
    directory=ROOT/row['result_dir']; screenshots=directory/'screenshots'
    if all((screenshots/('actual_view_%d.png'%i)).exists() for i in range(1,5)) and (screenshots/'actual_costmaps_obstacle.png').exists():
        selected=directory; break
if selected is None: raise RuntimeError('Complete actual navigation and costmap screenshots are required')
sequence=task4/'process_sequence'; sequence.mkdir(exist_ok=True)
for file in (selected/'screenshots').glob('*.png'): shutil.copy2(file,sequence/file.name)
source=dict(source_run=str(selected.relative_to(ROOT)),native_ros_images=True,
            hashes={file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in (selected/'screenshots').glob('*.png')})
(sequence/'source_manifest.json').write_text(json.dumps(source,indent=2))
task3=ROOT/'M3/M3-3/results'; current=task3/'current_nav'; current.mkdir(exist_ok=True)
for name in ['costmaps.png','commands.png']: shutil.copy2(report/name,current/name)
shutil.copy2(selected/'screenshots/actual_costmaps_obstacle.png',current/'actual_costmaps_window.png')
(current/'source_manifest.json').write_text(json.dumps(source,indent=2))
lines=['# 本轮默认静态十次：全部成败','', '|次序|严格通过|仿真秒|真值位置m|真值朝向rad|失败原因|','|---|---|---:|---:|---:|---|']
for row in records:
    if row['group']!='formal_static_B_tuned': continue
    lines.append('|%s|%s|%s|%s|%s|%s|'%(row['run'],row['success'],row['seconds'],row['position_error_m'],row['yaw_error_rad'],row['failure'] or '无'))
lines+=['','真实终点要求≤0.15m且≤0.20rad；内部目标容差0.05m/0.10rad。完整来源和哈希见`../../optimization/report/all_attempts.csv`。历史试验留在原日期目录，不覆盖。']
(task3/'runs.md').write_text('\n'.join(lines)+'\n')
stages=['# 同一AckermannRPP内核的分步调优','', '|阶段|修改|样本/成功|成功耗时s|转向TV rad/m|额外距离m|','|---|---|---:|---:|---:|---:|']
for label,key,change in [('B','formal_dynamic_B','激进：0.65m/s、固定0.25m前视、0.5s预测'),('B_speed','tuning_speed_only','只把巡航速度0.65降到0.32'),('B_lookahead','tuning_lookahead','保持0.32和0.5s预测；只将前视策略改为速度相关0.30～0.65m'),('B_tuned','formal_dynamic_B_tuned','保持速度和前视策略；只将预测0.5→2.0s')]:
    s=summary[key]; stages.append(f"|{label}|{change}|{s['attempts']}/{s['successes']}|{f(s['mean_seconds'])}|{f(s['mean_steering_variation_rad_per_m'])}|{f(s['mean_extra_length_m'])}|")
stages+=['','全部正式组共用相同运动内核、地图与YAML哈希、目标、footprint和验收器。B_speed为3次诊断，没有独立无障碍参考时不计算绕行均值；最终B与B_tuned各10次并有同配置参考。标准RPP及修正地图语义前的候选只作根因证据，不混入本表。','', '控制器改造先于参数对照：曲率在碰撞预测前受限，末端用虚拟朝向参考，真实目标未更换。源代码/参数快照/失败审计见`../../optimization/report/`。']
stages+=['','本表按参数差异链排序，不按采集时间排序；主组按预先固定计划采集，中间组用于补充消融归因，不冒称每轮看成绩后才在线决定下一参数。两个中间组各3次，未做显著性结论；每一步是否有可检测收益应读实际数字，不能只因改了参数就宣称改善。']
(task4/'tuning_log.md').write_text('\n'.join(stages)+'\n')
(task3/'tuning_log.md').write_text('\n'.join(stages)+'\n\n本表使用同一导航内核的实际动态诊断，避免把同时更换控制器与参数当成单参数收益。安装版Humble默认值→当前值→理由的完整101项记录见../config/changes.yaml；默认DWB方案不适用于该阿克曼车，不能捏造其同条件成功率。\n')
boundaries=[]; boundary_lines=['# 额外场景与失败边界','', '|场景|到达/次数|Action状态|最后线速度m/s|几何重叠采样|','|---|---:|---|---|---:|']
for group in json.loads(a.extended.read_text()):
    results=[]
    for directory in group['result_dirs']:
        for file in sorted((ROOT/directory).glob('run_*/result.json')):
            result=json.loads(file.read_text()); results.append(result)
            if group['label']=='boundary_blocked_goal':
                speed=(result.get('final_measured_speed') or [None])[0]
                valid=result['goal_accepted'] and not result['action_success'] and result['obstacle']['success'] and speed is not None and abs(speed)<.02 and result['geometric_overlap_samples']==0
                boundaries.append(dict(source=str(file.parent.relative_to(ROOT)),expected_unreachable=True,safe_rejection=valid,status=result['status'],speed_mps=speed,clearance_m=result['minimum_geometric_clearance_m']))
    boundary_lines.append('|%s|%s/%s|%s|%s|%s|'%(group['label'],sum(r['success'] for r in results),len(results),','.join(str(r['status']) for r in results),','.join(f((r.get('final_measured_speed') or [None])[0]) for r in results),sum(r['geometric_overlap_samples'] for r in results)))
boundary_lines+=['','目标被0.8m实体箱覆盖时预期不可达，不能把正确退出当作到达成功。近前方突发箱测试局部阻挡、重规划与停车；其结果单独报告，不能从单次推断“所有近障都必失败”。原始位置/目标/尺寸/时机见每组快照。']
(task4/'failure_boundary.md').write_text('\n'.join(boundary_lines)+'\n')
(report/'boundary_validation.json').write_text(json.dumps(boundaries,indent=2))
if not boundaries or not all(r['safe_rejection'] for r in boundaries): raise RuntimeError('Blocked-goal safe rejection needs review')
# Matched-speed control ablation: same rear reference and same nominal speeds.
feedback=next((ROOT/'M3/optimization/results').glob('*qualified_feedback_rear'))
stats=[]
for label,directory in [('Timed .28/.18',a.timed),('Feedback .28/.18',feedback)]:
    rows=json.loads((directory/'logs/runs.json').read_text()); assert len(rows)==10
    entry=dict(label=label,source=str(directory.relative_to(ROOT)),n=10)
    for key in ['truth_position_error_m','truth_angle_error_deg','sim_seconds']:
        if key=='sim_seconds':
            values=[]
            for row in rows:
                samples=list(csv.DictReader((directory/'logs'/('run_%02d_truth.csv'%row['lap'])).open()))
                values.append(float(samples[-1]['t'])-float(samples[0]['t']))
        else: values=[r[key] for r in rows]
        entry[key]=dict(mean=statistics.mean(values),sample_std=statistics.stdev(values))
    stats.append(entry)
(report/'square_matched_speed.json').write_text(json.dumps(stats,indent=2))
fig,axes=plt.subplots(1,3,figsize=(12,4))
for ax,key,title in zip(axes,['truth_position_error_m','truth_angle_error_deg','sim_seconds'],['Truth closure (m)','Truth heading closure (deg)','Duration (sim s)']):
    ax.bar([s['label'] for s in stats],[s[key]['mean'] for s in stats],yerr=[s[key]['sample_std'] for s in stats],capsize=5,color=['#c9664a','#237b86']); ax.set_title(title); ax.tick_params(axis='x',labelrotation=10); ax.grid(axis='y',alpha=.2)
fig.suptitle('Matched-speed actual Gazebo repeats: n=10 per mode, mean and sample SD'); fig.tight_layout(); fig.savefig(report/'square_matched_speed.png',dpi=170); plt.close(fig)
improvement=100*(1-stats[1]['truth_position_error_m']['mean']/stats[0]['truth_position_error_m']['mean'])
addition='\n## 同速十次重复消融\n\n定时与odom反馈均用后轴参考、0.28/0.18m/s和同一2m圆角轨迹，各10次。定时真值闭合 %.6f±%.6fm，反馈 %.6f±%.6fm，均为均值±样本标准差；本样本位置均值降低约%.1f%%。两批噪声时序不同，不冒充成对显著性检验。时间代价与角度见square_matched_speed.json/图。\n'%(stats[0]['truth_position_error_m']['mean'],stats[0]['truth_position_error_m']['sample_std'],stats[1]['truth_position_error_m']['mean'],stats[1]['truth_position_error_m']['sample_std'],improvement)
overview=ROOT/'M3/optimization/REPORT.md'; text=overview.read_text(); text=text.split('\n## 同速十次重复消融')[0]+addition; overview.write_text(text)
replanning=json.loads((report/'replanning_detail.json').read_text())
extra_replanning=json.loads((ROOT/'M3/optimization/extended_report/replanning_detail.json').read_text())
(task4/'replanning_summary.json').write_text(json.dumps(dict(main=replanning['summary'],extended=extra_replanning['summary']),indent=2))
# Put measured numbers directly into the four required oral/report answers.
answers=['\n## 四问的实测补充','']
for name in ['A','B','B_tuned']:
    s=summary['formal_dynamic_'+name]
    answers.append(f"- ① {name}：严格{s['successes']}/{s['attempts']}，成功耗时{f(s['mean_seconds'])}s、额外路径{f(s['mean_extra_length_m'])}m、指令转向TV {f(s['mean_steering_variation_rad_per_m'])}rad/m。采用同一验收器，成功样本均值和失败分母分开。")
for boundary in boundaries:
    answers.append(f"- ② 目标世界(11,5)在出发3s后被0.8m实体箱覆盖：Action状态{boundary['status']}，末速度{f(boundary['speed_mps'])}m/s，最小包络间距{f(boundary['clearance_m'])}m，安全退出检查{boundary['safe_rejection']}。这是目标占据的不可达边界，不推断其他坐标必败。")
for name,detail in [('主对照',replanning),('额外场景',extra_replanning)]:
    s=detail['summary']
    answers.append(f"- ③ {name}：{s['runs_with_controller_error']}/{s['runs']}次出现局部控制碰撞/进度/耐心错误；{s['runs_with_later_valid_plan']}次随后收到有效plan。错误日志墙钟→下条plan接收墙钟中位延迟{f(s['wall_delay_median_s'])}s，范围{f(s['wall_delay_min_s'])}～{f(s['wall_delay_max_s'])}s。空值表示没有可配对事件，不能填成0秒。")
s=summary['formal_dynamic_B_tuned']
answers.append(f"- ④ 当前约2m走廊、0.95m窄门、0.6m临时静止方盒场景，默认选0.32m/s、速度相关0.30～0.65m前视和2s预测；该组动态严格{s['successes']}/10，成功耗时{f(s['mean_seconds'])}s。该选择是对当前速度、平滑度和成功率的折中，额外位置/目标另列，不是任意场景最优证明。")
answers+=['','逐次依据：`../optimization/report/all_attempts.csv`、`../optimization/report/replanning_detail.json`、`../optimization/extended_report/`。日志配对不是ROS仿真时钟延迟；BT FAILURE→plan仿真时间另在同JSON逐条保留。','']
analysis=ROOT/'M3/M3-4/report.md'
analysis.write_text(analysis.read_text().split('\n## 四问的实测补充')[0]+'\n'.join(answers))
print('STANDARD_TASK_ENTRIES_READY',json.dumps(dict(dynamic_rows=len(dynamic),source_sequence=str(selected.relative_to(ROOT)),matched_position_improvement_percent=improvement,boundary=boundaries)))
