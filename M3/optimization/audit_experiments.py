"""Index every navigation candidate, including rejected and unaccepted attempts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--extended',type=Path); a=p.parse_args()
selected=set()
for file in [a.manifest,a.extended]:
    if file:
        selected.update(directory for group in json.loads(file.read_text()) for directory in group['result_dirs'])
rows=[]
for file in sorted((ROOT/'M3/optimization/results').glob('*/experiment.json')):
    metadata=json.loads(file.read_text()); results=[json.loads(path.read_text()) for path in file.parent.glob('run_*/result.json')]
    config=yaml.safe_load((file.parent/'parameters_used.yaml').read_text())
    control=config['controller_server']['ros__parameters']; checker=control['general_goal_checker']
    complete=len(results)==metadata['runs_requested']; accepted=sum(r.get('goal_accepted',False) for r in results)
    rows.append(dict(directory=str(file.parent.relative_to(ROOT)),selected_for_final_comparison=str(file.parent.relative_to(ROOT)) in selected,
        label=metadata['label'],requested=metadata['runs_requested'],recorded=len(results),accepted=accepted,successes=sum(r['success'] for r in results),
        status='complete' if complete and accepted==len(results) else 'infrastructure_or_incomplete',
        failures=dict(Counter(reason for result in results for reason in result.get('qualification_failures',[result.get('failure_reason','unclassified')]))),
        internal_xy_tolerance=checker['xy_goal_tolerance'],internal_yaw_tolerance=checker['yaw_goal_tolerance'],controller=control['FollowPath']['plugin'],
        code_head=metadata['code_head'],params_sha256=metadata['params_sha256'],map_sha256=metadata['map_sha256'],map_yaml_sha256=metadata.get('map_yaml_sha256'),
        rmw_implementation=metadata.get('rmw_implementation','rmw_fastrtps_cpp'),dds_transport=metadata.get('dds_transport'),
        candidate_decision=str(file.parent/'candidate_decision.json') if (file.parent/'candidate_decision.json').exists() else None))
out=ROOT/'M3/optimization/report/experiment_audit.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(dict(experiments=rows,notes=[
    'All retained attempts are indexed. Different candidates, tolerances and infrastructure failures are not pooled into one success rate.',
    'The standard-RPP nominal candidate with internal .08m/.15rad completed 9/10 but was not adopted because one terminal maneuver overlapped the conservative envelope.',
    'The first split-controller comparison exposed plugin factory initialization failure, not evidence of navigation quality. Raw files remain retained.',
    'Pre-correction map YAML used free_thresh .25, reloading gray205 as free. Actual native-loader checks prove the issue and correction. Those results are not pooled with final post-roundtrip-validated runs.']),indent=2))
print('EXPERIMENT_AUDIT',len(rows),'navigation experiment folders')
