import sys
import threading
import time
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import Pipeline


class Mock:
    output_shape=(1,1)
    def __init__(self,fail_at=None): self.calls=0; self.fail_at=fail_at; self.busy=False
    def infer(self,slot):
        assert not self.busy; self.busy=True
        try:
            self.calls+=1; time.sleep(.003)
            if self.calls==self.fail_at: raise RuntimeError('injected engine failure')
            slot.output[:]=slot.tensor.sum()
        finally: self.busy=False


def pre(frame,size): return np.full((1,3,size,size),frame[0,0,0],np.float32),None
def post(output,shape,transform): return float(output[0,0])
def frames(n):
    for i in range(n): yield np.full((2,2,3),i%100,np.uint8)


@pytest.mark.parametrize('mode',[1,2,3])
def test_same_output_and_frame_accounting(mode):
    actual=[]; p=Pipeline(Mock(),pre,post,size=2,capacity=1)
    report=p.run(frames(50),mode,lambda f,r,m:actual.append(r))
    assert actual==[12*(i%100) for i in range(50)]
    assert report['produced']==report['inferred']==report['consumed']==50
    assert len({x['pre_to_infer_pointer'] for x in report['buffer_addresses']})<=3


def test_backpressure_bounds_live_frames():
    made=[]; consumed=[]
    def source():
        for f in frames(100):
            made.append(1); assert len(made)-len(consumed)<=5; yield f
    p=Pipeline(Mock(),pre,post,size=2,capacity=1)
    r=p.run(source(),3,lambda *args:consumed.append(1))
    assert r['queue_wait_s']>0 and len(made)==len(consumed)==100


def test_engine_error_joins_every_worker():
    p=Pipeline(Mock(fail_at=3),pre,post,size=2,capacity=1)
    with pytest.raises(RuntimeError,match='injected engine failure'): p.run(frames(100),3)
    assert all(not t.is_alive() for t in p.threads)


def test_requested_stop_drains_inflight():
    p=Pipeline(Mock(),pre,post,size=2,capacity=1); timer=threading.Timer(.08,p.request_stop); timer.start()
    r=p.run(frames(10000),3); timer.join()
    assert 0<r['consumed']<10000 and r['produced']==r['consumed']
    assert all(not t.is_alive() for t in p.threads)
