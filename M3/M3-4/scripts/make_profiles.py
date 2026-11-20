"""Generate controlled RPP comparison and sequential tuning profiles."""
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[3]


def main():
    base=yaml.safe_load((ROOT/'M3/M3-3/config/nav2_params.yaml').read_text())
    folder=ROOT/'M3/M3-4/config'; folder.mkdir(exist_ok=True)
    for label in ['A','B','B_speed','B_tuned']:
        data=yaml.safe_load(yaml.safe_dump(base))
        follow=data['controller_server']['ros__parameters']['FollowPath']
        if label=='A': follow['desired_linear_vel']=.28
        if label in ['B','B_speed']:
            follow.update(desired_linear_vel=.65 if label=='B' else .32,
                          lookahead_dist=.25,min_lookahead_dist=.25,max_lookahead_dist=.25,
                          use_velocity_scaled_lookahead_dist=False,
                          max_allowed_time_to_collision_up_to_carrot=.5)
        # B -> B_speed: speed alone. B_speed -> B_tuned: lookahead policy + prediction time.
        # All profiles retain identical map, footprint, goal tolerances, planner, and reverse support.
        data['velocity_smoother']['ros__parameters']['max_velocity']=[.75,0.,1.2]
        path=folder/('planner_'+label+'_params.yaml')
        path.write_text(yaml.safe_dump(data,sort_keys=False))
        print(path)


if __name__=='__main__': main()
