#include <karto_sdk/Mapper.h>
#include <nlohmann/json.hpp>
#include <cmath>
#include <iostream>
#include <fstream>
int main(int argc,char**argv) {
  if(argc!=2) { std::cerr<<"Usage: inspect_posegraph <file.posegraph>\n"; return 2; }
  if(!std::ifstream(argv[1],std::ios::binary)) { std::cerr<<"Cannot read posegraph file: "<<argv[1]<<"\n"; return 2; }
  try {
  karto::Mapper mapper; mapper.LoadFromFile(argv[1]); auto* graph=mapper.GetGraph();
  nlohmann::json edges=nlohmann::json::array(); size_t vertices=0;
  for(const auto& item:graph->GetVertices()) vertices+=item.second.size();
  for(const auto* edge:graph->GetEdges()) {
    auto* source=edge->GetSource()->GetObject(); auto* target=edge->GetTarget()->GetObject();
    int a=source->GetStateId(),b=target->GetStateId(); auto p=source->GetCorrectedPose(),q=target->GetCorrectedPose();
    if(std::abs(a-b)>20) edges.push_back({{"source_id",a},{"target_id",b},{"scan_time_gap_s",std::abs(source->GetTime()-target->GetTime())},{"corrected_distance_m",std::hypot(p.GetX()-q.GetX(),p.GetY()-q.GetY())}});
  }
  std::cout<<"POSEGRAPH_JSON "<<nlohmann::json({{"vertices",vertices},{"edges",graph->GetEdges().size()},{"nonlocal_edges_id_gap_gt20",edges}}).dump()<<std::endl;
  } catch(const std::exception& error) { std::cerr<<"Posegraph read failed: "<<error.what()<<"\n"; return 1; }
}
