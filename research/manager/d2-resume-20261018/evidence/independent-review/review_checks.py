"""Independent evidence audit and event-interval oracle; no upstream execution."""
import datetime, hashlib, importlib.util, json, math, resource
from decimal import Decimal as D
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
resource.setrlimit(resource.RLIMIT_FSIZE, (16 << 20, 16 << 20))
ROOT=Path('/workspace/spoj-d2-review/research/manager/d2-resume-20261018')
OUT=Path('/workspace/scratch/d2-validator')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads((ROOT/'evidence/attempt-1/execution.json').read_text())
for name,value in original['source_sha256'].items(): assert sha(ROOT/name)==value,(name,'source changed')
for name,value in original['output_sha256'].items(): assert sha(ROOT/'evidence/attempt-1'/name)==value,(name,'raw output changed')
old=ROOT/'evidence/attempt-1/grid.stdout'; new=OUT/'rerun/grid.stdout'
assert old.read_bytes()==new.read_bytes(), 'full raw grid mismatch'
data=json.loads(new.read_text()); assert data==json.loads(old.read_text())
assert data['case_count']==864 and len(data['rows'])==864
assert data['input_sha256']==sha(ROOT/'inputs.json')
print('Full 864-row grid byte-for-byte equal:',sha(new))
print('Original source/input/output manifest: all entries match')
# SHA256 provenance plus independently computed git blob IDs against pinned API trees.
source_count=0
for raw in (ROOT/'sources/manifest.jsonl').read_text().splitlines():
 r=json.loads(raw); b=(ROOT/'sources'/r['project']/r['path']).read_bytes()
 assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 tree=json.loads((ROOT/'sources'/f"{r['project']}-tree.json").read_text())
 assert tree['sha']==r['revision'] and tree['truncated'] is False
 blob=next(e for e in tree['tree'] if e['path']==r['path'])
 blob_id=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert blob_id==blob['sha'],(r['path'],'blob mismatch')
 source_count+=1
bundle=0
for line in (ROOT/'sources/BUNDLE_SHA256SUMS').read_text().splitlines():
 digest,name=line.split('  ',1); assert sha(ROOT/'sources'/name)==digest,name; bundle+=1
print('Pinned manifest source files checked:',source_count,'bundle entries checked:',bundle)
# Discrete state changes, independently integrated across event intervals.
# Values are fractions of the initial payload present in the constrained pool.
def occupancy(events,end):
 state=D(1); prev=D(0); integral=D(0)
 for when,new_state in sorted(events):
  if when>end: break
  integral+=(when-prev)*state; state=D(new_state); prev=when
 return integral+(end-prev)*state

def close(actual,expected):
 assert math.isclose(actual,float(expected),rel_tol=1e-12,abs_tol=1e-12),(actual,expected)
checks=0
for row in data['rows']:
 size=D(row['kv_bytes'])/D(2**30); wait=D(str(row['wait_seconds']))
 export=D('.005')+size/D(str(row['bandwidth_gib_s']))
 restore=D('.005')+size/D(str(row['bandwidth_gib_s']))
 replay=D('.02')+D(row['tokens'])/D(row['prefill_tokens_s'])
 for p in row['policies']:
  policy=p['policy']
  if policy=='resident': logical=[]; physical=[]; ready=wait
  elif policy=='replay':
   logical=[(D(0),0),(wait,1)]
   physical=logical if row['allocator_releases'] else []
   ready=wait+replay
  else:
   # Event queue serializes export completion, tool arrival, restore start/end.
   restore_start=sorted([wait,export])[-1]
   ready=restore_start+restore
   logical=[(export,0),(restore_start,1)]
   physical=logical if row['allocator_releases'] and row['domain']=='separate' else []
  slot_saved=(wait-occupancy(logical,wait))*size
  physical_saved=(wait-occupancy(physical,wait))*size
  close(p['reusable_slot_saved_gib_s'],slot_saved)
  close(p['physical_saved_gib_s'],physical_saved)
  close(p['reusable_slot_saving_fraction'],slot_saved/(size*wait))
  close(p['physical_saving_fraction'],physical_saved/(size*wait))
  close(p['added_resume_seconds'],ready-wait)
  assert p['slot_economic_candidate']==(slot_saved>=D('.25')*size*wait and ready-wait<=D('.25'))
  assert p['physical_economic_candidate']==(physical_saved>=D('.25')*size*wait and ready-wait<=D('.25'))
  assert p['correctness']=='unverified' and p['accepted_inference_result'] is False
  checks+=1
print('Independent event-interval oracle passed for',checks,'policy outcomes')
# Challenge an excluded assumption: shared prefix cells cannot be reclaimed merely
# by deleting one owner's sequence. Model each cell's owners; no cost formula used.
# 8 of 10 cells belong to both A and B, only 2 exclusively to A.
cells=[{'A','B'} for _ in range(8)]+[{'A'} for _ in range(2)]
for owners in cells: owners.discard('A')
freed=sum(not owners for owners in cells)
assert freed==2 and freed/len(cells)<.25
print('Adversarial shared-prefix ownership: only 2/10 cells reusable; 25% impossible even with arbitrarily long wait. Confirms exclusive-KV limitation.')
# Challenge causal resume accounting with strongly asymmetric rates and long waits.
spec=importlib.util.spec_from_file_location('tested_cost_model',ROOT/'cost_model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
args=dict(size_bytes=1<<30,tokens=8192,write_gib_s=32,read_gib_s=.5,prefill_tokens_s=100000,domain='separate',allocator_releases=True)
for wait in (5,120,1000000):
 p=m.evaluate(wait_s=wait,**args)['policies'][2]
 assert p['reusable_slot_saving_fraction']>.99
 assert p['added_resume_seconds']==2.005 and not p['physical_economic_candidate']
print('Adversarial asymmetric transfer: waits 5/120/1000000s never hide 2.005s restore; all physical candidates rejected.')
# Caller-supplied compatibility is a simulation flag, not actual identity verification.
for p in m.evaluate(wait_s=120,compatible=False,**args)['policies']:
 assert not p['slot_economic_candidate'] and not p['physical_economic_candidate'] and not p['accepted_inference_result']
print('Incompatible-state negative control rejects every policy; no state payload inspected by this arithmetic.')
print('All audit checks PASS; model inference correctness remains UNVERIFIED.')
print('Completed UTC:',datetime.datetime.now(datetime.timezone.utc).isoformat())
counts={name:{gate:sum(p[gate] for row in data['rows'] for p in row['policies'] if p['policy']==name) for gate in ('slot_economic_candidate','physical_economic_candidate')} for name in ('resident','replay','snapshot')}
assert counts==data['candidate_counts_not_probabilities']
assert counts=={'resident':{'slot_economic_candidate':0,'physical_economic_candidate':0},'replay':{'slot_economic_candidate':96,'physical_economic_candidate':48},'snapshot':{'slot_economic_candidate':192,'physical_economic_candidate':48}}
assert not any(p['physical_economic_candidate'] for row in data['rows'] if not row['allocator_releases'] for p in row['policies'])
print('README candidate counts independently counted:',json.dumps(counts,sort_keys=True))
