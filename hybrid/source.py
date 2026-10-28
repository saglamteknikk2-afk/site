"""Reproduce the exact uploaded a1 file tree without duplicating shared assets."""
from pathlib import Path
import gzip, hashlib, json, zipfile

def load_source(repo: Path, source: Path | None = None) -> tuple[dict[str, bytes], dict]:
    patch = json.loads(gzip.decompress((repo/'hybrid/data/base-a1.patch.json.gz').read_bytes()))
    if source:
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != patch['uploaded_a1_sha256']:
            raise ValueError('The source archive differs from the reviewed a1 upload.')
        archive = source
    else:
        archive = repo/'saglamkombiklima-seo.zip'
        if hashlib.sha256(archive.read_bytes()).hexdigest() != patch['upstream_archive_sha256']:
            raise ValueError('The shared asset archive changed; source reconstruction stopped.')
    with zipfile.ZipFile(archive) as z:
        files = {}
        for item in z.infolist():
            if item.is_dir(): continue
            name = item.filename
            if name.startswith('/') or '..' in Path(name).parts or (item.external_attr>>16)&0o170000 == 0o120000:
                raise ValueError('Unsafe source archive entry.')
            files[name] = z.read(item)
    if not source:
        for name in patch['remove']:files.pop(name,None)
        files.update({name:text.encode('utf-8') for name,text in patch['replace'].items()})
    actual = {name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    if actual != patch['files']:
        raise ValueError('Reconstructed file tree does not match the uploaded a1 archive.')
    tree = hashlib.sha256()
    for name in sorted(files):tree.update(name.encode()+b'\0'+hashlib.sha256(files[name]).digest())
    return files, {'archive_sha256':patch['uploaded_a1_sha256'],
                   'archive_bytes':patch['uploaded_a1_bytes'],'file_tree_sha256':tree.hexdigest(),
                   'files':len(files),'all_uploaded_file_bytes_verified':True}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();files,meta=load_source(Path(__file__).resolve().parents[1])
    for name,data in files.items():
        path=args.output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print(json.dumps(meta,ensure_ascii=False))
