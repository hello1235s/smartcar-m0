"""Record only this live ROS application window, not the user's whole desktop."""
import argparse
import sys
import signal
import time
from pathlib import Path
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from PyQt5 import QtCore, QtGui, QtWidgets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--seconds', type=float, default=21)
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = Node('projection_clock_viewer')
    app = QtWidgets.QApplication(sys.argv[:1])
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    window = QtWidgets.QWidget()
    window.setWindowTitle('M1-3 Live projection and ROS clock')
    window.setFixedSize(660, 570)
    layout = QtWidgets.QVBoxLayout(window)
    clock_label = QtWidgets.QLabel('Waiting for ROS clock...')
    image_label = QtWidgets.QLabel('Waiting for /projection/debug_image...')
    image_label.setFixedSize(640, 480)
    layout.addWidget(clock_label)
    layout.addWidget(image_label)
    bridge = CvBridge()
    state = {'image': None, 'frames': 0, 'stamp': 0}

    def receive(message):
        state.update(image=bridge.imgmsg_to_cv2(message, 'rgb8').copy(), frames=state['frames']+1,
                     stamp=message.header.stamp.sec+message.header.stamp.nanosec/1e9)
    node.create_subscription(Image, '/projection/debug_image', receive, 5)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*'MJPG'), 5, (660, 570))
    if not writer.isOpened():
        raise RuntimeError('Cannot open application recording writer')
    started = time.monotonic()
    last_recorded = -1
    snapshots = set()

    def tick():
        nonlocal last_recorded
        if not rclpy.ok():
            app.quit()
            return
        rclpy.spin_once(node, timeout_sec=0)
        elapsed = time.monotonic()-started
        clock_label.setText('use_sim_time=%s  node_clock=%.3f s\nimage_stamp=%.3f  received=%d' %
                            (node.get_parameter('use_sim_time').value, node.get_clock().now().nanoseconds/1e9, state['stamp'], state['frames']))
        if state['image'] is not None:
            image = state['image']
            view = QtGui.QImage(image.data, image.shape[1], image.shape[0], image.strides[0], QtGui.QImage.Format_RGB888).copy()
            image_label.setPixmap(QtGui.QPixmap.fromImage(view))
        record_index = int(elapsed*5)
        if record_index != last_recorded:
            capture = window.grab().toImage().convertToFormat(QtGui.QImage.Format_RGBA8888)
            data = capture.bits()
            data.setsize(capture.byteCount())
            rgba = np.frombuffer(data, np.uint8).reshape(capture.height(), capture.width(), 4)
            writer.write(cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR))
            last_recorded = record_index
            for mark in [4, 9, 14]:
                if elapsed >= mark and mark not in snapshots:
                    capture.save(str(target.with_name('clock_window_%02d.png' % mark)))
                    snapshots.add(mark)
        if elapsed >= args.seconds:
            app.quit()
    timer = QtCore.QTimer()
    timer.timeout.connect(tick)
    timer.start(10)
    window.show()
    try:
        app.exec_()
    finally:
        writer.release()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
