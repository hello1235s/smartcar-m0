#pragma once
#include <array>
#include <cmath>
namespace smartcar_nav_checks {
// x,y,z,qx,qy,qz,qw; no ROS or simulation-truth dependency.
using Pose=std::array<double,7>;
inline bool valid(const Pose & p) {
  for(double value:p) if(!std::isfinite(value)) return false;
  const double norm=p[3]*p[3]+p[4]*p[4]+p[5]*p[5]+p[6]*p[6];
  return std::abs(norm-1.)<1e-3;
}
inline double yaw(const Pose & p) {
  return std::atan2(2*(p[6]*p[5]+p[3]*p[4]),1-2*(p[4]*p[4]+p[5]*p[5]));
}
inline bool reached(const Pose & query,const Pose & goal,double xy,double heading) {
  if(!valid(query)||!valid(goal)) return false;
  const double delta=yaw(query)-yaw(goal);
  return std::hypot(query[0]-goal[0],query[1]-goal[1])<=xy &&
         std::abs(std::atan2(std::sin(delta),std::cos(delta)))<=heading;
}
}
