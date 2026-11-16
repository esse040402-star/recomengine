import json, os, tempfile
from pathlib import Path

def write_json(path, data):
    """Atomic local replacement; no DB writes or network access."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
            temp=Path(f.name);json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
        os.replace(temp,path)
    finally:
        if temp and temp.exists():temp.unlink()

if __name__=='__main__':
    from .local_web import main
    raise SystemExit(main())
