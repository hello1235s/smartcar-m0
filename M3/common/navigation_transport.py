"""Use a project-local official ROS middleware install for M3 Nav2 only."""
import os
from pathlib import Path


def configure(root):
    root=Path(root).resolve()
    prefix=root/'vendor/m3-dds/opt/ros/humble'
    if not (prefix/'lib/librmw_cyclonedds_cpp.so').is_file():
        raise RuntimeError('M3 navigation middleware is missing. Run: bash scripts/install_m3_dds.sh')
    libraries=[str(prefix/'lib'),str(prefix/'lib/x86_64-linux-gnu')]
    libraries.extend(filter(None,os.environ.get('LD_LIBRARY_PATH','').split(':')))
    os.environ['LD_LIBRARY_PATH']=':'.join(dict.fromkeys(libraries))
    os.environ['AMENT_PREFIX_PATH']=str(prefix)+':'+os.environ.get('AMENT_PREFIX_PATH','')
    os.environ['RMW_IMPLEMENTATION']='rmw_cyclonedds_cpp'
    os.environ['CYCLONEDDS_URI']=(root/'M3/M3-3/config/cyclone_local.xml').as_uri()
    return dict(rmw_implementation='rmw_cyclonedds_cpp',dds_transport='UDPv4 loopback unicast',
                dds_scope='M3 navigation on this host only',dds_prefix=str(prefix),
                cyclone_config=str(root/'M3/M3-3/config/cyclone_local.xml'))
