import concurrent.futures, datetime, hashlib, json, pathlib, urllib.request
ROOT=pathlib.Path('/workspace/scratch/inference-prior-art'); (ROOT/'raw').mkdir(exist_ok=True)
URLS={
 'sglang-abstract':'https://arxiv.org/abs/2312.07104',
 'parrot-abstract':'https://arxiv.org/abs/2405.19888',
 'pagedattention-abstract':'https://arxiv.org/abs/2309.06180',
 'petals-abstract':'https://arxiv.org/abs/2209.01188',
 'flexgen-abstract':'https://arxiv.org/abs/2303.06865',
 'distserve-abstract':'https://arxiv.org/abs/2401.09670',
 'mamba-abstract':'https://arxiv.org/abs/2312.00752',
 'sglang-radix-cache':'https://raw.githubusercontent.com/sgl-project/sglang/05ce0e980f00aa80864190d6f1cd5d9b685802f1/python/sglang/srt/mem_cache/radix_cache.py',
 'sglang-frontend':'https://raw.githubusercontent.com/sgl-project/sglang/05ce0e980f00aa80864190d6f1cd5d9b685802f1/python/sglang/lang/interpreter.py',
 'parrot-head':'https://api.github.com/repos/microsoft/ParrotServe/commits/main',
 'petals-readme':'https://raw.githubusercontent.com/bigscience-workshop/petals/22afba627a7eb4fcfe9418c49472c6a51334b8ac/README.md',
 'petals-session':'https://raw.githubusercontent.com/bigscience-workshop/petals/22afba627a7eb4fcfe9418c49472c6a51334b8ac/src/petals/client/inference_session.py',
 'flexgen-readme':'https://raw.githubusercontent.com/FMInference/FlexLLMGen/004ffef82b46e8dc8685c55d0cdda650bdaf1269/README.md',
 'distserve-readme':'https://raw.githubusercontent.com/LLMServe/DistServe/82831f1604cc6b10bebd360f6c437a07790dde9f/README.md',
 'mamba-head':'https://api.github.com/repos/state-spaces/mamba/commits/main',
}
def fetch(item):
 name,url=item; out={'id':name,'requested_url':url,'fetched_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executed':False}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SPOJ-research/1.0'}),timeout=25) as r:
   b=r.read(5*1024*1024+1)
   if len(b)>5*1024*1024: raise ValueError('5MiB per response limit')
   out.update(status=r.status,final_url=r.url,size=len(b),sha256=hashlib.sha256(b).hexdigest(),content_type=r.headers.get('Content-Type'))
   path=ROOT/'raw'/name; path.write_bytes(b); out['raw_path']=str(path)
 except Exception as e: out['error']=str(e)
 return out
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(fetch,URLS.items()))
 (ROOT/'manifest.json').write_text(json.dumps(results,indent=2)+'\n')
 for r in results: print(r['id'],r.get('status'),r.get('size'),r.get('error',''))
