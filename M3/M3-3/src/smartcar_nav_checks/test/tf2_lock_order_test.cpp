// Apache-2.0. Public-API regression for the callback-under-lock cycle.
// Related upstream fix: https://github.com/ros2/geometry2/pull/990
// The external mutex represents a caller's timer/request bookkeeping lock.
#include <tf2/buffer_core.h>
#include <tf2/time.h>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <future>
#include <iostream>
#include <mutex>
#include <thread>
int main() {
  tf2::BufferCore buffer;
  std::mutex caller_mutex;
  std::promise<void> caller_locked, callback_started;
  auto locked=caller_locked.get_future();
  auto started=callback_started.get_future();
  bool completed=false;
  const auto stamp=tf2::timeFromSec(1.0);
  auto ignore=[](tf2::TransformableRequestHandle,const std::string&,
      const std::string&,tf2::TimePoint,tf2::TransformableResult) {};
  buffer.addTransformableRequest(
    [&](tf2::TransformableRequestHandle,const std::string&,const std::string&,
        tf2::TimePoint,tf2::TransformableResult) {
      callback_started.set_value();
      std::lock_guard<std::mutex> guard(caller_mutex);
      completed=true;
    },"map","car",stamp);
  std::thread waiter([&] {
    std::lock_guard<std::mutex> guard(caller_mutex);
    caller_locked.set_value();
    started.wait();
    buffer.addTransformableRequest(ignore,"map","later_frame",stamp);
  });
  locked.wait();
  geometry_msgs::msg::TransformStamped transform;
  transform.header.frame_id="map"; transform.child_frame_id="car";
  transform.header.stamp.sec=1; transform.transform.rotation.w=1.;
  // Old TF2 holds its request mutex while invoking the callback: the caller
  // waits for that mutex, while this thread waits for caller_mutex (AB-BA).
  const bool inserted=buffer.setTransform(transform,"lock_order_regression");
  waiter.join();
  if(!inserted||!completed) return 1;
  std::cout << "TF2 callback lock-order regression PASS\n";
  return 0;
}
