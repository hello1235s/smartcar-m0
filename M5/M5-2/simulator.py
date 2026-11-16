"""Explicit ROS software telemetry source, not measurements of a physical car."""
import json
import time
import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import String,Bool


class Simulator(Node):
    def __init__(self):
        super().__init__('training_telemetry_simulator'); self.started=time.monotonic(); self.seq=0; self.mode='normal'; self.frequency=30.; self.last_perception=0.
        self.perception=self.create_publisher(String,'/perception/detections',10); self.hw=self.create_publisher(String,'/hw/resources',10); self.counts={}; self.last_ready=None
        self.nav=self.create_publisher(String,'/navigation/quality',10); self.extra=None; self.ready=self.create_publisher(Bool,'/system_ready',10)
        self.create_subscription(String,'/simulator/mode',lambda m:setattr(self,'mode',m.data),10)
        self.create_subscription(String,'/operator/parameters',self.params,10); self.create_timer(1/30,self.tick)
    def params(self,m):
        data=json.loads(m.data); self.frequency=float(data['perception_hz']); self.mode='hardware' if data['scene']=='usb_indoor' else 'normal'
    def tick(self):
        if self.mode=='hardware': return
        now=time.monotonic(); t=now-self.started; self.seq+=1
        value=dict(stamp_wall_ns=time.time_ns(),confidence=.8+.1*math.sin(t),source='explicit_software_simulator')
        def publish(pub,key,data):
            self.counts[key]=self.counts.get(key,0)+1; pub.publish(String(data=json.dumps(dict(**data,seq=self.counts[key]))))
        rate=self.frequency/(8 if self.mode=='slow' else 1)
        if self.mode!='camera_off' and now-self.last_perception>=1/rate-.001:
            publish(self.perception,'camera',value); self.last_perception=now
        if self.seq%3==0: publish(self.nav,'nav',dict(**value,path_deviation_m=.02,network_rtt_ms=1.))
        if self.seq%6==0: self.hw.publish(String(data=json.dumps(dict(cpu_percent=99 if self.mode=='hot' else 15,temperature_c=92 if self.mode=='hot' else 45,voltage_v=12.,source='injected_simulator'))))
        if t>3 and self.extra is None: self.extra=self.create_publisher(String,'/perception/auto_discovered',10)
        if self.extra and self.seq%3==0: publish(self.extra,'extra',value)
        ready=self.mode!='camera_off'
        if ready!=self.last_ready or self.seq%30==0:
            self.ready.publish(Bool(data=ready)); self.last_ready=ready


if __name__=='__main__':
    rclpy.init(); n=Simulator()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.try_shutdown()
