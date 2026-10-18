import sys,json,concurrent.futures
sys.path.insert(0,'/workspace/scratch/inference-prior-art')
from fetch import ROOT,fetch
URLS={
'ring-repo':'https://api.github.com/repos/Selimonder/RingAttention',
'sglang-dcp-doc':'https://raw.githubusercontent.com/sgl-project/sglang/05ce0e980f00aa80864190d6f1cd5d9b685802f1/docs/docs/advanced_features/dcp.mdx',
'sglang-dcp-comm':'https://raw.githubusercontent.com/sgl-project/sglang/05ce0e980f00aa80864190d6f1cd5d9b685802f1/python/sglang/srt/layers/dcp/comm.py',
'sglang-dcp-kernels':'https://raw.githubusercontent.com/sgl-project/sglang/05ce0e980f00aa80864190d6f1cd5d9b685802f1/python/sglang/kernels/ops/attention/dcp_kernels.py',
'parrot-semantic-doc':'https://raw.githubusercontent.com/microsoft/ParrotServe/a72ad158604661e06b5ea38db5dcc026884a398c/docs/sys_design/app_layer/semantic_variable.md',
'parrot-graph-executor':'https://raw.githubusercontent.com/microsoft/ParrotServe/a72ad158604661e06b5ea38db5dcc026884a398c/parrot/serve/session/graph_executor.py',
'flashattn-readme':'https://raw.githubusercontent.com/Dao-AILab/flash-attention/965c9212e6be33c821ee9f2b461564c5c91a2503/README.md',
}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(fetch,URLS.items()))
p=ROOT/'manifest.json';data=json.loads(p.read_text());data.extend(results);p.write_text(json.dumps(data,indent=2)+'\n')
for r in results:print(r['id'],r.get('status'),r.get('size'),r.get('error',''))
