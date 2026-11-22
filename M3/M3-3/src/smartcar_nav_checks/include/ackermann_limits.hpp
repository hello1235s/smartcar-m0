#pragma once
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace smartcar_nav_checks {
struct Motion { double v,w; };
struct TerminalReference { bool enabled; double x,y; };
inline TerminalReference aligned_terminal_reference(double x,double y,double heading,double extension,double xy_tolerance,double yaw_tolerance) {
  if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(heading)||!std::isfinite(extension)||
     !std::isfinite(xy_tolerance)||!std::isfinite(yaw_tolerance)||extension<=0||xy_tolerance<=0||yaw_tolerance<=0)
    throw std::invalid_argument("Invalid terminal reference");
  const double angle=std::atan2(std::sin(heading),std::cos(heading));
  const double longitudinal=x*std::cos(angle)+y*std::sin(angle);
  const double lateral=-x*std::sin(angle)+y*std::cos(angle);
  // The real goal is unchanged. Ignore only the tiny cusp in a re-planned final
  // path when heading is already acceptable and cross-track error fits XY tolerance.
  if(std::hypot(x,y)>=.20||std::abs(angle)>yaw_tolerance||std::abs(lateral)>.75*xy_tolerance||
     std::abs(longitudinal)<=.25*xy_tolerance) return {false,x,y};
  const double direction=std::copysign(1.,longitudinal);
  return {true,x+direction*extension*std::cos(angle),y+direction*extension*std::sin(angle)};
}
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
