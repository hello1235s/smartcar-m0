#pragma once
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace smartcar_nav_checks {
struct Motion { double v,w; };
inline Motion bounded_motion(double v,double w,double radius,double distance,double slowdown,double gain,double floor) {
  if(!std::isfinite(v)||!std::isfinite(w)||!std::isfinite(distance)||radius<=0||distance<0)
    throw std::invalid_argument("Invalid Ackermann command or target distance");
  if(std::abs(v)<1e-6) return {0.,0.};
  const double curvature=std::clamp(w/v,-1./radius,1./radius);
  double speed=std::abs(v);
  if(distance<slowdown) speed=std::min(speed,std::max(floor,gain*distance));
  v=std::copysign(speed,v);
  return {v,v*curvature};
}
}
