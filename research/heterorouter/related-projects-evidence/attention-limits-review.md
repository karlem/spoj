# Independent attention limits probe review

Status: APPROVED. Final Limits ledger: learned control and KV-resident attention section, limits-sources.json and retained attention evidence reviewed. No unresolved blocking findings. No repo edits/product tests or new downloads. Executed only the authorized bounded localCPUfloat32 research tensors, not model inference, sockets, workers, hardware benchmarks, JEV API orRLtraining.

## Executed command and evidence

`/workspace/spoj/spoi/.venv/bin/python research/heterorouter/attention_limits_probe.py > /workspace/scratch/limits/reviewer-attention-results.json`

Exit0. Actual13positivecases:4seeds times3shardings plus1extreme-logit case. Maximumabsoluteerror4.76837158203125e-7 under rtol1e-5,atol1e-6. Two deliberatefaults rejected: averaging normalized shardoutputs error.5;ignoring requiredmask error1.0. StrictJSON parses with noNaN/Infinity; samplemissinglocalmaxima areJSONnull with explicitmeaningminusinfinity,noallowedkeys.

## Math/contract checks

local_stats computes local logitmaximum m,stable unnormalizedsum z,and weightedvalue numerator u. merge rescales each shard byexp(m-globalmax),then divides summednumerator by summeddenominator. EmptyKVshard contributes m=-inf,z=0,u=0;allmaskedqueries have zerooutput via zero numerator and safe denominator1. The tested extreme+/-1000logits avoid overflow by local/globalmax subtraction. Groupedqueryheads expandKVhead2toQhead4identically in localpath and directSDPA; kernels/reduction paths differ, with SDPA not reusinglocal_stats/merge arithmetic.

Coverage assertion requires everyoriginalKVposition exactlyonce;tests cover contiguousuneven,interleaved andemptyshards. Masks slice alongoriginalKVpositions and include queryspecificcausal-like boundaries plus deliberatelyallmaskedrow. No actualcacheidentity/version/disconnect/coherenceboundary is tested.

Declaredbyteledger independently checked:32layers*8KVheads*128dim*32768tokens*2(K,V)*2bytes=4294967296bytes(4GiB). DecodeQueryFP16fanout524288bytes; FP32partialoutputs1048576; FP32two-statistics16384; oneownedKVappend131072; total1720320bytes. These assumeonebatch/onequery perlayer,twoKVcontextshards,allqueryheads broadcast andappendstoredonce. Headers,nonattentionstate,workspace,precisionconversion andtransportcopies excluded.32dependentroundtrips*.5ms=16ms is anassumedstructuralcomponent,not a measuredlatency or universal bound.4GiB/1GBps=4.294967296seconds is rawtransferarithmetic.

No blocking findings. LocalFP32algebra does not establishFP16wireaccuracy,distributedexecution,physicalcapacity,taskquality orMacacceptance. Fullreport review remains pending.


## Final report/source review

Independently verified all12selectedfile hashes/sizes across11primaryrepos againstlimits-sources.json. LocalHelixREADME is saved with normalizeduppercasefilename while upstreammanifestcorrectlyrecordslowercasereadme.md; bytesmatch. Parentretainedrelated-projects-evidence/attention-limits-results.json exactlymatches independentreviewer-results.json as complete parsedJSON.

OfficialTypeSafeSDK/adapter/skillsdocumentation supports typedChoice/Noul/Score andJev/SystemOneframing. AdapterREADMEexplicitly describes comparisonviaotherLLMAPIs andprobabilitynormalization. Finaltext correctlydoesnotinferlocalopenweights,latency,calibration,modellicensingoronlinepolicyupdates fromSDKavailability/typedanswers. UpstreamSKILL.md wasresearchdata,not instructionauthority orinvokedskill. Suppliedblog403 fallback isexplicit andnoAPIexecutionclaimed.

Bandit/regression/MPC/RLchoices,feedback/counterfactualcausality,explorationcost,safeactionfilteringandcontrolleroverhead areproposedcomparisons,notlearnedpolicyresults. ThreeKVcases clearlyseparateexactprefixreuse,coldrestore/phasehandoff,andliveper-tokenattention. Identity/position/mask/precision/recurrentstate andbranchsuffixconditions prevent arbitrarycrossmodel/promptsharingclaims.

RingAttentionREADMEemphasizeslongcontexttrainingandblockwiseoverlap,notbatch-oneremotedecodespeed. InfiniGenprimaryabstractexplicitlyselectspredictedessentialKVfetches;DuoAttentionreplacesfullcache forstreamingheadsafterpatternidentification. Finaltextappropriatelykeepsselective/modeladaptedKVlanesseparatefromstrictfullattentionparity. OtherprojectmetadataandcitationleadsclearlyremainREADME-level,notfullpaperread/reproduction.

Finalfloat32probeclaims,13positivecases,2negativefaults,maxerrorandnull=-inftraceencoding matchactualindependentrun. SeparateFP16KV/query+FP32partialbytethoughtmodel isexplicitlynotvalidatedbyFP32tensorparity. No socket/codec/worker/cachecoherence/capacity/hardwarelatency/physicaladvantage isclaimed. Maincorrectness/nativeMacgatesunchanged. No newexperiments,downloads,repoeditsorproducttestsrun duringfinalreview.
