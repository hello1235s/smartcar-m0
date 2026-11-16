import hashlib
import json
from pathlib import Path
import tarfile
ROOT=Path(__file__).resolve().parents[1]; files=[]
for base in ['M1','M3','M5','M6','evidence','preparation-logs']:
    for f in (ROOT/base).rglob('*'):
        if not f.is_file(): continue
        relative=f.relative_to(ROOT); parts=relative.parts
        if any(p in parts for p in ['__pycache__','.pytest_cache','baseline_package']): continue
        if f.name.endswith('debug.onnx'): continue
        if base in ['evidence','preparation-logs'] or any(p in parts for p in ['results','maps','models','experiments','runs','test_assets','config']) or str(relative)=='M3/M3-4/report.md': files.append(f)
with tarfile.open('/tmp/smartcar_generated_evidence.tar.gz','w:gz') as archive:
    for f in files: archive.add(f,arcname=str(f.relative_to(ROOT)),recursive=False)
print(json.dumps(dict(files=len(files),archive_bytes=Path('/tmp/smartcar_generated_evidence.tar.gz').stat().st_size)))
