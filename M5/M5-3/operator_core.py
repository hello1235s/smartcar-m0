import csv
import json
import os
import threading
import time
from pathlib import Path
import yaml
from task_fsm import Engine,TaskContext
from task_fsm.nodes import MockBackend
from audit import Audit
from blackbox import Blackbox
from referee_bridge import Referee
from hot_model import HotModel


class Operator:
    def __init__(self,root,publish,model_client=None):
        self.root=Path(root); self.publish=publish; self.lock=threading.RLock(); self.context=None; self.worker=None; self.estopped=False
        self.run_dir=self.root/'M5/runs'/(time.strftime('%Y%m%d_%H%M%S')+'_'+str(time.time_ns()%1000000000)); self.run_dir.mkdir(parents=True)
        self.audit=Audit(self.run_dir/'audit_log.jsonl'); self.blackbox=Blackbox(self.run_dir/'blackbox.mcap')
        self.referee=Referee(self.task_action); self.model=model_client or HotModel(); self.params=dict(nav_speed=.4,perception_hz=10.,confidence=.25,scene='training_mock')
        self.state={}; self.experiment='manual'; self.closed=False; self.report=None
        with (self.run_dir/'switch_log.csv').open('w') as f: csv.writer(f).writerow(['ts_ns','kind','old','new','user','experiment','pid'])
        self.audit.append('SESSION_STARTED',pid=os.getpid(),mode='software_mock_task; real ROS transports',clock='MCAP log wall_ns + explicit ros_ns; FSM wall ts_ns')

    def emit(self,topic,data):
        self.publish(topic,data); self.blackbox.write(topic,data)

    def task_event(self,event):
        with self.lock: self.state[event['name']]=event
        self.emit('/task/state',dict(nodes=self.state.copy(),current=event,context=dict(self.context.data) if self.context else {}))

    def task_action(self,action,user):
        if action=='start':
            if self.estopped: raise ValueError('Emergency stop latched; manual clear required')
            if self.worker and self.worker.is_alive(): raise ValueError('Task already active')
            remaining=self.referee.snapshot()['remaining_s'] if self.referee.competition_active else 180
            self.context=TaskContext(task_id=self.run_dir.name,deadline=time.monotonic()+remaining,metadata={'backend':MockBackend(),'backend_name':'explicit_mock','on_event':self.task_event})
            self.context.data['triggered']=True; self.state={}
            def run():
                try:
                    report=Engine(str(self.root/'M5/M5-1/tasks/task_demo.yaml'),self.context).run()
                    self.report=report; (self.run_dir/'task_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
                    self.emit('/task/result',report)
                    if report['result'] in ('FAILED','TIMEOUT') and self.referee.state=='RUNNING':
                        self.task_action('stop','task_failure'); self.referee.state='FAULT'; self.emit('/referee/status',self.referee.snapshot())
                except Exception as error:
                    self.audit.append('TASK_ERROR',message=str(error)); self.task_action('stop','task_exception'); self.referee.state='FAULT'; self.emit('/referee/status',self.referee.snapshot())
            self.worker=threading.Thread(target=run,name='task_engine'); self.worker.start()
        elif action=='pause' and self.context: self.context.pause()
        elif action=='resume' and self.context:
            self.context.resume(); cause=self.context.metadata.pop('fault_pause',None)
            if cause: self.emit('/operator/fallback_cost',dict(cause_id=cause['cause_id'],pause_duration_s=(time.time_ns()-cause['wall_ns'])/1e9,action='manual resume after sensor fault'))
        elif action=='skip' and self.context: self.context.skip()
        elif action=='stop':
            if self.context: self.context.abort()
            self.estopped=True; self.emit('/emergency_stop',True); self.emit('/cmd_vel',dict(v=0,omega=0))
            self.emit('/task/cancel_navigation',dict(reason='emergency_stop',user=user))
        self.audit.append('TASK_'+action.upper(),user)

    def command(self,action,user='local_operator',**args):
        if action=='STOP':
            # The actuator latch must not wait for a slow parameter/model transaction.
            self.estopped=True; self.publish('/emergency_stop',True); self.publish('/cmd_vel',dict(v=0,omega=0))
        if action=='SOFT_RESET':
            self.audit.append('SOFT_RESET_REQUESTED',user)
            if self.context: self.context.abort()
            if self.worker: self.worker.join(2)
            if self.worker and self.worker.is_alive(): raise RuntimeError('Task did not cancel; soft reset refused')
            with self.lock:
                previous=self.run_dir/'task_report.json'
                if previous.exists(): previous.rename(self.run_dir/('task_report_before_reset_'+str(time.time_ns())+'.json'))
                self.context=None; self.state={}
                if self.referee.competition_active and self.referee.state in ('RUNNING','PAUSED'):
                    paused=self.referee.state=='PAUSED'; self.task_action('start',user)
                    if paused: self.context.pause()
                elif not self.referee.competition_active: self.referee=Referee(self.task_action)
                result=dict(pid=os.getpid(),context_reset=True,referee=self.referee.snapshot()); self.audit.append('SOFT_RESET_COMPLETED',user,result=result); return dict(ok=True,result=result)
        if action=='LOAD_MODEL':
            # Load/validate candidate outside the operator lock so STOP remains responsive.
            self.audit.append('COMMAND',user,command=action,arguments=args)
            try:
                result=self.switch_model(args['path'],user); self.audit.append('COMMAND_ACCEPTED',user,command=action,result=result); return dict(ok=True,result=result)
            except Exception as error:
                self.audit.append('COMMAND_REJECTED',user,command=action,error=str(error)); raise
        with self.lock:
            self.audit.append('COMMAND',user,command=action,arguments=args)
            try:
                if action in ('START','PAUSE','RESUME','STOP','PENALTY','SCORE_QUERY'): result=self.referee.command(action,user,**args)
                elif action=='SKIP': self.task_action('skip',user); result={}
                elif action=='HELP': self.emit('/referee/help',dict(user=user,text='请求人工介入')); result={}
                elif action=='HARD_RESET':
                    if self.referee.competition_active: raise ValueError('Hard reset disabled during competition')
                    self.emit('/operator/hard_reset',True); result=dict(supervised_restart_requested=True)
                elif action=='CLEAR_ESTOP':
                    if self.referee.state in ('RUNNING','COUNTDOWN'): raise ValueError('Stop referee before clearing emergency latch')
                    self.emit('/operator/clear_estop',True); self.estopped=False; result=dict(manual_clear_requested=True)
                elif action=='SET_PARAMS': result=self.switch_params(args['values'],user)
                elif action=='SET_EXPERIMENT': self.experiment=str(args['name']); result=dict(experiment=self.experiment)
                elif action=='LOAD_SCENE':
                    path=Path(args['path']).resolve()
                    if self.root not in path.parents: raise ValueError('Scene must be inside project')
                    result=self.switch_params(yaml.safe_load(path.read_text()),user)
                else: raise ValueError('Unknown command '+action)
                self.audit.append('COMMAND_ACCEPTED',user,command=action,result=result)
                self.emit('/referee/status',self.referee.snapshot()); return dict(ok=True,result=result)
            except Exception as error:
                self.audit.append('COMMAND_REJECTED',user,command=action,error=str(error)); raise

    def switch_params(self,values,user):
        if not isinstance(values,dict) or not values: raise ValueError('Parameter map required')
        candidate=dict(self.params); candidate.update(values)
        if set(candidate)-{'nav_speed','perception_hz','confidence','scene'}: raise ValueError('Unknown parameter')
        for key,lo,hi in [('nav_speed',.05,.8),('perception_hz',1.,30.),('confidence',.01,.99)]:
            if not lo<=float(candidate[key])<=hi: raise ValueError('Out of range: '+key)
        self.emit('/operator/parameters',candidate)
        old=self.params; self.params=candidate
        self.model.set_confidence(float(candidate['confidence']))
        self.switch_log('parameters',old,candidate,user); return candidate

    def switch_model(self,path,user):
        path=Path(path).resolve()
        if self.root not in path.parents or path.suffix!='.onnx': raise ValueError('Model must be ONNX inside project')
        result=self.model.load(path); self.model.set_confidence(float(self.params['confidence'])); self.switch_log('model',result['old'],result['new'],user); return result

    def switch_log(self,kind,old,new,user):
        row=[time.time_ns(),kind,json.dumps(old),json.dumps(new),user,self.experiment,os.getpid()]
        with (self.run_dir/'switch_log.csv').open('a') as f: csv.writer(f).writerow(row)
        self.blackbox.write('/operator/switch',dict(zip(['ts_ns','kind','old','new','user','experiment','pid'],row)))

    def sensor_fault(self,fault):
        if self.closed: return
        if fault.get('type')!='LOST' or not fault.get('topic','').startswith('/perception/'): return
        cause=str(fault['stamp_wall_ns'])+':'+fault['topic']
        if self.context:
            self.context.degraded=True; self.context.metadata['navigation_mode']='lidar_only_requested'; self.context.metadata['fault_pause']=dict(cause_id=cause,wall_ns=time.time_ns())
        if self.referee.state=='RUNNING': self.command('PAUSE',user='fault_policy')
        event=dict(cause_id=cause,action='pause task and request lidar-only fallback',task_mode='explicit_mock' if self.context else 'no active task',navigation_recovery_time_s=None)
        self.audit.append('SENSOR_FALLBACK','fault_policy',**event); self.emit('/operator/fallback',event)

    def tick(self):
        if self.closed: return
        if not self.lock.acquire(blocking=False): return
        try:
            self.referee.tick(); self.emit('/referee/status',self.referee.snapshot())
            if self.estopped: self.publish('/emergency_stop',True)
        finally: self.lock.release()

    def close(self):
        if self.closed: return
        self.closed=True
        if self.context and self.worker and self.worker.is_alive(): self.context.abort()
        if self.worker: self.worker.join(2)
        self.audit.append('SESSION_CLOSED'); self.audit.seal(); self.blackbox.close()
