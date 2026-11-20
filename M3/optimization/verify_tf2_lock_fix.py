"""Bounded old/new TF2 core regression, without changing any system package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(); p.add_argument('--expect-vulnerable-baseline',action='store_true'); a=p.parse_args()
exe=ROOT/'build_ros/smartcar_nav_checks/tf2_lock_order_test'
prefix=ROOT/'vendor/m3-dds/opt/ros/humble/lib'
assert exe.is_file() and (prefix/'libtf2.so').is_file()
results=[]
for name,directory in [('system_baseline',Path('/opt/ros/humble/lib')),('project_fixed',prefix)]:
    env=dict(os.environ,LD_LIBRARY_PATH=str(directory)+':/opt/ros/humble/lib')
    deps=subprocess.check_output(['ldd',str(exe)],env=env,text=True)
    line=next(line for line in deps.splitlines() if 'libtf2.so =>' in line)
    actual=Path(line.split('=>',1)[1].strip().split()[0])
    assert actual.resolve()==(directory/'libtf2.so').resolve(),line
    try:
        run=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=3)
        case=dict(name=name,result='PASS' if run.returncode==0 else 'FAIL',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr)
    except subprocess.TimeoutExpired:
        case=dict(name=name,result='DEADLOCK_TIMEOUT',timeout_s=3)
    case.update(library=str(actual),sha256=hashlib.sha256(actual.read_bytes()).hexdigest()); results.append(case)
assert results[1]['result']=='PASS',results
if a.expect_vulnerable_baseline: assert results[0]['result']=='DEADLOCK_TIMEOUT',results
record=dict(status='PASS',cases=results,system_package=subprocess.check_output(['dpkg-query','-W','ros-humble-tf2'],text=True).strip(),
    official_fix='https://github.com/ros2/geometry2/pull/990',
    method='Two-thread lock-order regression: caller holds its own lock then registers a TF request while the ready callback takes that lock. Old BufferCore invokes callbacks holding the request lock; fixed core invokes them after unlocking. Process timeout bounds the old deadlock.',
    inference='The observed stale Nav2 TF/forced cleanup is consistent with the upstream issue and this vulnerable installed core. This test does not claim a GDB backtrace was captured from the original failed Nav2 process.')
out=ROOT/'M3/optimization/report/tf2_lock_regression.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(record,indent=2)); print(json.dumps(record))
