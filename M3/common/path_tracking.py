"""ROS-independent forward Ackermann path tracking; no simulation truth input."""
from dataclasses import dataclass
import math


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


@dataclass(frozen=True)
class Reference:
    x: float
    y: float
    yaw: float
    s: float
    curvature: float


def rounded_square(side=2.0, radius=0.65, spacing=0.015):
    if not (side > 2 * radius > 0 and spacing > 0):
        raise ValueError('Square side must exceed twice a positive radius; spacing must be positive')
    points = [Reference(0., 0., 0., 0., 0.)]
    x = y = heading = distance = 0.
    for _ in range(4):
        length = side - 2 * radius
        count = max(2, math.ceil(length / spacing))
        for i in range(1, count + 1):
            step = length * i / count
            points.append(Reference(x + step * math.cos(heading), y + step * math.sin(heading), heading, distance + step, 0.))
        x, y, distance = points[-1].x, points[-1].y, points[-1].s
        count = max(3, math.ceil(math.pi * radius / (2 * spacing)))
        for i in range(1, count + 1):
            angle = math.pi * i / (2 * count)
            points.append(Reference(x + radius * (math.sin(heading + angle) - math.sin(heading)),
                                    y - radius * (math.cos(heading + angle) - math.cos(heading)),
                                    heading + angle, distance + radius * angle, 1 / radius))
        x, y, heading, distance = points[-1].x, points[-1].y, points[-1].yaw, points[-1].s
    return points


class ForwardTracker:
    def __init__(self, path, straight_speed=.28, turn_speed=.18, minimum_radius=.60,
                 position_tolerance=.035, yaw_tolerance=.07):
        if len(path) < 3 or min(straight_speed, turn_speed, minimum_radius) <= 0:
            raise ValueError('A nonempty path and positive motion bounds are required')
        self.path = path
        self.straight_speed, self.turn_speed = straight_speed, turn_speed
        self.minimum_radius = minimum_radius
        self.position_tolerance, self.yaw_tolerance = position_tolerance, yaw_tolerance
        self.index = 0
        self.previous_speed = 0.

    def command(self, pose, dt=.05):
        if len(pose) != 3 or not all(math.isfinite(v) for v in pose):
            raise ValueError('Pose must contain three finite values')
        x, y, heading = pose
        start = max(0, self.index - 4)
        candidates = range(start, min(len(self.path), self.index + 60))
        nearest = min(candidates, key=lambda i: math.hypot(self.path[i].x - x, self.path[i].y - y))
        self.index = max(self.index, nearest)
        ref, end = self.path[self.index], self.path[-1]
        remaining = end.s - ref.s
        error = math.hypot(end.x - x, end.y - y)
        yaw_error = wrap(end.yaw - heading)
        done = remaining < .15 and error <= self.position_tolerance and abs(yaw_error) <= self.yaw_tolerance
        if done:
            self.previous_speed = 0.
            return 0., 0., dict(done=True, index=self.index, remaining_m=remaining, position_error_m=error, yaw_error_rad=yaw_error)
        target_speed = self.turn_speed if abs(ref.curvature) > .2 else self.straight_speed
        target_speed = min(target_speed, max(.035, math.sqrt(max(0., 2 * .25 * remaining))))
        if remaining < .35:
            target_speed = min(target_speed, max(.035, .8 * error))
        dt = min(.2, max(.001, dt))
        speed = min(target_speed, self.previous_speed + .25 * dt)
        speed = max(speed, self.previous_speed - .5 * dt)
        self.previous_speed = speed
        lookahead = max(.16, min(.30, .14 + .6 * speed))
        target = self.index
        while target < len(self.path) - 1 and self.path[target].s < ref.s + lookahead:
            target += 1
        carrot = self.path[target]
        extension = max(0., ref.s + lookahead - end.s)
        cx = carrot.x + extension * math.cos(end.yaw)
        cy = carrot.y + extension * math.sin(end.yaw)
        dx, dy = cx - x, cy - y
        lateral = -math.sin(heading) * dx + math.cos(heading) * dy
        curvature = 2 * lateral / max(.0025, dx * dx + dy * dy)
        curvature = max(-1 / self.minimum_radius, min(1 / self.minimum_radius, curvature))
        return speed, speed * curvature, dict(done=False, index=self.index, remaining_m=remaining,
                                              position_error_m=error, yaw_error_rad=yaw_error, curvature=curvature)
