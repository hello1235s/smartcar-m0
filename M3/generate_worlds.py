from pathlib import Path

ROOT = Path(__file__).resolve().parent


def block(name, x, y, sx, sy, height=1.0):
    return '''<model name="%s"><static>true</static><pose>%s %s %s 0 0 0</pose><link name="body"><collision name="collision"><geometry><box><size>%s %s %s</size></box></geometry></collision><visual name="visual"><geometry><box><size>%s %s %s</size></box></geometry><material><ambient>0.6 0.65 0.7 1</ambient></material></visual></link></model>''' % (name,x,y,height/2,sx,sy,height,sx,sy,height)


def world(blocks):
    return '''<?xml version="1.0"?><sdf version="1.6"><world name="smartcar_training">
    <physics name="default" type="ode"><max_step_size>0.002</max_step_size><real_time_update_rate>500</real_time_update_rate><ode><solver><type>quick</type><iters>80</iters></solver></ode></physics>
    <gravity>0 0 -9.81</gravity><light name="sun" type="directional"><cast_shadows>false</cast_shadows><diffuse>0.8 0.8 0.8 1</diffuse><direction>-0.5 -0.5 -1</direction></light>
    <model name="ground"><static>true</static><link name="plane"><collision name="ground"><geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry></collision><visual name="ground"><geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry></visual></link></model>
    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so"><ros><namespace>/gazebo</namespace></ros><update_rate>50</update_rate></plugin>
    %s</world></sdf>''' % '\n'.join(blocks)


def main():
    square = world([])
    scene = world([block('south_wall',6,-0.1,12.4,0.2), block('north_wall',6,8.1,12.4,0.2),
                   block('west_wall',-0.1,4,0.2,8.0), block('east_wall',12.1,4,0.2,8.0),
                   block('inner_island',6,4,8,4), block('narrow_door_lower',6,0.25,0.15,0.5),
                   block('narrow_door_upper',6,1.75,0.15,0.5)])
    package = ROOT/'M3-1/src/smart_car_description/worlds'
    for directory in [package, ROOT/'M3-1/worlds', ROOT/'M3-2/worlds']:
        directory.mkdir(parents=True, exist_ok=True)
    (package/'square.world').write_text(square)
    (package/'scene.world').write_text(scene)
    (ROOT/'M3-1/worlds/square.world').write_text(square)
    (ROOT/'M3-2/worlds/scene.world').write_text(scene)


if __name__ == '__main__':
    main()
