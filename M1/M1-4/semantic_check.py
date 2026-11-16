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
    frame = np.random.default_rng(2026).integers(0,256,(480,640,3),dtype=np.uint8)
    bridge = CvBridge()
    message = bridge.cv2_to_imgmsg(frame, 'bgr8')
    message.header.stamp.sec, message.header.stamp.nanosec = 123,456789
    message.header.frame_id = 'test_camera'
    output = []
    instance = object.__new__(ImageProc)
    instance.bridge, instance.pub = bridge, SimpleNamespace(publish=output.append)
    instance.receive(message)
    expected = reference(frame)
    actual = bridge.imgmsg_to_cv2(output[0], 'mono8')
    assert np.array_equal(actual, expected)
    assert output[0].header == message.header
    report = {'pixel_exact': True, 'header_exact': True, 'encoding': output[0].encoding, 'sha256': hashlib.sha256(actual.tobytes()).hexdigest()}
    path = Path(__file__).with_name('results')/'semantic_check.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
