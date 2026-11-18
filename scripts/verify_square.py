import os
import signal
import subprocess
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'M3/M3-1/results'/time.strftime('%Y%m%d_%H%M%S')
OUT.mkdir(parents=True)
shutil.copyfile(ROOT/'M3/M3-1/src/smart_car_description/config/ackermann_controllers.yaml', OUT/'controller_config_used.yaml')
env = dict(os.environ, ROS_DOMAIN_ID='63', GAZEBO_MASTER_URI='http://127.0.0.1:11375', GAZEBO_MODEL_DATABASE_URI='', DISPLAY=':0')
stream = (OUT/'simulation.log').open('w')
process = subprocess.Popen(['ros2','launch','smart_car_description','sim.launch.py'], env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
try:
    result = subprocess.run([str(ROOT/'.venv-ros/bin/python'), str(ROOT/'M3/M3-1/scripts/square_driver.py'), '--laps','10','--side','2.0','--out',str(OUT/'logs')], env=env, capture_output=True, text=True, timeout=1800)
    (OUT/'driver.log').write_text(result.stdout+result.stderr)
    print(result.stdout, flush=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1800:])
    result = subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-1/scripts/analyze.py'),'--logs',str(OUT/'logs'),'--out',str(OUT)], env=env, capture_output=True, text=True, timeout=30)
    (OUT/'analysis.log').write_text(result.stdout+result.stderr)
    assert result.returncode == 0, result.stderr
    print(result.stdout, flush=True)
finally:
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    stream.close()
