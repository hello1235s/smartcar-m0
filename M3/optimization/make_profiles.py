"""Generate controlled profiles; reverse support changes the full command chain."""
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
base=yaml.safe_load((ROOT/'M3/M3-3/config/nav2_params.yaml').read_text())
folder=ROOT/'M3/optimization/config'; folder.mkdir(parents=True,exist_ok=True)
for name in ['strict_forward','strict_reverse']:
    data=yaml.safe_load(yaml.safe_dump(base))
    controller=data['controller_server']['ros__parameters']
    controller['general_goal_checker']['stateful']=False
    reverse=name=='strict_reverse'
    data['planner_server']['ros__parameters']['GridBased']['motion_model_for_search']='REEDS_SHEPP' if reverse else 'DUBIN'
    controller['FollowPath']['allow_reversing']=reverse
    controller['FollowPath']['use_rotate_to_heading']=False
    data['velocity_smoother']['ros__parameters']['min_velocity']=[-.20 if reverse else 0.,0.,-.9]
    (folder/(name+'.yaml')).write_text(yaml.safe_dump(data,sort_keys=False))
    print(folder/(name+'.yaml'))
