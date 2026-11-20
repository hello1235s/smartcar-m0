"""Use a project-local official ROS middleware install for M3 Nav2 only."""
import os
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path


def configure_tf2(root):
    root=Path(root).resolve()
    prefix=root/'vendor/m3-dds/opt/ros/humble'
    library=prefix/'lib/libtf2.so'
    if not library.is_file():
        raise RuntimeError('M3 TF2 fix is missing. Run: bash scripts/install_m3_runtime.sh')
    version=ET.parse(prefix/'share/tf2/package.xml').findtext('version')
    if version!='0.25.24': raise RuntimeError('Unqualified M3 TF2 core: '+str(version))
    libraries=[str(prefix/'lib'),str(prefix/'lib/x86_64-linux-gnu')]
    libraries.extend(filter(None,os.environ.get('LD_LIBRARY_PATH','').split(':')))
    os.environ['LD_LIBRARY_PATH']=':'.join(dict.fromkeys(libraries))
    os.environ['AMENT_PREFIX_PATH']=str(prefix)+':'+os.environ.get('AMENT_PREFIX_PATH','')
    return dict(tf2_core_version=version,tf2_core_library=str(library),
                tf2_core_library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
                tf2_scope='Project-local M3 only; system TF2 and M1 unchanged')


def configure(root):
    root=Path(root).resolve()
    runtime=configure_tf2(root)
    prefix=root/'vendor/m3-dds/opt/ros/humble'
    if not (prefix/'lib/librmw_cyclonedds_cpp.so').is_file():
        raise RuntimeError('M3 navigation middleware is missing. Run: bash scripts/install_m3_runtime.sh')
    os.environ['RMW_IMPLEMENTATION']='rmw_cyclonedds_cpp'
    os.environ['CYCLONEDDS_URI']=(root/'M3/M3-3/config/cyclone_local.xml').as_uri()
    return dict(**runtime,rmw_implementation='rmw_cyclonedds_cpp',dds_transport='UDPv4 loopback unicast',
                dds_scope='M3 navigation on this host only',dds_prefix=str(prefix),
                cyclone_config=str(root/'M3/M3-3/config/cyclone_local.xml'))


def inspect_native_tf2(launch_pid,root):
    """Read only our launched descendants' library maps before cleanup."""
    from process_cleanup import identity
    table={int(p.name):identity(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()}
    owned={launch_pid}; previous=set()
    while previous!=owned:
        previous=set(owned)
        owned.update(pid for pid,value in table.items() if value and value[0] in owned)
    expected=(Path(root)/'vendor/m3-dds/opt/ros/humble/lib/libtf2.so').resolve()
    nodes={}
    for pid in owned:
        try:
            folder=Path('/proc')/str(pid)
            command=folder.joinpath('cmdline').read_bytes().split(b'\0')[0].decode()
            name=Path(command).name
            if name not in ['controller_server','planner_server','amcl']: continue
            paths={line.split()[-1] for line in folder.joinpath('maps').read_text().splitlines() if 'libtf2.so' in line}
            nodes[name]=dict(pid=pid,loaded_libraries=sorted(paths),expected_library_loaded=bool(paths) and all(Path(path).resolve()==expected for path in paths))
        except (FileNotFoundError,PermissionError,ProcessLookupError): continue
    return dict(status='PASS' if len(nodes)==3 and all(n['expected_library_loaded'] for n in nodes.values()) else 'FAIL',nodes=nodes,expected_library=str(expected))
