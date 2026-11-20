#include "nav2_core/controller.hpp"
#include "nav2_core/goal_checker.hpp"
#include "pluginlib/class_loader.hpp"
#include "rclcpp/rclcpp.hpp"
#include <iostream>
int main(int argc,char**argv) {
  rclcpp::init(argc,argv);
  try {
    pluginlib::ClassLoader<nav2_core::GoalChecker> goals("nav2_core","nav2_core::GoalChecker");
    pluginlib::ClassLoader<nav2_core::Controller> controllers("nav2_core","nav2_core::Controller");
    auto checker=goals.createSharedInstance("smartcar_nav_checks::ValidPoseGoalChecker");
    auto standard=controllers.createSharedInstance("nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController");
    auto bounded=controllers.createSharedInstance("smartcar_nav_checks::AckermannRPP");
    if(!checker||!standard||!bounded) return 2;
    std::cout<<"PASS: guarded goal checker, standard RPP and Ackermann RPP coexist\n";
  } catch(const std::exception & error) {
    std::cerr<<error.what()<<'\n'; rclcpp::shutdown(); return 1;
  }
  rclcpp::shutdown(); return 0;
}
