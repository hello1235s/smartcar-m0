import argparse
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path
import cv2
import numpy as np
import yaml
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'M6/common'))
from runtime import Detector,preprocess


VERIFY='''import hashlib,importlib.util,json,sys
from pathlib import Path
import cv2,numpy as np
from runtime import Detector,preprocess
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
for file,digest in manifest['sha256'].items():
    assert hashlib.sha256((root/file).read_bytes()).hexdigest()==digest,'Hash mismatch: '+file
assert importlib.util.find_spec('torch') is None,'Use a clean inference-only environment without torch'
assert importlib.util.find_spec('tensorflow') is None,'Use a clean inference-only environment without tensorflow'
image=cv2.imdecode(np.fromfile(str(root/'sample.jpg'),np.uint8),cv2.IMREAD_COLOR); tensor=preprocess(image)[0]
actual=Detector(root/'models/best_fp32.onnx').raw(tensor); expected=np.load(root/'expected.npy')
cos=float(np.dot(actual.ravel(),expected.ravel())/(np.linalg.norm(actual)*np.linalg.norm(expected)))
assert actual.shape==(1,84,2100) and cos>.99 and np.isfinite(actual).all()
print(json.dumps(dict(status='PASS',cosine_similarity=cos,max_absolute_error=float(np.abs(actual-expected).max()),shape=list(actual.shape),training_frameworks_installed=False,python=sys.version,platform=sys.platform),indent=2))
'''


def main():
    p=argparse.ArgumentParser(); p.add_argument('--scene',required=True); p.add_argument('--model',required=True); p.add_argument('--sample',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); package=out/'baseline_package'; package.mkdir(exist_ok=True); (package/'models').mkdir(exist_ok=True)
    params=yaml.safe_load(Path(a.scene).read_text()); (package/'baseline.json').write_text(json.dumps(params,indent=2))
    shutil.copy2(a.model,package/'models/best_fp32.onnx'); shutil.copy2(a.sample,package/'sample.jpg'); shutil.copy2(ROOT/'M6/common/runtime.py',package/'runtime.py')
    detector=Detector(a.model); tensor=preprocess(cv2.imread(a.sample))[0]; np.save(package/'expected.npy',detector.raw(tensor))
    (package/'verify_baseline.py').write_text(VERIFY); (package/'verify_baseline.sh').write_text('#!/usr/bin/env bash\nset -e\ncd "$(dirname "$0")"\n"${PYTHON:-python3}" verify_baseline.py\n')
    (package/'requirements.lock').write_text('numpy==1.26.4\nonnxruntime==1.20.1\nopencv-python-headless==4.10.0.84\n')
    (package/'README.md').write_text('# Inference baseline\nCreate Python 3.10/3.11 venv, install requirements.lock, then run `python verify_baseline.py` (Windows/Linux) or `bash verify_baseline.sh`. Verifies file hashes, output shape, finite values, CosSim > .99 and no installed torch/tensorflow. Does not assert race mAP, Orin FPS, CUDA Graph or camera throughput. Indoor sample originates from real K230 USB.\n')
    manifest=dict(scope='functional inference baseline; race/Orin acceptance pending',thresholds=dict(cosine_similarity_min=.99,shape=[1,84,2100]),sha256={str(f.relative_to(package)):hashlib.sha256(f.read_bytes()).hexdigest() for f in package.rglob('*') if f.is_file() and f.name!='manifest.json' and '__pycache__' not in f.parts})
    (package/'manifest.json').write_text(json.dumps(manifest,indent=2))
    with tarfile.open(out/'baseline_package.tar.gz','w:gz') as archive: archive.add(package,arcname='baseline_package')
    print(out/'baseline_package.tar.gz')


if __name__=='__main__': main()
