import threading
import numpy as np


class Engine:
    """One session and one inference owner; reusable CPU I/O-bound output buffers."""
    def __init__(self,detector):
        self.detector=detector; self.lock=threading.Lock()
        sample=np.zeros((1,3,detector.size,detector.size),np.float32)
        self.output_shape=detector.raw(sample).shape
    def infer(self,slot):
        with self.lock:
            binding=self.detector.session.io_binding()
            binding.bind_cpu_input(self.detector.input.name,slot.tensor)
            binding.bind_output(self.detector.names[0],device_type='cpu',device_id=0,element_type=np.float32,shape=slot.output.shape,buffer_ptr=slot.output.ctypes.data)
            self.detector.session.run_with_iobinding(binding)
            if not np.isfinite(slot.output).all(): raise RuntimeError('Inference produced non-finite values')
