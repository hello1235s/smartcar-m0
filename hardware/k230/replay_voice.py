import argparse
import json
import time
import wave
from pathlib import Path
from vosk import Model,KaldiRecognizer,SetLogLevel


def main():
    p=argparse.ArgumentParser(); p.add_argument('--wav',required=True); p.add_argument('--model',required=True); p.add_argument('--out',required=True); p.add_argument('--publish',action='store_true'); p.add_argument('--realtime',action='store_true'); a=p.parse_args()
    SetLogLevel(-1); grammar=json.dumps(['小车 开始','小车 暂停','小车 停车','小车 求助','[unk]'],ensure_ascii=False); recognizer=KaldiRecognizer(Model(a.model),16000,grammar); recognizer.SetWords(True); events=[]
    if a.publish:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        rclpy.init(); node=Node('real_recording_voice_replay'); pub=node.create_publisher(String,'/operator/voice_command',10); time.sleep(1)
    def result(value):
        text=value.get('text','').replace(' ',''); words=value.get('result',[]); action=None
        if text and '小车' in text and words and sum(w['conf'] for w in words)/len(words)>=.65:
            action=next((v for k,v in {'开始':'START','暂停':'PAUSE','停车':'STOP','求助':'HELP'}.items() if k in text),None)
        if text:
            event=dict(text=text,words=words,action=action); events.append(event); print(json.dumps(event,ensure_ascii=False),flush=True)
            if a.publish and action: pub.publish(String(data=action)); rclpy.spin_once(node,timeout_sec=.01)
    with wave.open(a.wav,'rb') as stream:
        assert (stream.getnchannels(),stream.getframerate(),stream.getsampwidth())==(1,16000,2)
        started=time.monotonic(); frames=0
        while True:
            data=stream.readframes(640)
            if not data: break
            frames+=len(data)//2
            if recognizer.AcceptWaveform(data): result(json.loads(recognizer.Result()))
            if a.realtime: time.sleep(max(0,started+frames/16000-time.monotonic()))
        result(json.loads(recognizer.FinalResult()))
    report=dict(source='replay of actual user K230 microphone recording, not synthesized speech',real_time=a.realtime,seconds=frames/16000,events=events,recognized_commands=[e['action'] for e in events if e['action']]); dest=Path(a.out); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if a.publish: node.destroy_node(); rclpy.try_shutdown()


if __name__=='__main__': main()
