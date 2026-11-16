import argparse
import asyncio
from collections import deque
import json
import os
from pathlib import Path
import signal
import queue
import sys
import threading
import time
import webbrowser
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String,Bool
from geometry_msgs.msg import Twist
from std_srvs.srv import Trigger
from action_msgs.srv import CancelGoal
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType
from fastapi import FastAPI,WebSocket,HTTPException
from fastapi.responses import HTMLResponse,FileResponse
import uvicorn
ROOT=Path(__file__).resolve().parents[3]
for path in [ROOT/'M5/M5-1',ROOT/'M5/M5-3',ROOT/'M5/common',ROOT/'M6/common']: sys.path.insert(0,str(path))
from operator_core import Operator
from remote_model import RemoteModel


class Host(Node):
    def __init__(self):
        super().__init__('smartcar_host_terminal'); self.history=deque(maxlen=18000); self.faults=deque(maxlen=3000); self.current={}; self.task={}; self.ready=False; self.lock=threading.RLock()
        self.pubs={}; self.clear=self.create_client(Trigger,'/clear_emergency_stop'); self.cancel=self.create_client(CancelGoal,'/navigate_to_pose/_action/cancel_goal')
        self.speed=self.create_client(SetParameters,'/chassis_command_bridge/set_parameters')
        self.patterns=self.create_client(SetParameters,'/dashboard_aggregator/set_parameters')
        self.model_client=RemoteModel(self); self.operator=Operator(ROOT,self.publish,self.model_client); self.last_metric_record=0; self.perception_state={}
        self.jobs=queue.Queue(128); self.jobs_closed=threading.Event(); self.action_worker=threading.Thread(target=self.actions,daemon=True); self.action_worker.start()
        self.create_subscription(String,'/perception/model_state',lambda m:setattr(self,'perception_state',json.loads(m.data)),10)
        for topic in ['/dashboard/metrics','/dashboard/faults','/dashboard/task_state']:
            self.create_subscription(String,topic,lambda m,t=topic:self.receive(t,m),100)
        self.create_subscription(Bool,'/system_ready',lambda m:setattr(self,'ready',m.data) if self.operator.params['scene']!='usb_indoor' else None,10)
        self.create_subscription(Bool,'/perception/ready',lambda m:setattr(self,'ready',m.data) if self.operator.params['scene']=='usb_indoor' else None,10)
        self.create_subscription(String,'/referee/cmd',self.referee,10)
        self.create_subscription(Bool,'/k230/button',lambda m:self.dispatch('STOP','k230_key') if m.data else None,10)
        self.create_subscription(String,'/operator/voice_command',self.voice,10)
        self.create_timer(.2,lambda:self.operator.tick())

    def receive(self,topic,message):
        try: data=json.loads(message.data)
        except ValueError: return
        now=time.monotonic()
        if topic!='/dashboard/metrics' or now-self.last_metric_record>=.19:
            self.operator.blackbox.write(topic,data,self.get_clock().now().nanoseconds)
            if topic=='/dashboard/metrics': self.last_metric_record=now
        with self.lock:
            if topic=='/dashboard/metrics': self.current=data; self.history.append(data)
            elif topic=='/dashboard/faults': self.faults.append(data)
            elif topic=='/dashboard/task_state': self.task=data
        if topic=='/dashboard/faults' and data.get('type')=='LOST' and data.get('topic','').startswith('/perception/'):
            try: self.jobs.put_nowait(('fault',self.operator,data))
            except queue.Full: self.get_logger().error('Host command queue full; fault remains visible')

    def dispatch(self,action,source,**args):
        if action=='STOP':
            self.operator.estopped=True; self.publish('/emergency_stop',True); self.publish('/cmd_vel',dict(v=0,omega=0))
        try: self.jobs.put_nowait(('command',action,dict(source=source,**args)))
        except queue.Full: self.get_logger().error('Command queue full; emergency latch still applied')

    def actions(self):
        while not self.jobs_closed.is_set():
            try: kind,target,data=self.jobs.get(timeout=.2)
            except queue.Empty: continue
            try:
                if kind=='fault': target.sensor_fault(data)
                else: self.command(target,**data)
            except Exception as error:
                if not self.jobs_closed.is_set(): self.get_logger().warning('Command rejected safely: '+str(error))

    def referee(self,message):
        try:
            data=json.loads(message.data) if message.data.startswith('{') else {'action':message.data}
            action=data.pop('action')
            if action not in ('START','PAUSE','RESUME','STOP','PENALTY','SCORE_QUERY'): raise ValueError('Unknown referee protocol command')
            self.dispatch(action,'referee_topic',**data)
        except ValueError as error: self.get_logger().warning(str(error))

    def voice(self,message):
        try:
            if message.data not in ('START','PAUSE','STOP','HELP'): raise ValueError('Unknown voice command')
            self.dispatch(message.data,'offline_voice')
        except (ValueError,RuntimeError) as error: self.get_logger().warning('Voice command rejected safely: '+str(error))

    def command(self,action,source='web',**args):
        if action=='SEAL_RUN': self.operator.close(); return dict(ok=True)
        if self.operator.closed and action!='NEW_RUN': self.command('NEW_RUN',source=source)
        if action=='NEW_RUN':
            if self.operator.worker and self.operator.worker.is_alive(): raise ValueError('Stop current task before creating run')
            if not self.operator.closed: self.operator.close()
            self.operator=Operator(ROOT,self.publish,self.model_client); self.task={}; self.faults.clear(); self.history.clear(); return dict(ok=True,run=str(self.operator.run_dir))
        return self.operator.command(action,user=source,**args)

    def publish(self,topic,data):
        if topic=='/operator/hard_reset':
            (ROOT/'M5/.terminal_restart_requested').write_text('operator requested pre/post competition restart')
            threading.Timer(.5,lambda:os.kill(os.getpid(),signal.SIGINT)).start()
        elif topic=='/task/cancel_navigation':
            if self.cancel.service_is_ready(): self.cancel.call_async(CancelGoal.Request())
        elif topic=='/operator/clear_estop':
            if not self.clear.service_is_ready(): raise RuntimeError('Chassis latch clear service unavailable')
            future=self.clear.call_async(Trigger.Request()); deadline=time.monotonic()+3
            while not future.done() and time.monotonic()<deadline: time.sleep(.01)
            if not future.done() or not future.result().success: raise RuntimeError('Chassis did not confirm manual clear')
        else:
            if topic=='/operator/parameters':
                if not self.speed.service_is_ready(): raise RuntimeError('Chassis parameter service unavailable; parameters unchanged')
                self.model_client.parameters(confidence=float(data['confidence']),perception_hz=float(data['perception_hz']))
                req=SetParameters.Request(); req.parameters=[Parameter(name='max_speed',value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE,double_value=float(data['nav_speed'])))]
                future=self.speed.call_async(req); deadline=time.monotonic()+3
                while not future.done() and time.monotonic()<deadline: time.sleep(.01)
                if not future.done() or not all(r.successful for r in future.result().results): raise RuntimeError('Chassis rejected speed; parameters unchanged')
                patterns=['/perception/*','/navigation/*','/control/*','/hw/*','/task/state']
                thresholds={'/hw/*':1.,'/task/state':0.,'/perception/model_state':0.,'/perception/ready':0.}
                thresholds.update({'/perception/detections':0.,'/perception/auto_discovered':0.,'/hw/resources':0.} if data['scene']=='usb_indoor' else {'/perception/targets':0.,'/hw/k230':0.})
                if self.patterns.service_is_ready():
                    req=SetParameters.Request(); req.parameters=[Parameter(name='topic_patterns',value=ParameterValue(type=ParameterType.PARAMETER_STRING_ARRAY,string_array_value=patterns)),Parameter(name='topic_min_hz_json',value=ParameterValue(type=ParameterType.PARAMETER_STRING,string_value=json.dumps(thresholds)))]
                    result=self.patterns.call_async(req); deadline=time.monotonic()+3
                    while not result.done() and time.monotonic()<deadline: time.sleep(.01)
                    if not result.done() or not all(r.successful for r in result.result().results): raise RuntimeError('Aggregation patterns rejected')
            kind=Bool if isinstance(data,bool) else (Twist if topic=='/cmd_vel' else String)
            if topic not in self.pubs: self.pubs[topic]=self.create_publisher(kind,topic,10)
            if kind is Twist: m=Twist(); m.linear.x=float(data['v']); m.angular.z=float(data['omega'])
            else: m=kind(data=data if kind is Bool else json.dumps(data,ensure_ascii=False))
            self.pubs[topic].publish(m)

    def snapshot(self):
        with self.lock:
            return dict(metrics=self.current,faults=list(self.faults)[-50:],task=self.task,ready=self.ready,referee=self.operator.referee.snapshot(),estopped=self.operator.estopped,params=self.operator.params,pid=os.getpid(),perception=self.perception_state,run=str(self.operator.run_dir))


