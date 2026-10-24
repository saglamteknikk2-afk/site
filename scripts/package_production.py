#!/usr/bin/env python3
"""Create a deterministic ZIP whose top level is the production webroot."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

def package(source: Path, output: Path) -> list[str]:
    source=source.resolve(); output=output.resolve()
    if source==output or source in output.parents:
        raise ValueError('Production ZIP must be written outside its source webroot')
    names=[]
    for path in sorted(source.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(source)
        if path.is_symlink() or any(p in {'private','_private','templates','.git'} for p in rel.parts) or path.suffix.lower() in {'.db','.sqlite','.sqlite3','.log','.env'} or path.name.startswith('.env'):
            raise ValueError('Private/runtime file in production package: '+rel.as_posix())
        names.append(rel.as_posix())
    if 'index.html' not in names or 'api.php' not in names:
        raise ValueError('Expected production index.html and api.php at package root')
    info_path=source/'build-info.json'
    if not info_path.is_file(): raise ValueError('Missing build-info.json; rebuild before packaging')
    build_info=json.loads(info_path.read_text())
    digest=hashlib.sha256()
    for name in sorted(n for n in names if n!='build-info.json'):
        digest.update(name.encode()+b'\0'+hashlib.sha256((source/name).read_bytes()).digest())
    if digest.hexdigest()!=build_info.get('content_sha256'):
        raise ValueError('Published file bytes do not match build-info.json; rebuild before packaging')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in names:
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            archive.writestr(info,(source/name).read_bytes())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP integrity failed')
    zip_sha256=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(output.name+'.sha256').write_text(zip_sha256+'  '+output.name+'\n')
    output.with_name(output.name+'.json').write_text(json.dumps({'zip_file':output.name,'zip_sha256':zip_sha256,'files':len(names),'bytes':output.stat().st_size,'content_sha256':build_info['content_sha256'],'source_archive_sha256':build_info['archive_sha256']},ensure_ascii=False,indent=2)+'\n')
    return names

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();names=package(a.source.resolve(),a.output.resolve());print(f'Packaged {len(names)} files with index.html and api.php at ZIP root.')
