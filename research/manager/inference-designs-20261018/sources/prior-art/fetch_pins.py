import sys,json,concurrent.futures
sys.path.insert(0,'/workspace/scratch/inference-prior-art')
from fetch import ROOT,fetch
URLS={
'ring-correct-head':'https://api.github.com/repos/lhao499/llm_large_context/commits/main',
'vllm-context-pinned':'https://raw.githubusercontent.com/vllm-project/vllm/7879f3687b5b6a4be4754242e70b9c21cf7b4183/docs/serving/context_parallel_deployment.md',
'sglang-readme':'https://raw.githubusercontent.com/sgl-project/sglang/05ce0e980f00aa80864190d6f1cd5d9b685802f1/README.md',
'ring-html':'https://arxiv.org/html/2310.01889v4',
'mamba-module':'https://raw.githubusercontent.com/state-spaces/mamba/e9594ce1c732d97440f0332fdc43170a2294dbfa/mamba_ssm/modules/mamba_simple.py',
}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(fetch,URLS.items()))
p=ROOT/'manifest.json';data=json.loads(p.read_text());data.extend(results);p.write_text(json.dumps(data,indent=2)+'\n')
for r in results:print(r['id'],r.get('status'),r.get('size'),r.get('error',''))
