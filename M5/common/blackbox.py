import json
import threading
import time
import struct
from pathlib import Path
from mcap.writer import Writer,CompressionType
from rclpy.serialization import serialize_message
from std_msgs.msg import String


class Blackbox:
    def __init__(self,path):
        self.stream=Path(path).open('wb'); self.writer=Writer(self.stream,compression=CompressionType.NONE)
        self.writer.start(profile='ros2',library='smartcar-training')
        self.schema=self.writer.register_schema(name='std_msgs/msg/String',encoding='ros2msg',data=b'string data\n')
        self.channels={}; self.lock=threading.Lock(); self.closed=False

    def write(self,topic,data,ros_ns=None):
        with self.lock:
            if self.closed: return
            if topic not in self.channels: self.channels[topic]=self.writer.register_channel(topic=topic,message_encoding='cdr',schema_id=self.schema)
            now=time.time_ns(); value=dict(wall_ns=now,ros_ns=ros_ns,payload=data)
            payload=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')+b'\0'
            cdr=b'\x00\x01\x00\x00'+struct.pack('<I',len(payload))+payload
            self.writer.add_message(channel_id=self.channels[topic],log_time=now,publish_time=ros_ns or now,data=cdr)

    def close(self):
        with self.lock:
            if not self.closed: self.writer.finish(); self.stream.close(); self.closed=True
