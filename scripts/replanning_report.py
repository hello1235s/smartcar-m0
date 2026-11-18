import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]; rows=[]
manifest=json.loads((ROOT/'M3/M3-4/results/20261116_222952/manifest.json').read_text()); allowed={Path(p).name for item in manifest for p in item['result_dirs']}
for directory in (ROOT/'M3/M3-3/results').iterdir():
    if directory.name not in allowed and 'boundary' not in directory.name: continue
    for run in directory.glob('run_*'):
        if not (run/'plans.json').exists(): continue
        plans=json.loads((run/'plans.json').read_text()); log=(run/'navigation.log').read_text(errors='replace')
        failures=[]
        for line in log.splitlines():
            if re.search(r'failed to make progress|detected collision|failed to create plan|failed to compute path',line,re.I):
                stamp=re.search(r'\[(\d{10}\.\d+)\]',line)
                if stamp: failures.append((int(float(stamp[1])*1e9),line))
        if failures:
            first,line=failures[0]; next_plan=next((p for p in plans if p.get('wall_ns',0)>=first),None)
            rows.append(dict(run=str(run.relative_to(ROOT)),first_failure_wall_ns=first,error=line,next_plan_wall_ns=next_plan['wall_ns'] if next_plan else None,replanning_delay_s=(next_plan['wall_ns']-first)/1e9 if next_plan else None))
out=ROOT/'M3/M3-4/results/replanning_after_failure.json'; out.write_text(json.dumps(rows,indent=2)); print(json.dumps(dict(observed_failure_runs=len(rows),with_later_valid_plan=sum(r['replanning_delay_s'] is not None for r in rows),delays_s=[r['replanning_delay_s'] for r in rows if r['replanning_delay_s'] is not None]),indent=2))
