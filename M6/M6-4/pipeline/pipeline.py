"""Bounded, lossless between stages; queued items are Slot references, never frames."""
import queue
import threading
import time
import numpy as np
from .buffers import allocate


class Pipeline:
    def __init__(self,engine,preprocess,postprocess,size=320,capacity=4):
        self.engine=engine; self.preprocess=preprocess; self.postprocess=postprocess; self.size=size; self.capacity=capacity
        self.stop_requested=threading.Event(); self.abort=threading.Event(); self.failures=[]; self.results=[]; self.wait_s=0.; self.threads=[]; self.addresses=[]

    def request_stop(self): self.stop_requested.set()

    def run(self,source,mode=3,on_result=None):
        if mode not in (1,2,3): raise ValueError('mode must be 1,2,3')
        if self.threads: raise ValueError('Create a fresh Pipeline for each run')
        slots=allocate(self.capacity+2,self.size,self.engine.output_shape); free=queue.Queue(len(slots)); q1=queue.Queue(self.capacity); q2=queue.Queue(self.capacity)
        for slot in slots: free.put(slot)
        stats=dict(produced=0,inferred=0,consumed=0); guard=threading.Lock()
        def inc(key):
            with guard: stats[key]+=1
        def put(q,value):
            while not self.abort.is_set():
                try: q.put(value,timeout=.05); return
                except queue.Full: continue
            raise InterruptedError()
        def get(q):
            started=time.perf_counter()
            while not self.abort.is_set():
                try:
                    value=q.get(timeout=.05)
                    with guard: self.wait_s+=time.perf_counter()-started
                    return value
                except queue.Empty: continue
            raise InterruptedError()
        def pre(slot,frame,sequence):
            slot.frame=frame; slot.sequence=sequence; slot.marks=dict(start=time.perf_counter())
            tensor,slot.transform=self.preprocess(frame,self.size); np.copyto(slot.tensor,tensor)
            slot.marks['pre']=time.perf_counter(); inc('produced')
        def infer(slot):
            pointer=slot.tensor.ctypes.data; self.engine.infer(slot)
            assert slot.tensor.ctypes.data==pointer
            with guard:
                if len(self.addresses)<20: self.addresses.append(dict(slot=slot.index,pre_to_infer_pointer=pointer,output_pointer=slot.output.ctypes.data))
            slot.marks['infer']=time.perf_counter(); inc('inferred')
        def post(slot):
            result=self.postprocess(slot.output,slot.frame.shape,slot.transform); end=time.perf_counter()
            record=dict(sequence=slot.sequence,slot=slot.index,pre_ms=(slot.marks['pre']-slot.marks['start'])*1000,infer_and_wait_ms=(slot.marks['infer']-slot.marks['pre'])*1000,total_ms=(end-slot.marks['start'])*1000)
            if on_result: on_result(slot.frame,result,record)
            self.results.append(record); slot.frame=None; inc('consumed')
        def producer():
            for sequence,frame in enumerate(source):
                if self.stop_requested.is_set(): break
                slot=get(free); pre(slot,frame,sequence); put(q1,slot)
            put(q1,None)
        def inference():
            while True:
                slot=get(q1)
                if slot is None:
                    if mode==3: put(q2,None)
                    return
                infer(slot)
                if mode==2: post(slot); put(free,slot)
                else: put(q2,slot)
        def consumer():
            while True:
                slot=get(q2)
                if slot is None: return
                post(slot); put(free,slot)
        def guarded(function):
            try: function()
            except InterruptedError: pass
            except BaseException as error:
                with guard: self.failures.append(error)
                self.abort.set()
        started=time.perf_counter()
        if mode==1:
            for sequence,frame in enumerate(source):
                if self.stop_requested.is_set(): break
                slot=slots[0]; pre(slot,frame,sequence); infer(slot); post(slot)
        else:
            for name,function in [('preprocess',producer),('inference',inference)]+([('postprocess',consumer)] if mode==3 else []):
                thread=threading.Thread(target=guarded,args=(function,),name=name); self.threads.append(thread); thread.start()
            try:
                for thread in self.threads:
                    while thread.is_alive(): thread.join(.1)
            except BaseException:
                self.abort.set()
                for thread in self.threads: thread.join(5)
                raise
            if any(thread.is_alive() for thread in self.threads): raise RuntimeError('Pipeline failed to join')
            if self.failures: raise RuntimeError('Pipeline stage failed: '+str(self.failures[0])) from self.failures[0]
        elapsed=time.perf_counter()-started
        if len(set(stats.values()))!=1: raise RuntimeError('Unaccounted frames: '+str(stats))
        return dict(**stats,seconds=elapsed,fps=stats['consumed']/elapsed,queue_capacity=self.capacity,queue_wait_s=self.wait_s,buffer_addresses=self.addresses)
