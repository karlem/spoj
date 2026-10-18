# Independent bounded wedge probe review

Status: APPROVED. Final Wedge decision: affordable capacity, with a hard usefulness gate section, wedge-sources.json and retained raw evidence independently reviewed. No blocking findings. Read-only repository role, no source edits or product tests. This explicitly authorized probe executes the previously inspected pinnedEPLB policy, with constructed tensors; no model inference, network/hardware benchmark or artifact download.

## Actually executed

`/workspace/spoj/spoi/.venv/bin/python research/heterorouter/wedge_probe.py --eplb-source /workspace/scratch/software-atlas/deepseek-ai--EPLB/eplb.py > /workspace/scratch/wedge/reviewer-results.json`

Exit0. Python3.12.14,Torch2.14.1+cu130. SourceSHA25625b37ccd83aef2369c68f2b4bb596608a4f289956d97d9a3504bfd3159459e29, pinnedrevisiond52c72d5b2f2fb4c41afbf8eb21366820239913d. Script verifies the source digest before executing it.

## Checks and results

Observed physical order[0,3,1,2] implies two slots/device and expertowners[0,1,1,0]. With constructed loads[100,90,10,1], equalrate devices receive work101/100 and makespan101, matching exhaustive optimum101. With assumedrates[10,1], unchangedEPLBplan produces times10.1/100 and makespan100; finiteoracle assigns100+90 tofastdevice and10+1 toslow, times19/11 and makespan19. Reverse rates yieldEPLBmakespan101 versusoracle19. These are toy service-score units, not measured latency or model throughput.

For unequal slot capacities[3,1],EPLB equal2/2slots violates the assumedslowdevicecapacity, while enumeratedcoverage admits3/1 and makespan19.1. This is outsideEPLB's equal-slot contract, not an upstream bug or evidence an extension is novel. The enumeration visits all2^4expert-owner assignments, filters slot capacities, and minimizes parallelmakespan with lexicographic ties. Feasiblecounts6for2/2 and4for3/1 are correct. Every expert appears exactlyonce; replication/network/initialization/KV/reserves are intentionally outside this toy.

Analyticalcoldexposure is1-C(63,2)/C(64,2) raised across32 independentlayers, equivalently1-(31/32)^32=.6379447107436834. It is conditional onuniformtop2withoutreplacement perlayer and independentlayers. It does not establish actualrouterdistribution,tokenlatency oradversecoldtiercost.1/64weightfraction cannot generally substitute for measuredper-token exposure.

No blocking math/implementation findings. Probe demonstrates a baseline contract mismatch under constructedheterogeneity and a conditionalcold-exposure mechanism. It does not establish a newalgorithm,commercialwedge,physicalspeedup,modelcapacity orbotusefulness. Upstream issue anecdotes remain unverified reports and require independentreproduction.


## Final report/source/evidence review

Verified all six primaryREADMEbyte counts/SHA256 and allsixissueJSONsnapshotSHA256s againstwedge-sources.json. Savedcomments counts match declaredtotal/fetchedcounts (6,12,0,32,2,4); all available comments as of the snapshots are retained. Independently read the critical counterevidence:exo1102points toMac/Sparkpublicbeta1776;Colibri2109names prewarm2111andwarmstartfix2131;MLX-LM1438names existingstreamingPR1588,cache-sizepeak andpacked/concurrentcoalescingnulls. Report accurately treats these as unverifiedissueclaims and explicitly rejects missing-feature/novelty conclusions.

Parentprobe-results.json, independentreviewer-results.json and retainedrelated-projects-evidence/wedge-probe-results.json match as complete decodedJSON. Negativeartifact records expectedexit2onbadsource; script's hashguard occurs beforeimport, matching the claimed narrow integrity test. Reviewer did not rerun the negativecase. Sourcepins/environmentmatchtheexecutedprobe.

Final recommendation correctly marks capacity-donor integration as a conditionalcandidate, not a demonstratedadvantage. It acknowledgesColibri/exo/oMLXandotheralternatives,OOMbaseline/nonmeaningfulspeedupratios,smalleradequatelocalmodels,fullnon-expert/KV/workspace/stagingcapacitycosts andpendingactualhardware/workload/modelaccess. Proposed20%p95gate is expressly a proposeddecisioncriterion,not achieved orhuman-approvedSLO. No newimplementation/hardwareauthorization,nativeMacacceptance orphysicalmodelresult is claimed.

Nonblocking competitor-completeness note sent toparent:oMLXREADME162-168already claimsbyte-awareunequalshardplanning andmeasuredcompute/linkrebalancing,so itsprior-artbreadth isstrongerthanmerelyunequalmemorypipeline. Currentreport makesno missing-featureclaim,sothisdoesnotblockapproval;mentioningitstrengthenskillcriteria/upstream-firstframing.


Parent resolution: the final competitor paragraph explicitly names oMLX byte-aware shard planning, measured compute/link rebalancing and headroom-aware tuning. The optional completeness point is incorporated; probe code is unchanged.