def application(host):
    app=FastAPI()
    @app.get('/')
    async def index(): return FileResponse(Path(__file__).with_name('index.html'))
    @app.get('/api/state')
    def state(): return host.snapshot()
    @app.post('/api/command')
    def command(data:dict):
        try: return host.command(data.pop('action'),source='web',**data)
        except (ValueError,RuntimeError,OSError) as e: raise HTTPException(400,str(e))
    @app.get('/api/history')
    def history():
        with host.lock: return dict(history=list(host.history),faults=list(host.faults))
    @app.post('/api/infer')
    def infer(data:dict):
        path=Path(data['image']).resolve()
        if ROOT not in path.parents: raise HTTPException(400,'Image must be inside project')
        try: return host.operator.model.infer_file(path)
        except (RuntimeError,OSError) as e: raise HTTPException(400,str(e))
    @app.get('/api/export',response_class=HTMLResponse)
    def export():
        with host.lock: data=json.dumps(dict(history=list(host.history),faults=list(host.faults),state=host.snapshot()),ensure_ascii=False).replace('<','\\u003c')
        html='''<!doctype html><meta charset="utf-8"><title>Smartcar offline replay</title><style>body{font:16px sans-serif;background:#10202b;color:#e4eef4;padding:30px}input{width:90%}pre{white-space:pre-wrap}</style><h1>Smartcar · offline replay</h1><input id="seek" type="range" min="0" value="0"><b id="position"></b><pre id="view"></pre><script>const data=DATA;seek.max=Math.max(0,data.history.length-1);function show(){position.textContent=seek.value+" / "+seek.max;view.textContent=JSON.stringify({metrics:data.history[seek.value],faults:data.faults,state:data.state},null,2)}seek.oninput=show;show()</script>'''.replace('DATA',data)
        dest=host.operator.run_dir/('dashboard_snapshot_'+time.strftime('%Y%m%d_%H%M%S')+'.html'); dest.write_text(html,encoding='utf-8')
        return HTMLResponse(html,headers={'Content-Disposition':'attachment; filename="'+dest.name+'"'})
    @app.websocket('/ws')
    async def websocket(ws:WebSocket):
        await ws.accept()
        with host.lock: history=list(host.history)[-300:]
        await ws.send_json(dict(type='history',data=history))
        try:
            while True: await ws.send_json(dict(type='state',data=host.snapshot())); await asyncio.sleep(.2)
        except Exception: pass
    return app


def main():
    p=argparse.ArgumentParser(); p.add_argument('--no-browser',action='store_true'); p.add_argument('--bind',default='127.0.0.1'); a=p.parse_args()
    rclpy.init(); host=Host(); executor=SingleThreadedExecutor(); executor.add_node(host)
    def spin():
        try: executor.spin()
        except rclpy.executors.ExternalShutdownException: pass
    thread=threading.Thread(target=spin,daemon=True); thread.start(); app=application(host)
    dashboard=uvicorn.Server(uvicorn.Config(app,host=a.bind,port=8080,log_level='warning'))
    terminal=uvicorn.Server(uvicorn.Config(app,host=a.bind,port=8081,log_level='warning')); terminal.install_signal_handlers=lambda:None
    second=threading.Thread(target=terminal.run,daemon=True); second.start()
    if not a.no_browser: threading.Timer(2,lambda:webbrowser.open('http://127.0.0.1:8080')).start()
    try: dashboard.run()
    finally:
        terminal.should_exit=True; second.join(3); host.jobs_closed.set(); host.action_worker.join(3); host.operator.close(); executor.shutdown(timeout_sec=3); thread.join(3); host.destroy_node(); rclpy.shutdown()


if __name__=='__main__': main()
