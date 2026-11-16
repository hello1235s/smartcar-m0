import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import psutil
import rclpy
from rclpy.node import Node
from std_msgs.msg import String,Bool
from geometry_msgs.msg import Twist,TwistStamped
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/M5-dashboard'/time.strftime('%Y%m%d_%H%M%S'); OUT.mkdir(parents=True)
os.environ['ROS_DOMAIN_ID']='68'
env=dict(os.environ); processes=[]; streams=[]; samples=[]
def start(command,name):
    stream=(OUT/(name+'.log')).open('w'); streams.append(stream)
    proc=subprocess.Popen(command,env=env,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True); processes.append(proc); return proc
def api(action,**values):
    data=json.dumps(dict(action=action,**values)).encode(); req=urllib.request.Request('http://127.0.0.1:8081/api/command',data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as response: return json.load(response)
try:
    aggregator=start([str(ROOT/'install_ros/dashboard_tools/lib/dashboard_tools/dashboard_aggregator')],'aggregator')
    bridge=start([str(ROOT/'install_ros/smartcar_training/lib/smartcar_training/control_bridge')],'chassis')
    perception=start([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M6/M6-1/perception_node.py')],'perception')
    host=start([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M5/M5-2/host_side/dashboard.py'),'--no-browser'],'host')
    simulator=start([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M5/M5-2/simulator.py')],'simulator')
    rclpy.init(); node=Node('dashboard_verifier'); metrics=[]; faults=[]; reference=[]
    node.create_subscription(String,'/dashboard/metrics',lambda m:metrics.append((time.monotonic(),len(m.data),json.loads(m.data))),10)
    node.create_subscription(String,'/dashboard/faults',lambda m:faults.append((time.monotonic(),json.loads(m.data))),100)
    node.create_subscription(TwistStamped,'/ackermann_steering_controller/reference',lambda m:reference.append((time.monotonic(),m.twist.linear.x)),10)
    mode=node.create_publisher(String,'/simulator/mode',10); command=node.create_publisher(Twist,'/cmd_vel',10)
    def spin(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end: rclpy.spin_once(node,timeout_sec=.03)
    spin(5)
    assert all(p.poll() is None for p in processes), [(p.pid,p.poll()) for p in processes]
    for p in [psutil.Process(aggregator.pid),psutil.Process(host.pid)]: p.cpu_percent()
    monitored=[psutil.Process(aggregator.pid),psutil.Process(host.pid)]; begin=time.monotonic(); injected={}; actions={}
    while time.monotonic()-begin<65:
        elapsed=time.monotonic()-begin
        assert all(p.poll() is None for p in processes), [(p.pid,p.poll()) for p in processes]
        for when,label in [(5,'slow'),(12,'camera_off'),(18,'normal'),(25,'hot'),(30,'normal')]:
            key=str(when)
            if elapsed>=when and key not in injected: mode.publish(String(data=label)); injected[key]=time.monotonic()
        if elapsed>2 and 'start' not in actions: actions['start']=api('START')
        if elapsed>6 and 'pause' not in actions: actions['pause']=api('PAUSE')
        if elapsed>8 and 'resume' not in actions: actions['resume']=api('RESUME')
        if elapsed>15 and 'params' not in actions: actions['params']=api('SET_PARAMS',values=dict(confidence=.65,nav_speed=.25))
        if elapsed>32 and 'stop' not in actions:
            actions['stop']=api('STOP'); actions['stop_t']=time.monotonic()
        if elapsed>34 and 'reset' not in actions: actions['reset']=api('CLEAR_ESTOP')
        cmd=Twist(); cmd.linear.x=.3; command.publish(cmd)
        samples.append(dict(t=elapsed,aggregator_cpu=monitored[0].cpu_percent(),aggregator_rss_mb=monitored[0].memory_info().rss/1024**2,host_cpu=monitored[1].cpu_percent(),host_rss_mb=monitored[1].memory_info().rss/1024**2))
        spin(.25)
    with urllib.request.urlopen('http://127.0.0.1:8080/api/state') as response: final=json.load(response)
    with urllib.request.urlopen('http://127.0.0.1:8080/api/export') as response: (OUT/'offline_snapshot.html').write_bytes(response.read())
    lost=next((t-injected['12'] for t,f in faults if t>=injected['12'] and f.get('topic')=='/perception/detections' and f.get('type')=='LOST'),None)
    stopped=[v for t,v in reference if actions['stop_t']+.2<t<actions['stop_t']+1.8]
    report=dict(duration_s=time.monotonic()-begin,discovered_topics=list(metrics[-1][2]['topics']),metrics_hz=(len(metrics)-1)/(metrics[-1][0]-metrics[0][0]),mean_message_bytes=sum(x[1] for x in metrics)/len(metrics),camera_lost_detection_s=lost,fault_types=sorted(set(f['type'] for _,f in faults)),estop_continuous_override_blocked=bool(stopped) and all(v==0 for v in stopped),actions=actions,final_state=final,resources={key:dict(mean=sum(s[key] for s in samples)/len(samples),max=max(s[key] for s in samples)) for key in ['aggregator_cpu','aggregator_rss_mb','host_cpu','host_rss_mb']})
    report['bandwidth_kbytes_s']=report['mean_message_bytes']*report['metrics_hz']/1000
    (OUT/'report.json').write_text(json.dumps(report,indent=2)); (OUT/'resources.json').write_text(json.dumps(samples)); (OUT/'faults.json').write_text(json.dumps(faults)); print(json.dumps(report,indent=2))
    assert lost is not None and lost<1.0
    assert report['estop_continuous_override_blocked']
    assert '/perception/auto_discovered' in report['discovered_topics']
    assert report['resources']['aggregator_rss_mb']['max']<50
finally:
    for proc in reversed(processes):
        if proc.poll() is None: os.killpg(proc.pid,signal.SIGINT)
    for proc in reversed(processes):
        try: proc.wait(timeout=7)
        except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
    for stream in streams: stream.close()
    if rclpy.ok(): node.destroy_node(); rclpy.shutdown()
