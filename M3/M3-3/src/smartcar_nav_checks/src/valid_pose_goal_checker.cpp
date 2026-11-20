#include "nav2_core/goal_checker.hpp"
#include "nav2_util/node_utils.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "valid_pose.hpp"
#include <limits>
#include <stdexcept>
namespace smartcar_nav_checks {
class ValidPoseGoalChecker: public nav2_core::GoalChecker {
  double xy_=0.08,heading_=0.15;
  static Pose unpack(const geometry_msgs::msg::Pose & p) {
    return {p.position.x,p.position.y,p.position.z,p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w};
  }
public:
  void initialize(const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
      const std::string & name,const std::shared_ptr<nav2_costmap_2d::Costmap2DROS>) override {
    auto node=parent.lock();
    nav2_util::declare_parameter_if_not_declared(node,name+".xy_goal_tolerance",rclcpp::ParameterValue(xy_));
    nav2_util::declare_parameter_if_not_declared(node,name+".yaw_goal_tolerance",rclcpp::ParameterValue(heading_));
    node->get_parameter(name+".xy_goal_tolerance",xy_); node->get_parameter(name+".yaw_goal_tolerance",heading_);
    if(!std::isfinite(xy_)||!std::isfinite(heading_)||xy_<=0||heading_<=0) throw std::invalid_argument("Goal tolerances must be finite and positive");
  }
  void reset() override {}  // Always test position and heading together.
  bool isGoalReached(const geometry_msgs::msg::Pose & query,const geometry_msgs::msg::Pose & goal,
      const geometry_msgs::msg::Twist &) override {
    return reached(unpack(query),unpack(goal),xy_,heading_);
  }
  bool getTolerances(geometry_msgs::msg::Pose & pose,geometry_msgs::msg::Twist & speed) override {
    const auto invalid=std::numeric_limits<double>::lowest();
    pose.position.x=pose.position.y=xy_; pose.position.z=invalid;
    pose.orientation.z=std::sin(heading_/2); pose.orientation.w=std::cos(heading_/2);
    speed.linear.x=speed.linear.y=speed.linear.z=invalid;
    speed.angular.x=speed.angular.y=speed.angular.z=invalid;
    return true;
  }
};
}
PLUGINLIB_EXPORT_CLASS(smartcar_nav_checks::ValidPoseGoalChecker,nav2_core::GoalChecker)
