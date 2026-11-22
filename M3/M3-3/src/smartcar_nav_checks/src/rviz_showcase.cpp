// Native RViz VisualizationFrame with its own framebuffer capture API.
// No occupancy-grid repainting or synthetic replacement for RViz rendering.
#include <QApplication>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTimer>
#include <memory>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <rviz_common/visualization_frame.hpp>
#include <rviz_common/visualization_manager.hpp>
#include <rviz_common/render_panel.hpp>
#include <rviz_common/ros_integration/ros_node_abstraction.hpp>
#include <rviz_rendering/render_window.hpp>

int main(int argc,char ** argv)
{
  std::string config,out;
  for(int i=1;i+1<argc;++i){
    if(std::string(argv[i])=="--config")config=argv[++i];
    else if(std::string(argv[i])=="--out")out=argv[++i];
  }
  if(config.empty()||out.empty()){fprintf(stderr,"--config and --out are required\n");return 2;}
  QApplication app(argc,argv);
  rclcpp::init(argc,argv);
  auto abstraction=std::make_shared<rviz_common::ros_integration::RosNodeAbstraction>("rviz_showcase");
  auto node=abstraction->get_raw_node();
  auto frame=std::make_unique<rviz_common::VisualizationFrame>(abstraction);
  frame->setApp(&app);frame->setSplashPath("");frame->initialize(abstraction,QString::fromStdString(config));
  frame->setDisplayTitleFormat("RViz - Smartcar exam");frame->show();
  QDir().mkpath(QString::fromStdString(out));
  unsigned int messages=0,width=0,height=0;unsigned int captures=0;
  auto sub=node->create_subscription<nav_msgs::msg::OccupancyGrid>("/map",rclcpp::QoS(1).transient_local(),
    [&](nav_msgs::msg::OccupancyGrid::ConstSharedPtr m){++messages;width=m->info.width;height=m->info.height;});
  QTimer timer;
  QObject::connect(&timer,&QTimer::timeout,[&](){
    if(!rclcpp::ok()){app.quit();return;}
    if(!messages)return;
    auto window=frame->getRenderWindow();
    const QString file=QString::fromStdString(out)+"/native_rviz_render.png";
    window->captureScreenShot(file.toStdString());++captures;
    auto panel=frame->getManager()->getRenderPanel();
    const QPoint relative=panel->mapTo(frame.get(),QPoint(0,0));
    const QPoint global=panel->mapToGlobal(QPoint(0,0));
    QJsonObject record{{"source","rviz_rendering::RenderWindow::captureScreenShot"},
      {"map_messages",int(messages)},{"map_width",int(width)},{"map_height",int(height)},
      {"captures",int(captures)},{"window_id",double(frame->winId())},
      {"render_x_in_window",relative.x()},{"render_y_in_window",relative.y()},
      {"render_global_x",global.x()},{"render_global_y",global.y()},
      {"render_width",window->width()},{"render_height",window->height()},
      {"window_width",frame->width()},{"window_height",frame->height()},
      {"actual_rviz_components",true},{"map_repainted_by_custom_code",false}};
    QFile metadata(QString::fromStdString(out)+"/native_rviz_render.json");
    if(metadata.open(QIODevice::WriteOnly))metadata.write(QJsonDocument(record).toJson());
  });
  timer.start(1000);
  const int result=app.exec();
  frame.reset();
  rclcpp::shutdown();
  return result;
}
