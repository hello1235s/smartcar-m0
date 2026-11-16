#include <rclcpp/rclcpp.hpp>
#include <rclcpp/serialization.hpp>
#include <std_msgs/msg/string.hpp>
#include <nlohmann/json.hpp>
#include <fnmatch.h>
#include <deque>
#include <fstream>
#include <cstring>
using Json=nlohmann::json;
using Message=std_msgs::msg::String;
using Steady=std::chrono::steady_clock;
struct Topic {
  std::deque<double> times, delays, confidence;
  rclcpp::GenericSubscription::SharedPtr subscription;
  std::string type, state="WAITING";
  double created=0, changed=0, slow_since=0;
  int64_t sequence=-1, received=0, lost=0;
};
class Aggregator: public rclcpp::Node {
  std::map<std::string,Topic> topics_;
  rclcpp::Publisher<Message>::SharedPtr metrics_, faults_, task_;
  rclcpp::TimerBase::SharedPtr discovery_, timer_;
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr validation_;
  Json resources_={{"cpu_percent",nullptr},{"temperature_c",nullptr},{"voltage_v",nullptr},{"network_rtt_ms",nullptr},{"path_deviation_m",nullptr}};
  Json thresholds_=Json::object();
  double wall() {return std::chrono::duration<double>(Steady::now().time_since_epoch()).count();}
  void send(rclcpp::Publisher<Message>::SharedPtr p, const Json& j) {Message m; m.data=j.dump(); p->publish(m);}
  bool matches(const std::string& name) {
    const auto patterns=get_parameter("topic_patterns").as_string_array();
    for(const auto& p:patterns) if(!fnmatch(p.c_str(),name.c_str(),0)) return true;
    return false;
  }
  void discover() {
    thresholds_=Json::parse(get_parameter("topic_min_hz_json").as_string());
    for(auto i=topics_.begin();i!=topics_.end();) {if(!matches(i->first)) i=topics_.erase(i); else ++i;}
    for(const auto& [name,types]:get_topic_names_and_types()) {
      if(name.rfind("/dashboard/",0)==0 || !matches(name) || topics_.count(name) || types.empty()) continue;
      if(topics_.size()>=64) break;
      auto& topic=topics_[name]; topic.type=types[0]; topic.created=wall(); topic.changed=wall();
      topic.subscription=create_generic_subscription(name,types[0],rclcpp::QoS(1).best_effort(),
        [this,name](std::shared_ptr<rclcpp::SerializedMessage> raw){receive(name,*raw);});
    }
  }
  void receive(const std::string& name,const rclcpp::SerializedMessage& raw) {
    auto found=topics_.find(name); if(found==topics_.end()) return;
    auto& t=found->second; double now=wall(); t.times.push_back(now);
    if(t.type=="std_msgs/msg/String" && raw.size()<65536) {
      Message message; rclcpp::Serialization<Message> serializer; serializer.deserialize_message(&raw,&message);
      auto data=Json::parse(message.data,nullptr,false);
      if(!data.is_discarded() && data.is_object()) {
        if(data.contains("confidence") && data["confidence"].is_number()) t.confidence.push_back(data["confidence"].get<double>());
        if(data.contains("seq") && data["seq"].is_number_integer()) {
          int64_t seq=data["seq"].get<int64_t>();
          if(t.sequence!=-2) {if(t.sequence>=0 && seq<=t.sequence) t.sequence=-2; else {if(t.sequence>=0) t.lost+=std::max<int64_t>(0,seq-t.sequence-1); t.sequence=seq; ++t.received;}}
        }
        if(data.contains("stamp_wall_ns") && data["stamp_wall_ns"].is_number()) {
          double delay=(static_cast<double>(std::chrono::system_clock::now().time_since_epoch().count())-data["stamp_wall_ns"].get<double>())/1e6;
          if(delay>=0 && delay<10000) t.delays.push_back(delay);
        }
        for(auto& [key,value]:resources_.items()) if(data.contains(key) && data[key].is_number()) value=data[key];
      }
      if(name==get_parameter("task_topic").as_string()) {task_->publish(message);}
    }
    while(t.confidence.size()>60) t.confidence.pop_front();
    while(t.delays.size()>60) t.delays.pop_front();
  }
  Json mean(const std::deque<double>& values) {
    if(values.empty()) return nullptr; double sum=0; for(double v:values) sum+=v; return sum/values.size();
  }
  void tick() {
    double now=wall(); Json data={{"stamp_wall_ns",std::chrono::system_clock::now().time_since_epoch().count()},{"topics",Json::object()},{"resources",resources_}};
    for(auto& [name,t]:topics_) {
      while(!t.times.empty() && t.times.front()<now-2) t.times.pop_front();
      double hz=t.times.size()>1?(t.times.size()-1)/(t.times.back()-t.times.front()):0;
      double age=t.times.empty()?now-t.created:now-t.times.back();
      double minimum=get_parameter("min_hz").as_double();
      for(const auto& [pattern,value]:thresholds_.items()) if(!fnmatch(pattern.c_str(),name.c_str(),0)) minimum=value.get<double>();
      bool event_topic=minimum==0;
      bool slow=!event_topic && now-t.created>2 && hz<minimum;
      if(slow && !t.slow_since) t.slow_since=now; if(!slow) t.slow_since=0;
      std::string state=event_topic?"EVENT":(age>get_parameter("timeout_s").as_double()?"LOST":(t.slow_since && now-t.slow_since>.3?"DEGRADED":(t.times.empty()?"WAITING":"ONLINE")));
      if(state!=t.state) {
        if(state=="LOST" || state=="DEGRADED" || t.state=="LOST" || t.state=="DEGRADED")
          send(faults_,{{"stamp_wall_ns",data["stamp_wall_ns"]},{"topic",name},{"type",state},{"previous",t.state},{"duration_s",now-t.changed},{"recovered",state=="ONLINE"}});
        t.state=state; t.changed=now;
      }
      data["topics"][name]={{"hz",hz},{"age_s",age},{"state",state},{"delay_ms",mean(t.delays)},{"confidence",mean(t.confidence)},{"loss_rate",t.sequence<0?Json(nullptr):Json(double(t.lost)/std::max<int64_t>(1,t.received+t.lost))}};
    }
    bool resource_fault=(resources_["cpu_percent"].is_number() && resources_["cpu_percent"].get<double>()>95) || (resources_["temperature_c"].is_number() && resources_["temperature_c"].get<double>()>85) || (resources_["voltage_v"].is_number() && resources_["voltage_v"].get<double>()<10.5);
    static bool previous=false;
    if(resource_fault!=previous) {send(faults_,{{"stamp_wall_ns",data["stamp_wall_ns"]},{"type","RESOURCE"},{"resources",resources_},{"recovered",!resource_fault}}); previous=resource_fault;}
    send(metrics_,data);
  }
public:
  Aggregator():Node("dashboard_aggregator") {
    declare_parameter("topic_patterns",std::vector<std::string>{"/perception/*","/navigation/*","/control/*","/hw/*","/task/state"});
    declare_parameter("task_topic","/task/state"); declare_parameter("min_hz",5.0); declare_parameter("timeout_s",0.65);
    declare_parameter("topic_min_hz_json",std::string("{\"/hw/*\":1.0,\"/task/state\":0.0,\"/perception/model_state\":0.0}"));
    validation_=add_on_set_parameters_callback([](const std::vector<rclcpp::Parameter>& parameters){
      rcl_interfaces::msg::SetParametersResult result; result.successful=true;
      try { for(const auto& p:parameters) {
        if(p.get_name()=="topic_min_hz_json") {auto j=Json::parse(p.as_string()); if(!j.is_object()) throw std::runtime_error("Thresholds must be object"); for(auto& [k,v]:j.items()) if(!v.is_number() || v.get<double>()<0) throw std::runtime_error("Invalid threshold");}
        if(p.get_name()=="topic_patterns" && p.as_string_array().size()>64) throw std::runtime_error("At most 64 patterns");
        if((p.get_name()=="min_hz" || p.get_name()=="timeout_s") && p.as_double()<=0) throw std::runtime_error("Positive rate/timeout required");
      }} catch(const std::exception& e) {result.successful=false; result.reason=e.what();} return result;
    });
    metrics_=create_publisher<Message>("/dashboard/metrics",10); faults_=create_publisher<Message>("/dashboard/faults",100); task_=create_publisher<Message>("/dashboard/task_state",10);
    discovery_=create_wall_timer(std::chrono::milliseconds(500),[this]{discover();});
    timer_=create_wall_timer(std::chrono::milliseconds(100),[this]{tick();});
  }
};
int main(int argc,char** argv) {rclcpp::init(argc,argv); rclcpp::spin(std::make_shared<Aggregator>()); rclcpp::shutdown();}
