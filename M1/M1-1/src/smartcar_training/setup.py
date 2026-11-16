from glob import glob
from setuptools import setup

setup(name='smartcar_training', version='1.0.0', packages=['smartcar_training'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/smartcar_training']),
                  ('share/smartcar_training', ['package.xml']),
                  ('share/smartcar_training/launch', glob('launch/*.launch.py')),
                  ('share/smartcar_training/config', glob('config/*.yaml'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='张驰', maintainer_email='3544516607@qq.com', description='Smartcar ROS training', license='MIT',
      entry_points={'console_scripts': [
          'node_a_sensor = smartcar_training.sensor_chain:sensor_main',
          'node_b_filter = smartcar_training.sensor_chain:filter_main',
          'node_c_alarm = smartcar_training.sensor_chain:alarm_main',
          'control_bridge = smartcar_training.control_bridge:main',
          'filter_ready = smartcar_training.sensor_chain:ready_main']})
