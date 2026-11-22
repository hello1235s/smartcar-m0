#include "ackermann_limits.hpp"
#include <iostream>
using namespace smartcar_nav_checks;
int main() {
  auto turn=bounded_motion(.32,2.,.6,4.,.6,.7,.035);
  if(std::abs(turn.w/turn.v)>1/.6+1e-12) return 1;
  auto reverse=bounded_motion(-.2,1.,.6,4.,.6,.7,.035);
  if(reverse.v>=0||std::abs(reverse.w/reverse.v)>1/.6+1e-12) return 2;
  auto stop=bounded_motion(0.,1.,.6,1.,.6,.7,.035);
  if(stop.v!=0||stop.w!=0) return 3;
  auto terminal=bounded_motion(.32,.32,.6,.08,.6,.7,.035);
  if(std::abs(terminal.v-.056)>1e-12||std::abs(terminal.w-terminal.v)>1e-12) return 4;
  auto gentle=bounded_motion(.02,.01,.6,.01,.6,.7,.035);
  if(gentle.v>.02+1e-12) return 5; // A speed floor must never accelerate a slower safe command.
  auto forward=aligned_terminal_reference(.057,.008,.02,.45,.02,.10);
  if(!forward.enabled||forward.x<.5) return 6; // A tiny re-planned cusp must not command reverse before this forward goal.
  auto backward=aligned_terminal_reference(-.057,.008,.02,.45,.02,.10);
  if(!backward.enabled||backward.x>-.5) return 7;
  if(aligned_terminal_reference(.057,.04,.02,.45,.02,.10).enabled) return 8;
  if(aligned_terminal_reference(.057,.008,.2,.45,.02,.10).enabled) return 9;
  if(aligned_terminal_reference(.5,.008,.02,.45,.02,.10).enabled) return 10;
  std::cout<<"PASS: feasible forward/reverse curvature, no spin, terminal deceleration\n";
}
