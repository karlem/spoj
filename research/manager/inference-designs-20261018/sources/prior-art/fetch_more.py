import sys,json,concurrent.futures
sys.path.insert(0,'/workspace/scratch/inference-prior-art')
from fetch import ROOT,fetch
URLS={
'ring-abstract':'https://arxiv.org/abs/2310.01889',
'ring-head':'https://api.github.com/repos/Selimonder/RingAttention/commits/main',
'flashdecoding-blog':'https://crfm.stanford.edu/2023/10/12/flashdecoding.html',
'flashattn-head':'https://api.github.com/repos/Dao-AILab/flash-attention/commits/main',
'parrot-readme':'https://raw.githubusercontent.com/microsoft/ParrotServe/a72ad158604661e06b5ea38db5dcc026884a398c/README.md',
'parrot-tree':'https://api.github.com/repos/microsoft/ParrotServe/git/trees/a72ad158604661e06b5ea38db5dcc026884a398c?recursive=1',
'mamba-readme':'https://raw.githubusercontent.com/state-spaces/mamba/e9594ce1c732d97440f0332fdc43170a2294dbfa/README.md',
'sglang-tree':'https://api.github.com/repos/sgl-project/sglang/git/trees/05ce0e980f00aa80864190d6f1cd5d9b685802f1?recursive=1',
'vllm-context-parallel':'https://docs.vllm.ai/en/latest/serving/context_parallel_deployment.html',
}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(fetch,URLS.items()))
p=ROOT/'manifest.json'; data=json.loads(p.read_text()); data.extend(results);p.write_text(json.dumps(data,indent=2)+'\n')
for r in results:print(r['id'],r.get('status'),r.get('size'),r.get('error',''))
