import sys,json,concurrent.futures
sys.path.insert(0,'/workspace/scratch/inference-prior-art')
from fetch import ROOT,fetch
URLS={
'ring-readme':'https://raw.githubusercontent.com/lhao499/llm_large_context/d2ea1af9a288f85ea2fd74690ece1c16d2eebc83/README.md',
'mamba2-abstract':'https://arxiv.org/abs/2405.21060',
'mamba2-module':'https://raw.githubusercontent.com/state-spaces/mamba/e9594ce1c732d97440f0332fdc43170a2294dbfa/mamba_ssm/modules/mamba2.py',
'parrot-scheduler':'https://raw.githubusercontent.com/microsoft/ParrotServe/a72ad158604661e06b5ea38db5dcc026884a398c/parrot/serve/scheduler/global_scheduler.py',
}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,URLS.items()))
p=ROOT/'manifest.json';data=json.loads(p.read_text());data.extend(results);p.write_text(json.dumps(data,indent=2)+'\n')
for r in results:print(r['id'],r.get('status'),r.get('size'),r.get('error',''))
