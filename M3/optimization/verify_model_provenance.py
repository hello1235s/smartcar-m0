"""Check original source provenance and unchanged expanded physical geometry."""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
package=ROOT/'M3/M3-1/src/smart_car_description'
expected={
    'urdf/smart_car.original.urdf.xacro':'e4e7289d2acb4da7cd596a41d0c7620453cef23a6663354e674f3032019a93f5',
    'config/ackermann_controllers.original.yaml':'d5406a080f99a6cc7a794312c03b66c88b8edb45d7527ba61cb295d4f9571d49'}
for name,digest in expected.items():
    assert hashlib.sha256((package/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
def expand(name):
    return ET.fromstring(subprocess.check_output(['xacro',str(package/'urdf'/name)]))
def canonical(node):
    return node.tag,tuple(sorted(node.attrib.items())),' '.join((node.text or '').split()),tuple(canonical(child) for child in node)
old=expand('smart_car.original.urdf.xacro'); current=expand('smart_car.urdf.xacro')
counts={}
for tag in ['link','joint']:
    before={node.attrib['name']:node for node in old.findall(tag)}
    after={node.attrib['name']:node for node in current.findall(tag)}
    assert set(before)==set(after),(tag,'names changed')
    for name,node in before.items():
        if tag=='joint' and name=='base_footprint_joint': continue
        assert canonical(node)==canonical(after[name]),(tag,name,'physical definition changed')
    counts[tag]=len(before)
joint=current.find("joint[@name='base_footprint_joint']")
offset=[float(x) for x in joint.find('origin').attrib['xyz'].split()]
assert offset==[.14,0.,.05]
result=dict(status='PASS',reference_repository='https://github.com/Blake-John/22SmartCar',
    reference_commit='cdc8dd45296f4eaf57924c0686d861e07252905d',
    original_sha256_after_crlf_normalization=expected,expanded_physical_links_unchanged=counts['link'],
    expanded_nonreference_joints_unchanged=counts['joint']-1,
    changed_reference_joint=dict(name='base_footprint_joint',xyz_m=offset),
    scope='Link visual/collision/inertial geometry and all other joint definitions. ROS interfaces, RIGHT/LEFT controller ordering and optional disabled camera plugin are adaptations, not claimed byte-identical.')
out=ROOT/'M3/optimization/report/model_provenance.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)); print(json.dumps(result))
