from dataclasses import dataclass,field
import numpy as np


@dataclass
class Slot:
    index:int
    tensor:np.ndarray
    output:np.ndarray
    frame:object=None
    transform:object=None
    sequence:int=0
    marks:dict=field(default_factory=dict)


def allocate(count,size,output_shape):
    return [Slot(i,np.empty((1,3,size,size),np.float32),np.empty(output_shape,np.float32)) for i in range(count)]
