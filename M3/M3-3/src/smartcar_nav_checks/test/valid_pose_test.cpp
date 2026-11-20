#include "valid_pose.hpp"
#include <limits>
#include <iostream>
using namespace smartcar_nav_checks;
int main() {
  Pose origin{0,0,0,0,0,0,1},zero{},near{.04,.02,0,0,0,0,1};
  if(reached(origin,zero,.08,.15)) return 1;  // Actual Humble failed-transform regression.
  if(!reached(near,origin,.08,.15)) return 2;
  Pose far=origin; far[0]=10;
  if(reached(origin,far,.08,.15)) return 3;
  Pose turned=origin; turned[5]=std::sin(.4/2); turned[6]=std::cos(.4/2);
  if(reached(origin,turned,.08,.15)) return 4;
  Pose invalid=origin; invalid[0]=std::numeric_limits<double>::quiet_NaN();
  if(reached(origin,invalid,.08,.15)) return 5;
  Pose a=origin,b=origin;
  a[5]=std::sin(3.13/2); a[6]=std::cos(3.13/2);
  b[5]=std::sin(-3.13/2); b[6]=std::cos(-3.13/2);
  if(!reached(a,b,.08,.15)) return 6;
  std::cout<<"PASS: invalid transforms, finite values, joint XY/yaw and angle wrapping\n";
}
