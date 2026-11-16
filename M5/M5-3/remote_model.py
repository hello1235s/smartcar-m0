import json
import time
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType
from std_srvs.srv import Trigger


class RemoteModel:
    """Host sends parameters; model/inference remain in the existing perception role."""
    detector=None
    def __init__(self,node):
        self.node=node; self.client=node.create_client(SetParameters,'/smartcar_perception/set_parameters'); self.check=node.create_client(Trigger,'/perception/check'); self.path=None; self.sha256=None
    def wait(self,future):
        deadline=time.monotonic()+25
        while not future.done() and self.node.context.ok() and time.monotonic()<deadline: time.sleep(.01)
        if not future.done(): raise RuntimeError('Perception service timeout')
        return future.result()
    def parameters(self,**values):
        if not self.client.service_is_ready(): raise RuntimeError('Existing perception node unavailable')
        request=SetParameters.Request()
        for key,value in values.items():
            pv=ParameterValue(type=ParameterType.PARAMETER_STRING,string_value=value) if isinstance(value,str) else ParameterValue(type=ParameterType.PARAMETER_DOUBLE,double_value=float(value))
            request.parameters.append(Parameter(name=key,value=pv))
        result=self.wait(self.client.call_async(request))
        if not all(r.successful for r in result.results): raise RuntimeError('; '.join(r.reason for r in result.results if not r.successful))
    def load(self,path,threads=1):
        self.parameters(model_path=str(path)); old=self.path; self.path=str(path)
        return dict(old=old,new=self.path,architecture='model loaded by existing perception ROS process')
    def set_confidence(self,value): self.parameters(confidence=float(value))
    def infer_file(self,path):
        self.parameters(test_image_path=str(path))
        if not self.check.service_is_ready(): raise RuntimeError('Perception check service unavailable')
        result=self.wait(self.check.call_async(Trigger.Request()))
        if not result.success: raise RuntimeError(result.message)
        return json.loads(result.message)
