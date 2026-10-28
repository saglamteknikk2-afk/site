"""Include the public production download in the final preview file manifest."""
from pathlib import Path
import hashlib,json,sys

root=Path(sys.argv[1]);metadata=root/'build-info.json';info=json.loads(metadata.read_text());digest=hashlib.sha256()
files=sorted((p.relative_to(root).as_posix(),p) for p in root.rglob('*') if p.is_file() and p!=metadata)
for name,path in files:digest.update(name.encode()+b'\0'+hashlib.sha256(path.read_bytes()).digest())
info.update(content_sha256=digest.hexdigest(),files=len(files))
metadata.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
