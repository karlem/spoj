import os,sys,json,hashlib,subprocess,resource,time,statistics,signal,math
from pathlib import Path
from fractions import Fraction as F
ROOT=Path('/workspace/spoj-hardware-review/research/manager/hardware-os-20261018')
OUT=Path('/workspace/scratch/hardware-validator')
RAW=Path('/workspace/scratch/hardware-sources')
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from architecture_model import evaluate,os_bound
records=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def limits():
    os.setsid()
    resource.setrlimit(resource.RLIMIT_AS,(256<<20,256<<20))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16<<20,16<<20))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def call(name,cmd,cwd,expected=0,timeout=30):
    start=time.monotonic()
    proc=subprocess.Popen(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=limits,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    try:stdout,stderr=proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate()
        raise AssertionError('timeout')
    (OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
    row={'name':name,'command':cmd,'cwd':str(cwd),'exit':proc.returncode,'expected_exit':expected,'seconds':time.monotonic()-start}
    records.append(row)
    assert proc.returncode==expected,row
    return stdout
checks=[]
def ok(name,data=True):checks.append({'check':name,'result':data})
# Original architecture source and output provenance.
meta=json.loads((ROOT/'evidence/model-attempt-1/execution.json').read_text())
for name,want in meta['source_sha256'].items():assert digest(ROOT/name)==want,name
for name,want in meta['output_sha256'].items():assert digest(ROOT/'evidence/model-attempt-1'/name)==want,name
ok('architecture_original_hashes')
call('unit',[sys.executable,'-B','-m','unittest','-v','test_architecture'],ROOT)
grid=call('grid',[sys.executable,'-B','architecture_model.py'],ROOT)
assert grid==(ROOT/'evidence/model-attempt-1/grid.stdout').read_bytes()
ok('exact_full_grid_rerun',{'case_count':json.loads(grid)['case_count'],'sha256':hashlib.sha256(grid).hexdigest(),'counts':json.loads(grid)['counts_not_probabilities']})
# Independent formulas and units, recomputed for every frozen row, not calling evaluate.
cfg=json.loads((ROOT/'inputs.json').read_text())
W=3*4096*14336*2*F(1,2);A=2*4096*2
assert W==168*2**20 and A==16384 and W/A==10752
for row in json.loads(grid)['rows']:
    M=row['cold_layers'];g=F(str(row['gpu_expert_ms']));c=F(str(row['cpu_expert_ms']));r=F(str(row['rtt_ms']))
    n=F(str(row['line_gbit_s']))*10**9/F(8)*F(4,5)/row['flows']
    p=24*10**9;base=F(32,10)+(32-M)*g
    expected={'payload_bytes_per_second':n,'weight_staging_lower_ms':base+M*(r+max(g,W/n*1000,W/p*1000)),
              'weight_staging_serial_ms':base+M*(r+g+W/n*1000+W/p*1000),
              'near_weights_lower_ms':base+M*(r+max(c,F(A)/n*1000,F(A)/p*1000)),
              'near_weights_serial_ms':base+M*(r+c+F(A)/n*1000+F(A)/p*1000),
              'coarse_layer_design_ms_feasibility_unverified':(32-M)*(F(1,10)+g)+M*(F(1,2)+c)+(r+F(A)/n*1000+F(A)/p*1000 if M else 0)}
    for k,v in expected.items():assert row[k]==float(v),(k,row[k],v)
    win='no_robust_20pct_winner'
    if expected['near_weights_serial_ms']<=F(4,5)*expected['weight_staging_lower_ms'] and expected['near_weights_serial_ms']<expected['weight_staging_lower_ms']:win='near_weights_robust_conditional'
    elif expected['weight_staging_serial_ms']<=F(4,5)*expected['near_weights_lower_ms'] and expected['weight_staging_serial_ms']<expected['near_weights_lower_ms']:win='weight_staging_robust_conditional'
    assert row['conditional_decision']==win
ok('independent_all_row_arithmetic',{'weight_bytes':int(W),'activation_bytes':A,'ratio':int(W/A),'400Gbps_raw_GBs':400/8,'HBM_to_network_nominal_ratio':3350/(400/8)})
# Adversarial extension is deliberately OUTSIDE the frozen grid.
adversarial=evaluate(cfg,cold=32,gpu_ms=.2,cpu_ms=100,line_gbit_s=400,flows=1,rtt_ms=.2)
assert adversarial['conditional_decision']=='weight_staging_robust_conditional'
ok('exploratory_slow_cpu_counterexample_not_grid_change',adversarial)
for f,r,target in [(.05,1,.05),(.2,1,.2),(.4,.5,.2)]:
    bound=os_bound(f,r);assert bound['latency_reduction_fraction']==target
    assert math.isclose(bound['speedup_upper_bound'],1/(1-target))
assert os_bound(.2,1)['speedup_upper_bound']==1.25
ok('amdahl_latency_vs_speedup')
# Full original transport hash manifest and original source hashes.
transport=ROOT/'transport'
for line in (transport/'SHA256SUMS').read_text().splitlines():
    want,name=line.split('  ',1);assert digest(transport/name)==want,name
for name,want in json.loads((transport/'raw/environment.json').read_text())['source_sha256'].items():assert digest(transport/name)==want,name
ok('transport_original_hashes')
summary=json.loads((transport/'raw/summary.json').read_text());total=good=0;meds={}
for session in summary['sessions']:
    data=[json.loads(l) for l in (transport/'raw'/(session['name']+'.jsonl')).read_text().splitlines()]
    req=[r for r in data if r['kind']=='request'];final=data[-1]
    process=json.loads((transport/'raw'/(session['name']+'.process.json')).read_text())
    assert all(r['io_ok'] for r in req)
    expected=42 if session['mode']=='corrupt' else 0
    assert process['exit']==final['exit']==expected and final['child_exit']==0
    total+=sum(r['completed_echo_bytes'] for r in req);good+=sum(r['equal'] for r in req)
    assert sum(r['completed_echo_bytes'] for r in req)==final['completed_echo_bytes']
    if expected==0:
        assert len(req)==152 and all(r['equal'] for r in req)
        assert [r['sequence'] for r in req]==list(range(1,153))
        for size,count in [(128,128),(16384,16),(1048576,2)]:
            measured=[r['rtt_verify_ns'] for r in req if r['payload_bytes']==size and not r['warmup']]
            assert len(measured)==count
            med=statistics.median(measured)
            assert med==session['payloads'][str(size)]['median_ns']
            meds[(session['pair'],session['transport'],size)]=med
    else:assert len(req)==1 and not req[0]['equal']
assert total==90117376 and good==1520
for pair in range(1,6):
    for size in (128,16384):assert (meds[(pair,'unix',size)]<meds[(pair,'tcp',size)]) == bool(pair%2)
assert json.loads((transport/'raw-attempt1/compile.json').read_text())['returncode']==1
assert (transport/'attempt1-driver.exit').read_text().strip()=='1'
ok('original_raw_positive_negative_accounting_order_reversal',{'good_requests':good,'application_bytes':total,'failure_retained':True})
# Inspect source occurred before execution. Compile frozen file without changes.
binary=OUT/'echo.bin'
call('compile',['gcc','-std=c11','-O2','-Wall','-Wextra','-Wpedantic','-Werror',str(transport/'echo.c'),'-o',str(binary)],OUT)
small_total=small_good=0
for mode,condition,expected in [('tcp','normal',0),('unix','normal',0),('tcp','corrupt',42)]:
    out=call(mode+'-'+condition,[str(binary),mode,condition],OUT,expected=expected,timeout=20)
    data=[json.loads(l) for l in out.decode().splitlines()];req=[r for r in data if r['kind']=='request'];final=data[-1]
    assert final['child_exit']==0 and final['exit']==expected and all(r['io_ok'] for r in req)
    if expected==0:assert len(req)==152 and all(r['equal'] for r in req)
    else:assert len(req)==1 and not req[0]['equal']
    small_total+=final['completed_echo_bytes'];small_good+=final['successful_requests']
assert small_total==18023680 and small_good==304
ok('smallest_transport_independent_rerun',{'good_requests':small_good,'application_bytes':small_total,'exits':[0,0,42],'source_sha256':digest(transport/'echo.c')})
# All available raw originals and every public excerpt verified, not just summaries.
manifest=json.loads((ROOT/'sources/manifest.json').read_text());hashed=0
for row in manifest:
    p=RAW/'raw'/row['id']
    if p.exists() and 'sha256' in row:
        assert digest(p)==row['sha256'],row['id'];assert p.stat().st_size==row['bytes'];hashed+=1
excerpts=0
for row in json.loads((ROOT/'sources/public-evidence.json').read_text()):
    p=RAW/'raw'/row['id']
    assert digest(p)==row['sha256'],row['id']
    lines=(RAW/(row['id']+'.txt')).read_text().splitlines()
    for excerpt in row.get('extracts',[]):
        assert '\n'.join(lines[excerpt['first_line']-1:excerpt['last_line']])==excerpt['text'],(row['id'],excerpt)
        excerpts+=1
ok('source_originals_and_public_excerpts',{'hashed_raw_documents':hashed,'matched_excerpts':excerpts})
report={'reviewer':'/root/hardware_validator','frozen_revision':'e9f9d08f8bfb5ded804cc5f79fb0f2b4c913b064','scope':'Same-host independent worker; no physical replication or inference validation','limits':{'as_bytes_per_process':256<<20,'cpu_s_per_process':30,'fsize_bytes':16<<20,'command_timeout_s':30,'transport_timeout_s':20,'whole_script_timeout_s':280},'records':records,'checks':checks}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'status':'PASS','transport_application_bytes':small_total,'counterexample_weight_serial_ms':adversarial['weight_staging_serial_ms'],'counterexample_near_lower_ms':adversarial['near_weights_lower_ms']},indent=2))
