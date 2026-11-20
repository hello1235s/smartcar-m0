"""Preserve standard trinary PGM labels when its YAML is loaded again."""
import hashlib
from pathlib import Path
import yaml


def normalize_trinary_yaml(path):
    path=Path(path); metadata=yaml.safe_load(path.read_text())
    if metadata.get('mode','trinary')!='trinary' or metadata.get('negate',0)!=0:
        raise ValueError('Expected the standard, non-negated trinary map_saver output')
    image=path.parent/metadata['image']; digest=hashlib.sha256(image.read_bytes()).hexdigest()
    old=metadata['free_thresh']; metadata['free_thresh']=.196
    path.write_text(yaml.safe_dump(metadata,sort_keys=False))
    if hashlib.sha256(image.read_bytes()).hexdigest()!=digest: raise RuntimeError('Map image must never be modified')
    return dict(old_free_thresh=old,new_free_thresh=.196,unknown_gray=205,
                unknown_occupancy=1.-205./255.,image_sha256_unchanged=digest,
                reason='Gray205 must remain between free and occupied thresholds, rather than becoming free during reload')
