"""Existing perception role: transactional model swap, independent of host UI process."""
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import String,Bool
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger
from cv_bridge import CvBridge
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'M5/M5-3'),str(ROOT/'M6/common')]
from hot_model import HotModel
from runtime import read_image


class Perception(Node):
    def __init__(self):
        super().__init__('smartcar_perception'); self.model=HotModel(); self.bridge=CvBridge(); self.latest=None; self.lock=threading.Lock()
        self.declare_parameter('model_path',str(ROOT/'M6/M6-1/models/best_fp32.onnx')); self.declare_parameter('confidence',.25); self.declare_parameter('perception_hz',10.); self.declare_parameter('test_image_path','')
        self.model.load(self.get_parameter('model_path').value); self.model.detector.conf=.25
        self.state=self.create_publisher(String,'/perception/model_state',10); self.targets=self.create_publisher(String,'/perception/targets',10); self.ready=self.create_publisher(Bool,'/perception/ready',10)
        self.add_on_set_parameters_callback(self.parameters)
        group=ReentrantCallbackGroup(); self.create_subscription(Image,'/camera/image_raw',self.image,qos_profile_sensor_data,callback_group=group)
        self.create_service(Trigger,'/perception/check',self.check,callback_group=group); self.create_timer(1.,self.publish_state)
        self.last_infer=0.; self.sequence=0
    def parameters(self,parameters):
        try:
            values={p.name:p.value for p in parameters}
            if 'confidence' in values and not .01<=values['confidence']<=.99: raise ValueError('confidence out of range')
            if 'perception_hz' in values and not 1<=values['perception_hz']<=30: raise ValueError('frequency out of range')
            for key in ['model_path','test_image_path']:
                if key in values and values[key] and ROOT not in Path(values[key]).resolve().parents: raise ValueError('Path must remain inside project')
            if 'model_path' in values: self.model.load(values['model_path'],confidence=values.get('confidence',self.get_parameter('confidence').value))
            if 'confidence' in values: self.model.detector.conf=values['confidence']
            self.publish_state(); return SetParametersResult(successful=True)
        except Exception as e: return SetParametersResult(successful=False,reason=str(e))
    def publish_state(self):
        self.state.publish(String(data=json.dumps(dict(pid=os.getpid(),model_path=self.model.path,model_sha256=self.model.sha256))))
        self.ready.publish(Bool(data=self.latest is not None and time.monotonic()-self.last_infer<1.5))
    def image(self,message):
        import time
        now=time.monotonic()
        if now-self.last_infer<1/self.get_parameter('perception_hz').value: return
        if not self.lock.acquire(False): return
        try:
            self.last_infer=now; self.latest=self.bridge.imgmsg_to_cv2(message,'bgr8'); result=self.infer(self.latest); self.sequence+=1; result['seq']=self.sequence; self.targets.publish(String(data=json.dumps(result)))
        finally: self.lock.release()
    def infer(self,image):
        detections,timing=self.model.infer(image)
        confidence=sum(d['confidence'] for d in detections)/len(detections) if detections else None
        return dict(pid=os.getpid(),stamp_wall_ns=time.time_ns(),confidence=confidence,model_path=self.model.path,model_sha256=self.model.sha256,targets=detections,timing=timing,source='actual image inference; class_id/xyxy, no invented 3D grasp pose')
    def check(self,request,response):
        try:
            path=self.get_parameter('test_image_path').value; image=read_image(path) if path else self.latest
            if image is None: raise ValueError('No camera frame or explicit test image')
            result=self.infer(image); response.success=True; response.message=json.dumps(dict(detections=result['targets'],**{k:v for k,v in result.items() if k!='targets'}))
        except Exception as error: response.success=False; response.message=str(error)
        return response


if __name__=='__main__':
    rclpy.init(); node=Perception(); executor=MultiThreadedExecutor(num_threads=2); executor.add_node(node)
    try: executor.spin()
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException): pass
    finally: executor.shutdown(); node.destroy_node(); rclpy.try_shutdown()
