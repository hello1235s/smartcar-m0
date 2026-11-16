"""Offline wake-word command adapter. Consumes K230 RIGHT 16k mono ROS audio."""
import argparse
import json
import time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import UInt8MultiArray,String
from vosk import Model,KaldiRecognizer,SetLogLevel


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--out',required=True); p.add_argument('--seconds',type=float,default=100); a=p.parse_args()
    SetLogLevel(-1); grammar=json.dumps(['小车 开始','小车 暂停','小车 停车','小车 求助','[unk]'],ensure_ascii=False)
    recognizer=KaldiRecognizer(Model(a.model),16000,grammar); recognizer.SetWords(True)
    rclpy.init(); node=Node('offline_k230_voice'); pub=node.create_publisher(String,'/operator/voice_command',10); records=[]; armed_until=0
    def audio(message):
        nonlocal armed_until
        if not recognizer.AcceptWaveform(bytes(message.data)): return
        result=json.loads(recognizer.Result()); text=result.get('text','').replace(' ','')
        if not text: return
        record=dict(ts_ns=time.time_ns(),text=text,words=result.get('result',[]),action=None)
        if '小车' in text: armed_until=time.monotonic()+4
        if time.monotonic()<armed_until:
            actions={'开始':'START','暂停':'PAUSE','停车':'STOP','求助':'HELP'}
            for word,action in actions.items():
                if word in text:
                    confidences=[w.get('conf',0) for w in result.get('result',[])]
                    if confidences and sum(confidences)/len(confidences)>=.65:
                        pub.publish(String(data=action)); record['action']=action; armed_until=0
                    break
        records.append(record); print(json.dumps(record,ensure_ascii=False),flush=True)
    node.create_subscription(UInt8MultiArray,'/audio/pcm_s16le_16k_mono',audio,qos_profile_sensor_data)
    deadline=time.monotonic()+a.seconds
    try:
        while rclpy.ok() and time.monotonic()<deadline: rclpy.spin_once(node,timeout_sec=.1)
    finally:
        path=Path(a.out); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(dict(source='real K230 USB microphone',records=records,wake_phrase='小车',confidence_gate=.65),ensure_ascii=False,indent=2)); node.destroy_node(); rclpy.try_shutdown()


if __name__=='__main__': main()
