"""Re-run all four M1 tasks and retain every command, result and measurement."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--short-seconds',type=float,default=24);p.add_argument('--long-seconds',type=float,default=60);a=p.parse_args()
out=(a.out or ROOT/'evidence/M1-acceptance-v2'/time.strftime('%Y%m%d_%H%M%S')).resolve();out.mkdir(parents=True,exist_ok=False)
python=str(ROOT/'.venv-ros/bin/python')
env=dict(os.environ,RMW_IMPLEMENTATION='rmw_fastrtps_cpp')
env.pop('CYCLONEDDS_URI',None)
for name in ['LD_LIBRARY_PATH','AMENT_PREFIX_PATH']:
    env[name]=':'.join(value for value in env.get(name,'').split(':') if value and '/vendor/m3-dds/' not in value)
for path in Path('/proc').iterdir():
    if not path.name.isdigit():continue
    try:
        if (path/'comm').read_text().strip()!='Xwayland':continue
        command=(path/'cmdline').read_bytes().decode().split('\0')
        if '-auth' in command:env['XAUTHORITY']=command[command.index('-auth')+1];break
    except (FileNotFoundError,PermissionError,ProcessLookupError):pass
report=dict(status='running',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    rmw_implementation=env['RMW_IMPLEMENTATION'],steps=[],tasks={},limits='Task-defined tests in this VM and measurement windows, not a proof of zero defects under all inputs or loads.')
def save():(out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
def run(name,arguments):
    print('M1_STEP_START',name,flush=True);save()
    with (out/(name+'.log')).open('w') as log:result=subprocess.run(arguments,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    report['steps'].append(dict(name=name,command=arguments,returncode=result.returncode));save()
    assert result.returncode==0,name
    print('M1_STEP_DONE',name,flush=True)
def new_result(base,before):
    created=set(base.iterdir())-before;assert len(created)==1,created
    return next(iter(created))
try:
    run('message_filter_timeout_contracts',[python,'scripts/verify_m1_contracts_v2.py','--out',str(out/'contracts')])
    run('three_nodes_namespaces_readiness',[python,'scripts/verify_m1_chain.py'])
    chain=json.loads((ROOT/'evidence/M1-chain/latest.json').read_text());assert chain['result']=='PASS'
    report['tasks']['M1-1']=dict(status='PASS',source=str((out/'contracts/results.json').relative_to(ROOT)),sensor_hz=chain['sensor_hz'],processed_hz=chain['processed_hz'])
    report['tasks']['M1-2']=dict(status='PASS',namespaced_nodes=chain['namespaced_nodes'],thresholds=chain['thresholds'],missing_yaml_error=chain['missing_yaml_human_error'],isolated_alpha=chain['isolated_alpha'],topic_endpoints_namespace_isolated=chain['topic_endpoints_namespace_isolated'])
    # Confirm the actual readiness probe finished before node C was launched.
    chain_directory=max((ROOT/'evidence/M1-chain').glob('*/results.json'),key=lambda path:path.stat().st_mtime).parent
    for robot in ['robot1','robot2']:
        lines=(chain_directory/(robot+'.log')).read_text().splitlines()
        ready=next(i for i,line in enumerate(lines) if 'FILTER_READY' in line)
        alarm=next(i for i,line in enumerate(lines) if 'node_c_alarm-' in line and 'process started' in line)
        assert ready<alarm,(robot,ready,alarm)
    report['tasks']['M1-2']['readiness_before_alarm_verified']=True
    projection_base=ROOT/'M1/M1-3/results';before=set(projection_base.iterdir())
    run('projection_two_calibrations_clock_video',[python,'scripts/verify_projection.py'])
    projection=new_result(projection_base,before)
    run('projection_bag_pixel_and_tf_oracle',[python,'scripts/verify_m1_projection_oracle_v2.py','--directory',str(projection)])
    projection_report=json.loads((projection/'results.json').read_text());assert projection_report['result']=='PASS'
    report['tasks']['M1-3']=dict(status='PASS',source=str(projection.relative_to(ROOT)),measurements=projection_report,
        exact_pixel_oracle=str((projection/'pixel_oracle.json').relative_to(ROOT)))
    run('image_pixels_headers_all_gray_levels',[python,'M1/M1-4/semantic_check.py'])
    semantic=json.loads((ROOT/'M1/M1-4/results/semantic_check.json').read_text());assert len(semantic['cases'])==5
    performance_base=ROOT/'M1/M1-4/results';before=set(performance_base.iterdir())
    run('performance_four_way_comparison',[python,'M1/M1-4/measure_chain.py','--seconds',str(a.short_seconds)])
    comparison=new_result(performance_base,before);measurements=json.loads((comparison/'measurements.json').read_text())
    assert len(measurements)==4
    def qualified(row):return row['input_hz_self_reported'] is not None and row['input_hz_self_reported']>=30 and row['output_hz']>=30 and row['control_hz']>=20 and row['p95_ms'] is not None and row['p95_ms']<200 and row['output_stamps_unique']
    assert all(not qualified(row) for row in measurements if row['variant']!='optimized'),measurements
    assert qualified(next(row for row in measurements if row['variant']=='optimized')),measurements
    before=set(performance_base.iterdir())
    run('performance_optimized_long_window',[python,'M1/M1-4/measure_chain.py','--variants','optimized','--seconds',str(a.long_seconds)])
    long=new_result(performance_base,before);extended=json.loads((long/'measurements.json').read_text());assert len(extended)==1 and qualified(extended[0]),extended
    faults=(ROOT/'M1/M1-4/FAULTS.md').read_text();assert len([line for line in faults.splitlines() if line.startswith('## ')])>=4
    report['tasks']['M1-4']=dict(status='PASS',comparison_source=str(comparison.relative_to(ROOT)),comparison=measurements,
        long_window_source=str(long.relative_to(ROOT)),long_window=extended[0],pixel_header_cases=5,faults_document_entries_at_least_four=True)
    report.update(status='PASS',all_four_tasks_pass=True,
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['M1/M1-1/src/smartcar_training/smartcar_training/sensor_chain.py','M1/M1-3/projection_node.py','M1/M1-4/camera_pub.py','M1/M1-4/image_proc.py']})
    save();print('M1_COMPLETE_ACCEPTANCE_PASS',out,flush=True)
except BaseException as error:
    report.update(status='FAIL',error=str(error));save();raise
