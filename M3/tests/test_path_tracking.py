import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from path_tracking import ForwardTracker, rounded_square, wrap


class TrackingTests(unittest.TestCase):
    def test_reference_geometry_and_nontrivial_closed_path(self):
        points = rounded_square()
        self.assertAlmostEqual(points[-1].x, 0.)
        self.assertAlmostEqual(points[-1].y, 0.)
        self.assertAlmostEqual(points[-1].yaw, 2 * math.pi)
        self.assertAlmostEqual(max(p.x for p in points) - min(p.x for p in points), 2.)
        self.assertAlmostEqual(max(p.y for p in points) - min(p.y for p in points), 2.)
        self.assertGreater(points[-1].s, 6.)

    def test_no_initial_false_success_at_closed_path_start(self):
        speed, _, state = ForwardTracker(rounded_square()).command((0., 0., 0.))
        self.assertFalse(state['done'])
        self.assertGreater(state['remaining_m'], 6.)
        self.assertGreater(speed, 0.)

    def test_invalid_pose_rejected(self):
        with self.assertRaises(ValueError):
            ForwardTracker(rounded_square()).command((float('nan'), 0., 0.))

    def test_closed_loop_with_actuator_lag_and_odometry_noise(self):
        tracker = ForwardTracker(rounded_square())
        x = y = yaw = speed = steering = 0.
        done = False
        for step in range(16000):
            dt = .02
            measured = (x + .001 * math.sin(step * .31), y + .001 * math.cos(step * .27), yaw)
            v, omega, state = tracker.command(measured, dt)
            self.assertLessEqual(abs(omega), v / .60 + 1e-9)
            target = math.atan(.28 * omega / v) if v else 0.
            steering += (target - steering) * dt / .12
            speed += (v - speed) * dt / .10
            yaw += speed * math.tan(steering) / .28 * dt
            x += speed * math.cos(yaw) * dt
            y += speed * math.sin(yaw) * dt
            if state['done']:
                done = True
                break
        self.assertTrue(done, (x, y, yaw, state))
        self.assertLess(math.hypot(x, y), .045)
        self.assertLess(abs(wrap(yaw)), .08)


if __name__ == '__main__': unittest.main()
