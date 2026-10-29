"""Versioned runtime fixes layered over the byte-verified uploaded source."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parent

def apply_runtime_updates(files):
    changed=[]
    for source in sorted((ROOT/'runtime').rglob('*')):
        if not source.is_file():continue
        name=source.relative_to(ROOT/'runtime').as_posix()
        if source.suffix not in {'.php','.js','.css'} or any(p in {'private','.git','..'} for p in source.parts):
            raise ValueError('Unexpected runtime override: '+name)
        data=source.read_bytes();files[name]=data
        changed.append({'path':name,'sha256':hashlib.sha256(data).hexdigest()})
    return {'files':changed,'private_data_replaced':False}
