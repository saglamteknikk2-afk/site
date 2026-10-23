#!/usr/bin/env python3
"""Create a deterministic ZIP whose top level is the production webroot."""
import argparse
from pathlib import Path
import zipfile

def package(source: Path, output: Path) -> list[str]:
    names=[]
    for path in sorted(source.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(source)
        if path.is_symlink() or any(p in {'private','_private','templates','.git'} for p in rel.parts) or path.suffix.lower() in {'.db','.sqlite','.sqlite3','.log','.env'} or path.name.startswith('.env'):
            raise ValueError('Private/runtime file in production package: '+rel.as_posix())
        names.append(rel.as_posix())
    if 'index.html' not in names or 'api.php' not in names:
        raise ValueError('Expected production index.html and api.php at package root')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in names:
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            archive.writestr(info,(source/name).read_bytes())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP integrity failed')
    return names

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();names=package(a.source.resolve(),a.output.resolve());print(f'Packaged {len(names)} files with index.html and api.php at ZIP root.')
