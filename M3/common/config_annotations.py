"""Explain each changed YAML leaf without changing its configured value."""
MISSING='<not present in original Humble YAML>'
REASONS={
    'desired_linear_vel':'Nominal cruise .32m/s balances traversal time, clearance and command variation; aggressive comparison is .65m/s.',
    'min_turning_radius':'Clamp curvature before prediction; .60m exceeds the car geometric inner-wheel limit of about .575m.',
    'terminal_extension':'Virtual .45m heading reference improves terminal alignment; ControllerServer still checks the original goal.',
    'terminal_slowdown_distance':'Start actual-goal speed limiting within .60m; the virtual reference must not cause overshoot.',
    'terminal_speed_gain':'Inside the terminal region cap |v| by max(approach floor, .7*distance), preserving an already lower safe speed.',
    'lookahead_dist':'Nominal reference distance; velocity scaling and min/max bounds determine the actual carrot.',
    'min_lookahead_dist':'Lower bound avoids chasing laser/localization noise at near-zero speed.',
    'max_lookahead_dist':'Upper bound limits corner cutting in the narrow ring corridors.',
    'lookahead_time':'Scale the reference distance from measured forward/reverse speed before clamping to .30-.65m.',
    'use_velocity_scaled_lookahead_dist':'Adapt tracking distance to measured speed; fixed short lookahead is reserved for the aggressive comparison.',
    'max_allowed_time_to_collision_up_to_carrot':'Predict feasible chassis arcs for up to2s, bounded by the current tracking/stopping region.',
    'use_collision_detection':'Retain footprint checks on the bounded command; never rely only on bridge clipping.',
    'min_approach_linear_velocity':'A .035m/s floor prevents numerical stall; the terminal cap never accelerates a lower safe command.',
    'approach_velocity_scaling_dist':'Keep inherited RPP approach regulation; additional terminal regulation uses the actual goal, not the virtual endpoint.',
    'use_regulated_linear_velocity_scaling':'Reduce cruise speed when reference curvature becomes tight.',
    'use_cost_regulated_linear_velocity_scaling':'Reduce speed near obstacle inflation costs.',
    'regulated_linear_scaling_min_radius':'Begin speed regulation before reaching the .60m physical curvature bound.',
    'regulated_linear_scaling_min_speed':'Inherited regulation floor; terminal approach may command lower speeds.',
    'cost_scaling_dist':'Proximity band for cost-based speed regulation, separate from footprint collision checks.',
    'cost_scaling_gain':'Keep cost regulation proportional rather than adding an unmeasured extra gain.',
    'inflation_cost_scaling_factor':'Match the actual costmap inflation-layer decay factor.',
    'use_rotate_to_heading':'False: an Ackermann chassis cannot execute an in-place rotation.',
    'allow_reversing':'True: match Reeds-Shepp path inversions and the negative smoother velocity bound.',
    'max_angular_accel':'Inherited rotate-only RPP parameter is inactive in this Ackermann branch; the external smoother bounds angular acceleration.',
    'xy_goal_tolerance':'Internal .05m leaves map-grid and localization margin inside the independent .15m truth limit.',
    'yaw_goal_tolerance':'Internal .10rad leaves margin inside the independent .20rad truth limit.',
    'stateful':'False documents joint XY/yaw checking; the custom checker always checks both and rejects invalid poses.',
    'minimum_turning_radius':'Hybrid-A* radius .65m leaves margin above controller/chassis .60m bound.',
    'motion_model_for_search':'Reeds-Shepp explicitly supports feasible forward/reverse car maneuvers.',
    'angle_quantization_bins':'72 heading bins give5deg search resolution; this is not a precision claim.',
    'tolerance':'Planner fallback search tolerance is separate from the strict physical-goal validation; an approximate endpoint cannot pass if truth limits fail.',
    'footprint_padding':'Add .08m planning margin around the unchanged physical envelope; independent evaluation does not shrink its footprint.',
    'inflation_radius':'Soft .45m cost field improves corner clearance without treating the full radius as a lethal band.',
    'failure_tolerance':'Allow2s of transient unavailable local control while periodic global replanning can respond.',
    'required_movement_radius':'Slow .15m progress remains valid during obstacle approach.',
    'movement_time_allowance':'Allow20s to make measurable progress; the external trial timeout remains bounded.',
}


def expand_changes(original,current,broad_notes):
    result=[]
    def walk(before,after,path):
        if isinstance(after,dict):
            old=before if isinstance(before,dict) else {}
            for key,value in after.items(): walk(old.get(key,MISSING),value,path+[key])
        elif before!=after:
            name='/'.join(path)
            matches=[n for n in broad_notes if name==n['parameter'] or name.startswith(n['parameter']+'/')]
            broad=max(matches,key=lambda n:len(n['parameter']))['reason'] if matches else 'Retain the explicit car/navigation configuration difference from the original Humble snapshot.'
            reason=REASONS.get(path[-1],broad)
            result.append(dict(parameter=name,old=before,new=after,reason=reason))
    walk(original,current,[])
    return result
