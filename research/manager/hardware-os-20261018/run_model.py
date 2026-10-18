"""Bounded evidence capture for the architecture arithmetic only."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent


def limits():
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16<<20,16<<20))


def main():
    out=Path(sys.argv[1]).resolve()
    out.mkdir(parents=True,exist_ok=False)
    records=[]
    for name,args in [('unit',['-m','unittest','-v','test_architecture']),
                      ('grid',['architecture_model.py'])]:
        cmd=[sys.executable,'-B',*args]
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        tick=time.monotonic()
        with (out/f'{name}.stdout').open('wb') as stdout,(out/f'{name}.stderr').open('wb') as stderr:
            p=subprocess.run(cmd,cwd=ROOT,stdout=stdout,stderr=stderr,
                             env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},
                             timeout=300,preexec_fn=limits)
        records.append({'name':name,'command':cmd,'cwd':str(ROOT),'started_at':start,
                        'elapsed_seconds':time.monotonic()-tick,'exit_code':p.returncode})
    evidence={'records':records,'python':sys.version,'platform':platform.platform(),
              'limits':{'wall_seconds':300,'cpu_seconds':60,'address_space_bytes':2<<30,'file_bytes':16<<20},
              'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(ROOT.iterdir()) if p.is_file()},
              'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(out.iterdir())}}
    (out/'execution.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(records,indent=2))
    return 0 if all(r['exit_code']==0 for r in records) else 1


if __name__=='__main__':raise SystemExit(main())
