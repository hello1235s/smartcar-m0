"""Combine complete group manifests without dropping or relabeling attempts."""
import argparse
import json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,required=True)
p.add_argument('manifests',type=Path,nargs='+')
a=p.parse_args(); result=[]
for path in a.manifests: result.extend(json.loads(path.read_text()))
labels=[r['label'] for r in result]
if len(set(labels))!=len(labels): raise ValueError('Duplicate group labels; keep candidates in separate analyses')
if any(r['returncode'] for r in result): raise ValueError('Manifest contains an infrastructure failure')
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(result,indent=2))
print('COMBINED_GROUPS',len(result),a.out)
