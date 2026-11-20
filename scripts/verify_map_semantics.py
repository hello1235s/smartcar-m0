"""Load the actual saved map through Nav2 and verify occupied/free/unknown labels."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
from PIL import Image
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'M3/common'))
from map_semantics import normalize_trinary_yaml
from process_cleanup import terminate_owned_tree


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--map',type=Path,default=ROOT/'M3/M3-2/maps/map.yaml')
    p.add_argument('--out',type=Path); p.add_argument('--normalize',action='store_true'); p.add_argument('--update-manifest',action='store_true')
    p.add_argument('--domain',type=int,default=222); a=p.parse_args()
    out=(a.out or ROOT/'M3/M3-2/results'/('map_semantics_'+time.strftime('%Y%m%d_%H%M%S'))).resolve(); out.mkdir(parents=True,exist_ok=False)
    path=a.map.resolve(); before=path.read_bytes(); (out/'yaml_before.yaml').write_bytes(before)
    info=yaml.safe_load(before); image=path.parent/info['image']; pixels=np.asarray(Image.open(image).convert('L'))
    counts=Counter(int(x) for x in pixels.ravel())
    if set(counts)-{0,205,254}: raise ValueError('Expected actual trinary map_saver palette 0,205,254')
    normalization=normalize_trinary_yaml(path) if a.normalize else None
    info=yaml.safe_load(path.read_text()); shutil.copy2(image,out/image.name)
    info['image']=image.name; runtime=out/'map_loaded.yaml'; runtime.write_text(yaml.safe_dump(info,sort_keys=False))
    expected={'occupied':counts[0],'unknown':counts[205],'free':counts[254]}
    os.environ.update(ROS_DOMAIN_ID=str(a.domain),FASTDDS_BUILTIN_TRANSPORTS='UDPv4')
    import rclpy
    from rclpy.node import Node
    from lifecycle_msgs.srv import ChangeState
    from nav_msgs.srv import GetMap
    env=dict(os.environ)
    log=(out/'map_server.log').open('w')
    server=subprocess.Popen(['ros2','run','nav2_map_server','map_server','--ros-args','-r','__node:=semantic_map_server',
                             '-p','yaml_filename:='+str(runtime),'-p','use_sim_time:=false'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init(); node=Node('saved_map_semantic_verifier'); report=None
    try:
        lifecycle=node.create_client(ChangeState,'/semantic_map_server/change_state')
        if not lifecycle.wait_for_service(timeout_sec=20): raise RuntimeError('Native map_server lifecycle unavailable')
        for transition in [1,3]:
            request=ChangeState.Request(); request.transition.id=transition
            future=lifecycle.call_async(request); rclpy.spin_until_future_complete(node,future,timeout_sec=15)
            if not future.done() or not future.result().success: raise RuntimeError('Native map_server lifecycle transition failed')
        deadline=time.monotonic()+15; services=[]
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            services=[name for name,types in node.get_service_names_and_types() if 'nav_msgs/srv/GetMap' in types]
            if services: break
        if len(services)!=1: raise RuntimeError('Expected exactly one isolated native GetMap service: '+str(services))
        client=node.create_client(GetMap,services[0])
        if not client.wait_for_service(timeout_sec=10): raise RuntimeError('Native GetMap service unavailable')
        future=client.call_async(GetMap.Request()); rclpy.spin_until_future_complete(node,future,timeout_sec=15)
        if not future.done(): raise RuntimeError('Native GetMap request timed out')
        message=future.result().map; actual=Counter(int(x) for x in message.data)
        observed={'occupied':actual[100],'unknown':actual[-1],'free':actual[0]}
        report=dict(status='PASS' if expected==observed else 'FAIL',source_yaml=str(path.relative_to(ROOT)),
                    source_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                    source_yaml_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    expected_from_actual_pgm=expected,observed_from_native_nav2_getmap=observed,
                    other_values={str(k):v for k,v in actual.items() if k not in [-1,0,100]},
                    normalization=normalization,native_getmap_service=services[0],free_thresh=info['free_thresh'],
                    image_pixels_unchanged=True)
        (out/'roundtrip.json').write_text(json.dumps(report,indent=2))
        if expected!=observed or report['other_values']: raise RuntimeError('Saved map labels changed after native Nav2 reload: '+str(report))
        if a.update_manifest:
            manifest_path=path.parent/'map_manifest.json'; manifest=json.loads(manifest_path.read_text())
            manifest.update(map_yaml_sha256=report['source_yaml_sha256'],semantic_roundtrip=dict(report=str((out/'roundtrip.json').relative_to(ROOT)),**report))
            manifest_path.write_text(json.dumps(manifest,indent=2))
        print('MAP_SEMANTICS_PASS '+json.dumps(report),flush=True)
    finally:
        node.destroy_node(); rclpy.shutdown(); terminate_owned_tree(server); log.close()
        if report is None: (out/'verification_error.json').write_text(json.dumps(dict(status='FAIL',reason='Native loader verification failed before response')))


if __name__=='__main__': main()
