from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; out=ROOT/'M3/M3-1/results'; out.mkdir(exist_ok=True)
fig,ax=plt.subplots(figsize=(10,6)); ax.set(xlim=(0,10),ylim=(0,7)); ax.axis('off')
nodes={'map':(5,6),'odom':(5,4.8),'base_footprint':(5,3.5),'base_link':(5,2.1),'lidar_link':(2,0.7),'camera_link':(8,.7)}
for name,(x,y) in nodes.items(): ax.text(x,y,name,ha='center',va='center',fontsize=11,bbox=dict(boxstyle='round,pad=.6',fc='#eaf3f7',ec='#447284'))
edges=[('map','odom','DYNAMIC: slam_toolbox / AMCL\nAbsent in M3-1',True),('odom','base_footprint','DYNAMIC: Ackermann controller / wheel odometry',False),('base_footprint','base_link','STATIC: robot_state_publisher / fixed joint',False),('base_link','lidar_link','STATIC: robot_state_publisher',False),('base_link','camera_link','STATIC: robot_state_publisher',False)]
for a,b,label,dashed in edges:
    x,y=nodes[a]; xx,yy=nodes[b]; ax.annotate('',xy=(xx,yy+.23),xytext=(x,y-.23),arrowprops=dict(arrowstyle='->',color='#355d6e',linestyle='--' if dashed else '-'))
    ax.text((x+xx)/2+.12,(y+yy)/2,label,fontsize=8,ha='left',va='center')
ax.set_title('Provided car TF frames and actual publishing roles',fontsize=14); fig.tight_layout(); fig.savefig(out/'tf_tree_annotated.png',dpi=160); plt.close(fig)
