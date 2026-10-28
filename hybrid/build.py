#!/usr/bin/env python3
"""Reproducible hybrid content build from the exact uploaded a1 file tree."""
from pathlib import Path
import argparse, hashlib, json, os, sys, zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parent
sys.path.insert(0,str(REPO/'preview-release'))
from source import load_source
from publishing import retire_offers, apply_publication_policy, preview_files, retain_review
from route_correction import correct_routes

def stamp(files, mode, source, metrics):
    files.pop('build-info.json',None)
    digest=hashlib.sha256()
    for name in sorted(files):digest.update(name.encode()+b'\0'+hashlib.sha256(files[name]).digest())
    info={'schema_version':2,'release':'hybrid-matrix','mode':mode,'base_path':'/site' if mode=='preview' else '/',
          **source,'archive_sha256_kind':'uploaded-a1-archive','content_sha256':digest.hexdigest(),
          'files':len(files),'visitor_pages':sum(n.endswith('.html') and not n.startswith(('assets/','inceleme/','google','yandex')) for n in files),
          'source_commit':os.environ.get('GITHUB_SHA','local'),'metrics':metrics,
          'live_backend_delivery_verified':False,'google_indexing_guaranteed':False}
    files['build-info.json']=(json.dumps(info,ensure_ascii=False,indent=2)+'\n').encode()
    return info

def build(mode='production', source=None):
    files,provenance=load_source(REPO,source)
    from regions import apply_regions
    from hubs import apply_hubs
    from matching import apply_matching
    from semantics import apply_semantics
    from performance import apply_performance
    from retired_copy import correct_retired_copy
    from reporting import add_report
    from cache_versions import version_assets
    from editorial_audit import audit_editorial
    from service_editorial import apply_services, audit_services
    from redirects import apply_redirects
    from service_handoff import apply_service_handoff
    metrics={}
    metrics['service_scope']=retire_offers(files)
    metrics['retired_offer_copy']=correct_retired_copy(files)
    metrics['relative_route_base']=correct_routes(files)
    metrics['matching']=apply_matching(files)
    metrics['regions']=apply_regions(files)
    metrics['service_editorial']=apply_services(files)
    metrics['service_handoff']=apply_service_handoff(files)
    metrics['redirects']=apply_redirects(files)
    metrics['hubs']=apply_hubs(files)
    metrics['publication_policy']=apply_publication_policy(files)
    metrics['semantics']=apply_semantics(files)
    metrics['editorial']=audit_editorial(files=files)
    metrics['combined_editorial']=audit_services(files)
    metrics['performance']=apply_performance(files)
    add_report(files,REPO,metrics,provenance)
    from index_review import add_index_review
    metrics['index_review']=add_index_review(files,REPO,metrics)
    # Modules are responsible for indexable HTML, not runtime-only SEO text.
    if mode=='preview':
        files,metrics['preview']=preview_files(files,REPO)
        retain_review(files,REPO)
    metrics['asset_cache']=version_assets(files)
    stamp(files,mode,provenance,metrics)
    return files,metrics,provenance

def write_files(files,output):
    output.mkdir(parents=True,exist_ok=True)
    expected=set(files)
    for existing in output.rglob('*'):
        if existing.is_file() and existing.relative_to(output).as_posix() not in expected:existing.unlink()
    for name,data in files.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def package(files,target):
    if any(Path(n).suffix in {'.db','.sqlite','.sqlite3','.log','.env'} or any(p in {'private','_private','.git'} for p in Path(n).parts) for n in files):
        raise ValueError('Runtime/private files must not be packaged.')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(files):
            item=zipfile.ZipInfo(name,(2026,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16
            archive.writestr(item,files[name])
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
    result={'zip_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'files':len(files)}
    target.with_suffix(target.suffix+'.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['production','preview'],default='production');p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--zip',type=Path)
    args=p.parse_args();files,metrics,provenance=build(args.mode,args.source);write_files(files,args.output)
    print(json.dumps({'mode':args.mode,'source':provenance,'files':len(files),'metrics':metrics,'zip':package(files,args.zip) if args.zip else None},ensure_ascii=False,indent=2))
