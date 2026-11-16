import hashlib
import json
import os
import threading
import time
from pathlib import Path


def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def verify(path):
    previous='0'*64; count=0
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        entry=json.loads(line); claimed=entry.pop('hash')
        if entry.get('previous_hash')!=previous or hashlib.sha256(canonical(entry)).hexdigest()!=claimed:
            return dict(valid=False,failed_line=count+1)
        previous=claimed; count+=1
    return dict(valid=True,lines=count,head=previous)


class Audit:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.lock=threading.Lock(); self.previous='0'*64; self.sealed=False
        if self.path.exists():
            result=verify(self.path)
            if not result['valid']: raise ValueError('Existing audit chain invalid; refusing append')
            self.previous=result['head']

    def append(self,action,user='local_operator',**details):
        with self.lock:
            if self.sealed: raise ValueError('Audit sealed; create a new session before appending')
            entry=dict(ts_ns=time.time_ns(),action=action,user=user,details=details,previous_hash=self.previous)
            entry['hash']=hashlib.sha256(canonical(entry)).hexdigest()
            with self.path.open('a',encoding='utf-8') as f:
                f.write(json.dumps(entry,ensure_ascii=False)+'\n'); f.flush(); os.fsync(f.fileno())
            self.previous=entry['hash']; return entry

    def seal(self):
        # Store this head separately to detect removal of a valid suffix.
        with self.lock:
            self.path.with_suffix('.seal.json').write_text(json.dumps(dict(head=self.previous,ts_ns=time.time_ns()))); self.sealed=True
