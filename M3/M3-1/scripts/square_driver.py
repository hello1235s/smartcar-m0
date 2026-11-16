import argparse
import csv
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'common'))
import rclpy
from geometry_msgs.msg import Twist
from sim_support import SimulationClient, normalize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--laps', type=int, default=10)
    parser.add_argument('--side', type=float, default=2.0)
    parser.add_argument('--radius', type=float, default=0.65)
    parser.add_argument('--speed', type=float, default=0.6)
    parser.add_argument('--turn-speed', type=float, default=0.35)
    parser.add_argument('--out', default='logs')
    args = parser.parse_args()
    minimum = 0.28/math.tan(0.5236)+0.18/2
    if not minimum <= args.radius < args.side/2 or min(args.speed, args.turn_speed) <= 0:
        parser.error('radius must fit Ackermann inner-wheel limit and square; speeds must be positive')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = SimulationClient('square_driver')
    summary = []
    try:
        node.ready()
        for lap in range(1, args.laps+1):
            if lap > 1:
                node.reset_pose()
            node.advance(1.0)
            node.odom_rows, node.truth_rows = [], []
            node.recording = True
            for corner in range(4):
                node.drive(args.speed, 0, (args.side-2*args.radius)/args.speed)
                node.drive(args.turn_speed, args.turn_speed/args.radius, (math.pi/2)*args.radius/args.turn_speed)
            node.drive(0, 0, 1.0)
            node.recording = False
            result = {'lap': lap, 'side_m': args.side, 'radius_m': args.radius, 'minimum_center_radius_m': minimum}
            for source, rows in [('odom', node.odom_rows), ('truth', node.truth_rows)]:
                if len(rows) < 30:
                    raise RuntimeError('Insufficient actual '+source+' samples')
                with (out/('run_%02d_%s.csv' % (lap, source))).open('w', newline='') as stream:
                    writer = csv.writer(stream)
                    writer.writerow(['t','x','y','theta'])
                    writer.writerows(rows)
                result[source+'_position_error_m'] = math.hypot(rows[-1][1]-rows[0][1], rows[-1][2]-rows[0][2])
                result[source+'_angle_error_deg'] = abs(math.degrees(normalize(rows[-1][3]-rows[0][3])))
                result[source+'_x_span_m'] = max(row[1] for row in rows)-min(row[1] for row in rows)
                result[source+'_y_span_m'] = max(row[2] for row in rows)-min(row[2] for row in rows)
                if max(result[source+'_x_span_m'], result[source+'_y_span_m']) < 0.5:
                    raise RuntimeError('Vehicle did not follow commands: '+json.dumps(result))
            summary.append(result)
            (out/'runs.json').write_text(json.dumps(summary, indent=2))
            print(json.dumps(result), flush=True)
    finally:
        node.command = Twist()
        node.publisher.publish(node.command)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
