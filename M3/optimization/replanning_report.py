"""Separate transient controller errors, BT action failures and periodic plans."""
import argparse
import json
from pathlib import Path
import re
import statistics
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--out',type=Path,default=ROOT/'M3/optimization/report/replanning_detail.json'); a=p.parse_args()
records=[]
for group in json.loads(a.manifest.read_text()):
    for directory in group['result_dirs']:
        for run in sorted((ROOT/directory).glob('run_*')):
            if not (run/'result.json').exists(): continue
            result=json.loads((run/'result.json').read_text()); plans=json.loads((run/'plans.json').read_text())
            text=(run/'navigation.log').read_text(errors='replace') if (run/'navigation.log').exists() else ''
            failures=[]
            for line in text.splitlines():
                if 'controller_server' not in line: continue
                if not re.search(r'detected collision|failed to make progress|controller patience exceeded',line,re.I): continue
                stamp=re.search(r'\[(\d{10}\.\d+)\]',line)
                if stamp: failures.append((int(float(stamp[1])*1e9),line))
            first=failures[0] if failures else None
            next_plan=next((plan for plan in plans if first and plan.get('wall_ns',0)>=first[0]),None)
            records.append(dict(group=group['label'],run=str(run.relative_to(ROOT)),strict_success=result['success'],
                                first_controller_error=first[1] if first else None,controller_error_count=len(failures),
                                next_valid_plan_after_controller_error_wall_s=(next_plan['wall_ns']-first[0])/1e9 if next_plan else None,
                                bt_followpath_failure_events=result.get('controller_failure_replans',[]),
                                periodic_next_plan_after_injection_sim_s=result['first_plan_after_injection_delay_s']))
delays=[r['next_valid_plan_after_controller_error_wall_s'] for r in records if r['next_valid_plan_after_controller_error_wall_s'] is not None]
summary=dict(runs=len(records),runs_with_controller_error=sum(r['first_controller_error'] is not None for r in records),
             runs_with_later_valid_plan=len(delays),wall_delay_median_s=statistics.median(delays) if delays else None,
             wall_delay_min_s=min(delays,default=None),wall_delay_max_s=max(delays,default=None),
             method='Earliest collision/progress/patience log from controller_server -> next /plan receipt wall_ns. BT failures retain separate received simulation-time pairs. Periodic injection latency is not a recovery metric.')
a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(dict(summary=summary,runs=records),indent=2)); print(json.dumps(summary))
