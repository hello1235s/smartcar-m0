import csv
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'M5/common'),str(ROOT/'M5/M5-4')]
from audit import verify
from quick_review import review,render
def read(path): return json.loads((ROOT/path).read_text())

graph_dir=ROOT/'M3/M3-2/results/replay_20261116_225310'
lines=(graph_dir/'graph_analysis.txt').read_text().splitlines(); graph=json.loads(next(x.split('POSEGRAPH_JSON ',1)[1] for x in lines if x.startswith('POSEGRAPH_JSON ')))
(graph_dir/'graph_analysis.json').write_text(json.dumps(graph,indent=2))
quality=read('M3/M3-2/results/quality/quality.json'); comparisons=read('M3/M3-4/results/matched_comparison/summary.json'); replans=read('M3/M3-4/results/replanning_after_failure.json')
delays=[r['replanning_delay_s'] for r in replans if r['replanning_delay_s'] is not None]
report=['# M3-4 实测分析','','|配置|成功/10|成功率|成功耗时(s,仿真时钟)|规划绕行估计(m)|转向变化(rad/m)|','|---|---:|---:|---:|---:|---:|']
for r in comparisons: report.append('|%s|%d|%.0f%%|%.3f|%.3f|%.3f|'%(r['planner'],r['successes'],100*r['success_rate'],r['seconds'],r['extra_length_m'],r['steering_variation_rad_per_m']))
report+=['','## ① 综合选择','安全优先选择A：8/10成功，代价是约40秒。B更快但只3/10成功且转向变化更大。B调优后7/10成功，比B增加40个百分点，成功耗时约29秒，保留速度与稳定性的折中。样本每组10次，不把点估计当作任意随机障碍下的成功保证。','','## ② 实测失效边界','实体0.8m障碍在目标世界(11,5)生成，目标被覆盖，测试Action aborted，约42.2秒，相关运行包含boundary_goal_blocked。激进B在无障碍参考中也可能失败，说明短前视和高速度本身已不稳，不能把所有失败都归因于箱子。','','## ③ 失败后是否重规划','记录controller/planner错误的墙钟时间，与实际/plan接收墙钟逐一对齐。%d个失败运行中，%d个随后有有效新plan；其延迟中位数%s秒、范围%s秒。没有有效新plan的记录为null，尤其目标占据无法靠重规划变成可达。注入到下一plan是另一个字段，不能混用。'%(len(replans),len(delays),round(statistics.median(delays),3) if delays else '未测得',[round(min(delays),3),round(max(delays),3)] if delays else '未测得'),'','## ④ 比赛参数','本场景为1m窄门和2m走廊。稳定优先用A：0.28m/s、0.7m前视、2s预测；限时较紧时可用B_tuned：0.45m/s、0.5m前视、1.5s预测，须接受本次7/10的结果。未测更窄门、更快移动障碍，不扩展结论。','','## 数据口径','绕行主指标采用题面允许的/plan：注入至少3秒后，已行进的规划起点前缀加当前余程，再减各参数配置匹配的无障碍初始plan长度。它是规划距离估计，不能冒充真值里程。另保留odom积分差；B没有成功的无障碍到达样本时该项为null，不把失败半程当基线。原始统一参考的初稿保留，最终以matched_comparison为准。','四阶段截图来自实际ROS map/plan/scan/TF窗口；最终演示按运动开始、真实激光命中障碍区域、绕行和通过位置触发。早期路径外障碍试验不计入30次。原始命令为控制器实际reference，转向变化按atan(0.28*omega/v)积分归一化。']
(ROOT/'M3/M3-4/report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
formal=read('M5/experiments/latest.json'); runs=[]
for name in formal['experiments']: runs+=read('M5/experiments/'+name+'/summary.json')['run_paths']
audits=[]; reviews=[]
for run in map(Path,runs):
    result=review(run); (run/'review.md').write_text(render(result),encoding='utf-8'); reviews.append(result)
    check=verify(run/'audit_log.jsonl'); seal=json.loads((run/'audit_log.seal.json').read_text()); check['seal_matches']=check.get('head')==seal['head']; check['run']=str(run.relative_to(ROOT)); audits.append(check)
assert len(runs)==5 and all(r['result']=='SUCCESS' for r in reviews)
assert all(a['valid'] and a['seal_matches'] for a in audits)
(ROOT/'M5/experiments/audit_validation.json').write_text(json.dumps(audits,indent=2))
resource_file=sorted((ROOT/'evidence/M5-dashboard').glob('*/report.json'))[-1]; resource=json.loads(resource_file.read_text())
pipeline={name:read('M6/M6-4/results/'+name+'/report.json') for name in ['serial','dual','triple']}
fig,ax=plt.subplots(figsize=(9,4))
for name in pipeline:
    rows=list(csv.DictReader((ROOT/'M6/M6-4/results'/name/'rss.csv').open())); origin=float(rows[0]['steady_t']); ax.plot([float(r['steady_t'])-origin for r in rows],[float(r['rss_mb']) for r in rows],label=name)
ax.set(xlabel='Seconds after sampling starts',ylabel='Process RSS (MB)',title='Three measured 180-second VM CPU runs'); ax.legend(); fig.tight_layout(); fig.savefig(ROOT/'M6/M6-4/results/rss_curve.png',dpi=160); plt.close(fig)
summary=dict(created=time.strftime('%Y-%m-%d %H:%M:%S'),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),hardware='VMware Ubuntu 22.04 + actual K230 USB; Orin not arrived',m3_graph=graph,m3_quality=quality,m3_dynamic=comparisons,m5_resources=resource,m5_formal_runs=5,m5_audits_valid=True,m5_review_max_s=max(r['review_seconds'] for r in reviews),m6_cpu=read('M6/M6-1/results/vm_cpu/benchmark.json'),m6_live=read('M6/M6-1/results/live_USB_verified/live_report.json'),m6_quantization=read('M6/M6-2/results/quantization.json'),m6_mnn=read('M6/M6-2/results/mnn_cpu.json'),m6_tuning=read('M6/M6-3/results/tuned.json'),m6_pipeline=pipeline,m6_pipeline_speedup=pipeline['triple']['fps']/pipeline['serial']['fps'],qualification=dict(race_map=None,orin_cpu_gpu_npu=None,cuda_graph_full_chain=None,pipeline_1_6x=False,int8_2x=False))
(ROOT/'evidence/advanced_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)); print('FINAL_REPORTS_READY',len(runs),len(audits),summary['m6_pipeline_speedup'])
