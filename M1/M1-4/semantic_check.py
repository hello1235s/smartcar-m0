import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
from cv_bridge import CvBridge
from image_proc import ImageProc


def reference(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    large = cv2.resize(gray, (1280,720), interpolation=cv2.INTER_LINEAR)
    bright = np.empty_like(large)
    contrast = np.empty_like(large)
    for y in range(720):
        for x in range(1280):
            bright[y,x] = min(255, int(large[y,x])+20)
    for y in range(720):
        for x in range(1280):
            contrast[y,x] = max(0, min(255, (int(bright[y,x])-128)*3//2+128))
    return cv2.resize(contrast, (640,480), interpolation=cv2.INTER_LINEAR)


def main():
    random = np.random.default_rng(2026).integers(0,256,(480,640,3),dtype=np.uint8)
    ramp = np.resize(np.arange(256,dtype=np.uint8),(480,640))
    cases = [('random_bgr',random,'bgr8'),('all_gray_levels',ramp,'mono8'),
             ('black',np.zeros((480,640,3),np.uint8),'bgr8'),
             ('white',np.full((480,640,3),255,np.uint8),'bgr8'),
             ('random_rgb',random,'rgb8')]
    bridge = CvBridge()
    checked=[]
    for index,(name,frame,encoding) in enumerate(cases):
        message = bridge.cv2_to_imgmsg(frame, encoding)
        message.header.stamp.sec, message.header.stamp.nanosec = 123+index,456789
        message.header.frame_id = 'test_camera_'+name
        output = []
        instance = object.__new__(ImageProc)
        instance.bridge, instance.pub = bridge, SimpleNamespace(publish=output.append)
        instance.receive(message)
        reference_bgr=cv2.cvtColor(frame,cv2.COLOR_GRAY2BGR) if encoding=='mono8' else cv2.cvtColor(frame,cv2.COLOR_RGB2BGR) if encoding=='rgb8' else frame
        expected = reference(reference_bgr)
        assert len(output)==1
        actual = bridge.imgmsg_to_cv2(output[0], 'mono8')
        assert np.array_equal(actual, expected),name
        assert output[0].header == message.header,name
        assert (output[0].width,output[0].height,output[0].encoding)==(640,480,'mono8')
        checked.append(dict(case=name,input_encoding=encoding,pixel_exact=True,header_exact=True,sha256=hashlib.sha256(actual.tobytes()).hexdigest()))
    report = {'pixel_exact': True, 'header_exact': True, 'encoding': 'mono8', 'sha256': checked[0]['sha256'],'cases':checked}
    path = Path(__file__).with_name('results')/'semantic_check.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
