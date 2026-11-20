"""Closed path control uses /odom only; Gazebo truth is recorded independently."""
import csv
import json
import math
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
from path_tracking import ForwardTracker, rounded_square, wrap
from sim_support import SimulationClient
from geometry_msgs.msg import Twist
import rclpy


def relative_pose(row, origin):
    dx, dy = row[1] - origin[1], row[2] - origin[2]
    c, s = math.cos(origin[3]), math.sin(origin[3])
    return c * dx + s * dy, -s * dx + c * dy, wrap(row[3] - origin[3])


def run(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rclpy.init(); node = SimulationClient('feedback_square_driver'); runs = []
    try:
        node.ready()
        for lap in range(1, args.laps + 1):
            if lap > 1: node.reset_pose()
            node.command = Twist(); node.advance(1.)
            origin = node.odom[:]
            tracker = ForwardTracker(rounded_square(args.side, args.radius), args.speed, args.turn_speed)
            node.odom_rows, node.truth_rows = [], []
            node.recording = True
            traces = []; start = previous = node.seconds(); wall = time.monotonic(); done = False
            while node.seconds() - start < args.timeout and time.monotonic() - wall < args.timeout * 12:
                current = node.seconds()
                pose = relative_pose(node.odom, origin)
                v, omega, state = tracker.command(pose, current - previous)
                previous = current
                node.command.linear.x, node.command.angular.z = v, omega
                traces.append([current, *pose, state['index'], state['remaining_m'], v, omega])
                if state['done']: done = True; break
                node.advance(.05)
            node.command = Twist(); node.advance(1.)
            node.recording = False
            result = dict(lap=lap, side_m=args.side, radius_m=args.radius, mode='odom_feedback',
                          success=done, control_input='/odom only', sim_seconds=node.seconds()-start,
                          straight_speed=args.speed, turn_speed=args.turn_speed)
            for source, rows in [('odom', node.odom_rows), ('truth', node.truth_rows)]:
                if len(rows) < 30: raise RuntimeError('Insufficient independent '+source+' samples')
                with (out/('run_%02d_%s.csv' % (lap, source))).open('w', newline='') as stream:
                    writer=csv.writer(stream); writer.writerow(['t','x','y','theta']); writer.writerows(rows)
                result[source+'_position_error_m']=math.hypot(rows[-1][1]-rows[0][1],rows[-1][2]-rows[0][2])
                result[source+'_angle_error_deg']=abs(math.degrees(wrap(rows[-1][3]-rows[0][3])))
                result[source+'_x_span_m']=max(r[1] for r in rows)-min(r[1] for r in rows)
                result[source+'_y_span_m']=max(r[2] for r in rows)-min(r[2] for r in rows)
            with (out/('run_%02d_tracking.csv' % lap)).open('w',newline='') as stream:
                writer=csv.writer(stream); writer.writerow(['t','odom_relative_x','odom_relative_y','odom_relative_yaw','path_index','remaining_m','v_command','omega_command']); writer.writerows(traces)
            runs.append(result); (out/'runs.json').write_text(json.dumps(runs,indent=2))
            print(json.dumps(result),flush=True)
            if not done: raise RuntimeError('Feedback trial timed out; actual failure data retained')
    finally:
        node.command = Twist(); node.publisher.publish(node.command)
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
