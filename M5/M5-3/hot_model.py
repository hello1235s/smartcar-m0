"""Transactional ORT swap: loading failure cannot replace the working session."""
import hashlib
import threading
from pathlib import Path


class HotModel:
    def __init__(self): self.lock=threading.RLock(); self.detector=None; self.path=None; self.sha256=None

    def load(self,path,threads=1,confidence=None):
        from runtime import Detector
        import numpy as np
        candidate=Detector(path,threads=threads)
        if confidence is not None: candidate.conf=float(confidence)
        candidate.raw(np.zeros((1,3,candidate.size,candidate.size),np.float32))
        digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        with self.lock:
            old=self.path; self.detector=candidate; self.path=str(Path(path).resolve()); self.sha256=digest
        return dict(old=old,new=self.path,sha256=digest)

    def infer(self,image):
        with self.lock: detector=self.detector
        if detector is None: raise RuntimeError('No inference model loaded')
        return detector.infer(image)

    def set_confidence(self,value):
        with self.lock:
            if self.detector: self.detector.conf=float(value)
