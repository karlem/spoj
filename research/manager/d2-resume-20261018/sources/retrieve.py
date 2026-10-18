import urllib.request,json,pathlib,datetime,hashlib,sys
p=pathlib.Path('/workspace/scratch/d2-sources')
sets={'serverlessllm':('ServerlessLLM/ServerlessLLM',['sllm/backends/transformers_backend.py','sllm/backends/vllm_backend.py','sllm/routers/migration_router.py','docs/features/live_migration.md']), 'llama':('ggml-org/llama.cpp',['include/llama.h','src/llama-context.cpp','src/llama-kv-cache.cpp','src/llama-sampling.cpp','common/sampling.cpp','tools/server/server-context.cpp'])}
for name,(slug,paths) in sets.items():
 sha=json.loads((p/(name+'-commit.json')).read_text())['sha']
 for path in paths:
  dest=p/name/path; dest.parent.mkdir(parents=True,exist_ok=True); url=f'https://raw.githubusercontent.com/{slug}/{sha}/{path}'
  try:
   data=urllib.request.urlopen(url,timeout=30).read(2000000)
   dest.write_bytes(data)
   rec=dict(project=name,revision=sha,path=path,url=url,retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
   (p/'manifest.jsonl').open('a').write(json.dumps(rec)+'\n'); print(path,len(data))
  except Exception as e:
   rec=f'{datetime.datetime.now(datetime.timezone.utc).isoformat()} {url} {repr(e)}\n'; (p/'failures.txt').open('a').write(rec); print(rec)
