// Apache-2.0. Uses the public/protected API of Nav2 Humble RPP.
// Upstream: ros-navigation/navigation2/nav2_regulated_pure_pursuit_controller.
// Adds chassis-feasible prediction and a virtual terminal heading reference.
#include "nav2_regulated_pure_pursuit_controller/regulated_pure_pursuit_controller.hpp"
#include "nav2_util/node_utils.hpp"
#include "nav2_core/exceptions.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "ackermann_limits.hpp"
#include "valid_pose.hpp"
#include <mutex>
namespace smartcar_nav_checks {
class AckermannRPP: public nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController {
  using Base=nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController;
  double radius_=.60,extension_=.45,slowdown_=.60,gain_=.7;
  geometry_msgs::msg::PoseStamped goal_;
public:
  void configure(const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,std::string name,
      std::shared_ptr<tf2_ros::Buffer> tf,std::shared_ptr<nav2_costmap_2d::Costmap2DROS> map) override {
    Base::configure(parent,name,tf,map); auto node=parent.lock();
    for(const auto & parameter:std::vector<std::pair<std::string,double*>>{
        {"min_turning_radius",&radius_},{"terminal_extension",&extension_},
        {"terminal_slowdown_distance",&slowdown_},{"terminal_speed_gain",&gain_}}) {
      nav2_util::declare_parameter_if_not_declared(node,name+"."+parameter.first,rclcpp::ParameterValue(*parameter.second));
      node->get_parameter(name+"."+parameter.first,*parameter.second);
      if(!std::isfinite(*parameter.second)||*parameter.second<0) throw std::invalid_argument("Invalid Ackermann RPP bound");
    }
    if(radius_<=0||slowdown_<=0||gain_<=0||use_rotate_to_heading_)
      throw std::invalid_argument("Ackermann RPP needs positive motion bounds and use_rotate_to_heading=false");
  }
  void setPlan(const nav_msgs::msg::Path & original) override {
    std::lock_guard<std::mutex> guard(mutex_);
    if(original.poses.empty()) throw nav2_core::PlannerException("Empty Ackermann reference path");
    goal_=original.poses.back(); goal_.header=original.header;
    nav_msgs::msg::Path tracking=original;
    const auto & q=goal_.pose.orientation;
    const double heading=std::atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));
    double direction=1.;
    if(original.poses.size()>1) {
      const auto & before=original.poses[original.poses.size()-2].pose.position;
      const auto & last=goal_.pose.position;
      if((last.x-before.x)*std::cos(heading)+(last.y-before.y)*std::sin(heading)<0) direction=-1.;
    }
    const int count=static_cast<int>(std::ceil(extension_/.05));
    for(int i=1;i<=count;++i) {
      auto point=goal_; const double offset=direction*extension_*i/count;
      point.pose.position.x+=offset*std::cos(heading); point.pose.position.y+=offset*std::sin(heading);
      tracking.poses.push_back(point);
    }
    // ControllerServer independently retains original.poses.back() as the true goal.
    Base::setPlan(tracking);
  }
  geometry_msgs::msg::TwistStamped computeVelocityCommands(const geometry_msgs::msg::PoseStamped & pose,
      const geometry_msgs::msg::Twist & speed,nav2_core::GoalChecker *) override {
    std::lock_guard<std::mutex> guard(mutex_);
    geometry_msgs::msg::PoseStamped goal_here;
    auto current_goal=goal_;
    // A fixed map goal needs the latest map->odom correction, not the transform
    // at the last planner message time. Never wait for TF holding the costmap.
    current_goal.header.stamp=builtin_interfaces::msg::Time();
    if(!transformPose(pose.header.frame_id,current_goal,goal_here))
      throw nav2_core::PlannerException("Goal transform unavailable; hold safely");
    std::unique_lock<nav2_costmap_2d::Costmap2D::mutex_t> map_guard(*(costmap_->getMutex()));
    const double distance=std::hypot(goal_here.pose.position.x-pose.pose.position.x,goal_here.pose.position.y-pose.pose.position.y);
    auto path=transformGlobalPlan(pose);
    double lookahead=getLookAheadDistance(speed);
    if(allow_reversing_) lookahead=std::min(lookahead,findVelocitySignChange(path));
    auto carrot=getLookAheadPoint(lookahead,path); carrot_pub_->publish(createCarrotMsg(carrot));
    const double x=carrot.pose.position.x,y=carrot.pose.position.y,rr=x*x+y*y;
    const double curvature=rr>1e-6?std::clamp(2*y/rr,-1./radius_,1./radius_):0.;
    double direction=allow_reversing_&&x<0?-1.:1.;
    double velocity=desired_linear_vel_;
    applyConstraints(curvature,speed,costAtPose(pose.pose.position.x,pose.pose.position.y),path,velocity,direction);
    auto feasible=bounded_motion(velocity,velocity*curvature,radius_,distance,slowdown_,gain_,min_approach_linear_velocity_);
    // The virtual reference aligns heading; it never changes the physical goal.
    // Near the goal predict only to its stopping region, never a fictitious extra .45m drive.
    double prediction_distance=std::hypot(x,y);
    if(distance<slowdown_) prediction_distance=std::min(prediction_distance,distance+.02);
    if(use_collision_detection_&&isCollisionImminent(pose,feasible.v,feasible.w,prediction_distance))
      throw nav2_core::PlannerException("AckermannRPP detected collision on feasible chassis arc");
    geometry_msgs::msg::TwistStamped command; command.header=pose.header;
    command.twist.linear.x=feasible.v; command.twist.angular.z=feasible.w;
    return command;
  }
};
}
PLUGINLIB_EXPORT_CLASS(smartcar_nav_checks::AckermannRPP,nav2_core::Controller)
