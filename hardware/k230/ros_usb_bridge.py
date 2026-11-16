"""Ubuntu relay consumer. K230 USB is owned by Windows; SSH forwards localhost."""
import argparse
import base64
import json
import queue
import socket
import threading
import time
from pathlib import Path
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String, Bool, UInt8MultiArray


def main():
    p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8766)
    p.add_argument('--seconds',type=float,default=65); p.add_argument('--out',required=True); args=p.parse_args()
    rclpy.init(); node=Node('k230_usb_bridge')
    image_pub=node.create_publisher(Image,'/camera/image_raw',qos_profile_sensor_data)
    audio_pub=node.create_publisher(UInt8MultiArray,'/audio/pcm_s16le_16k_mono',qos_profile_sensor_data)
    button_pub=node.create_publisher(Bool,'/k230/button',10); meta_pub=node.create_publisher(String,'/hw/k230',10)
    pending=queue.Queue(128); closed=threading.Event(); stats=dict(video=0,audio=0,button=0,dropped=0,errors=[],source='real_K230_USB_via_SSH',audio_samples=0)
    def read():
        while not closed.is_set():
            try:
                with socket.create_connection((args.host,args.port),timeout=2) as sock:
                    sock.settimeout(3)
                    with sock.makefile('rb') as f:
                        for line in f:
                            if closed.is_set(): return
                            if len(line)>1048576: raise RuntimeError('Oversized relay packet')
                            event=json.loads(line)
                            try: pending.put_nowait(event)
                            except queue.Full:
                                pending.get_nowait(); pending.put_nowait(event); stats['dropped']+=1
            except (OSError,ValueError) as error:
                closed.wait(.2)
    reader=threading.Thread(target=read,daemon=True); reader.start(); deadline=time.monotonic()+args.seconds; first=last=None
    try:
        while rclpy.ok() and time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.001)
            try: e=pending.get(timeout=.05)
            except queue.Empty: continue
            kind=e['kind']; stamp=node.get_clock().now().to_msg()
            # Stamp is ROS receipt time, NOT an uncalibrated K230 capture timestamp.
            if kind=='video':
                bgr=cv2.imdecode(np.frombuffer(base64.b64decode(e['data']),np.uint8),cv2.IMREAD_COLOR)
                if bgr is None: raise ValueError('Invalid JPEG')
                msg=Image(); msg.header.stamp=stamp; msg.header.frame_id='k230_camera_optical'
                msg.height,msg.width=bgr.shape[:2]; msg.encoding='bgr8'; msg.step=msg.width*3; msg.data=bgr.tobytes(); image_pub.publish(msg)
                stats['video']+=1; first=first or time.monotonic(); last=time.monotonic()
            elif kind=='audio':
                stereo=np.frombuffer(base64.b64decode(e['data']),dtype='<i2').reshape(-1,2)
                mono=stereo[:,1].copy().tobytes(); msg=UInt8MultiArray(); msg.data=list(mono); audio_pub.publish(msg)
                stats['audio']+=1; stats['audio_samples']+=len(mono)//2
            elif kind=='button':
                button_pub.publish(Bool(data=e['pressed'])); stats['button']+=1
            elif kind=='error': stats['errors'].append(e)
            meta={k:v for k,v in e.items() if k!='data'}; meta['ros_receipt_ns']=node.get_clock().now().nanoseconds
            meta_pub.publish(String(data=json.dumps(meta)))
            if kind=='done': break
    finally:
        closed.set(); reader.join(4)
        stats['video_hz']=(stats['video']-1)/(last-first) if stats['video']>1 else 0
        stats['audio_seconds']=stats['audio_samples']/16000
        dest=Path(args.out); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(stats,indent=2))
        print(json.dumps(stats,indent=2)); node.destroy_node(); rclpy.shutdown()
    if stats['errors'] or min(stats['video'],stats['audio'])==0: raise SystemExit(1)


if __name__=='__main__': main()
