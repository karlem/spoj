import datetime, hashlib, json, os, platform, resource, subprocess, sys, time
from pathlib import Path
out=Path('/workspace/scratch/d2-validator')
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30)); resource.setrlimit(resource.RLIMIT_CPU,(60,60)); resource.setrlimit(resource.RLIMIT_FSIZE,(16<<20,16<<20))
cmd=[sys.executable,'-B',str(out/'review_checks.py')]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
with (out/'audit.stdout').open('wb') as stdout,(out/'audit.stderr').open('wb') as stderr:
 p=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=300,preexec_fn=limits,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
record={'command':cmd,'started_at':start,'elapsed_seconds':time.monotonic()-tick,'exit_code':p.returncode,'frozen_commit':'ad562a27560091abac92c3af38cb6062969f4ae0','worker':'/root/d2_validator','model_id':'unavailable; not exposed by harness','provider_run_id':'unavailable; not exposed by harness','same_host':True,'platform':platform.platform(),'python':sys.version,'limits':{'wall_seconds':300,'cpu_seconds':60,'address_space_bytes':2<<30,'per_file_bytes':16<<20},'sha256':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['review_checks.py','audit.stdout','audit.stderr']}}
(out/'audit-execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(p.returncode)
