"""Independent geometry/goal metrics; evaluation data never controls the car."""
import math


def wrap(angle): return math.atan2(math.sin(angle), math.cos(angle))


def footprint(pose, rear_reference=True, width=.26):
    x,y,yaw=pose
    center=.14 if rear_reference else 0.
    c,s=math.cos(yaw),math.sin(yaw)
    return [(x+c*px-s*py,y+s*px+c*py) for px,py in
            [(center-.225,-width/2),(center+.225,-width/2),(center+.225,width/2),(center-.225,width/2)]]


def rectangle(x,y,length,width):
    return [(x-length/2,y-width/2),(x+length/2,y-width/2),(x+length/2,y+width/2),(x-length/2,y+width/2)]


def point_segment_distance(point,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0.,min(1.,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/max(1e-12,dx*dx+dy*dy)))
    return math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy)


def clearance(a,b):
    """Signed convex-polygon separation: Euclidean gap, or negative SAT penetration."""
    separated=False; penetration=float('inf')
    for poly in [a,b]:
        for p,q in zip(poly,poly[1:]+poly[:1]):
            dx,dy=q[0]-p[0],q[1]-p[1]; length=math.hypot(dx,dy)
            if length<1e-10: continue
            axis=(-dy/length,dx/length)
            aa=[v[0]*axis[0]+v[1]*axis[1] for v in a]
            bb=[v[0]*axis[0]+v[1]*axis[1] for v in b]
            if min(aa)>max(bb) or min(bb)>max(aa): separated=True
            penetration=min(penetration,max(aa)-min(bb),max(bb)-min(aa))
    if not separated: return -max(0.,penetration)
    return min([point_segment_distance(p,u,v) for p in a for u,v in zip(b,b[1:]+b[:1])]+
               [point_segment_distance(p,u,v) for p in b for u,v in zip(a,a[1:]+a[:1])])


def scene_obstacles():
    data=[('south_wall',6,-.1,12.4,.2),('north_wall',6,8.1,12.4,.2),
          ('west_wall',-.1,4,.2,8),('east_wall',12.1,4,.2,8),('inner_island',6,4,8,4),
          ('narrow_door_lower',6,.25,.15,.5),('narrow_door_upper',6,1.75,.15,.5)]
    return [(name,rectangle(x,y,l,w)) for name,x,y,l,w in data]


def world_goal(goal,origin=(1.,1.,0.)):
    c,s=math.cos(origin[2]),math.sin(origin[2])
    return origin[0]+c*goal[0]-s*goal[1],origin[1]+s*goal[0]+c*goal[1],wrap(origin[2]+goal[2])


def goal_errors(pose,goal):
    return dict(position_m=math.hypot(pose[0]-goal[0],pose[1]-goal[1]),yaw_rad=abs(wrap(pose[2]-goal[2])))
