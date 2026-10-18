# B-trees, LSM trees, and actual I/O

## B-tree family

A page-oriented B+ tree stores sorted separator keys in internal pages and data
or references at the leaves. High fanout reduces tree height. A lookup traverses
roughly `O(log_B N)` levels in an idealized balanced tree with fanout `B`; actual
I/O depends on cache residency and layout. A range scan locates its start, then
walks adjacent key ranges. SQLite uses particular table/index B-tree page formats;
do not generalize its layout to every database.

Updates modify pages and may split or rebalance them. WAL or another recovery
protocol must protect durable consistency. Small random updates can induce page
writes, while cache/buffer management can coalesce changes. A clustered access
path improves locality for one ordering but cannot cluster the same records in
every secondary-index order.

## LSM family

Writes normally enter a log and an in-memory sorted structure. Immutable sorted
runs are flushed to storage and merged by compaction. Reads reconcile the newest
visible version across memory and applicable runs. Deletes introduce tombstones
until old versions can safely be discarded. This shifts work from foreground
random updates to sequential writes and background maintenance; it does not make
write I/O free.

In leveled compaction, non-overlap within a level can limit point lookup work, but
moving data through levels rewrites bytes. More overlapping runs can reduce some
write amplification at the expense of read or space amplification. Exact trade-offs
depend on policy, size ratio, overlap, skew, compression, and implementation.
RocksDB's documented options are a concrete implementation, not a universal LSM law.

## Amplification ledger

| Quantity | Practical question | Measurement boundary |
| --- | --- | --- |
| Read amplification | How many probes/bytes serve one logical query? | Include cache misses, filters, index/data blocks, and versions |
| Write amplification | How many storage bytes per logical changed byte? | Say whether WAL, compaction, filesystem, and device writes are included |
| Space amplification | How much storage per live logical byte? | Include old versions, tombstones, temporary compaction files, and indexes |

Compression can reduce bytes but add CPU. A better write-amplification number
with a longer fsync tail may still miss an ingest SLO. Reserve space and I/O for
background compaction so the engine can maintain its structure under sustained
load; capacity at the start of an empty-database test is misleading.

## Original workload comparison

A telemetry service performs bursts of 50,000 inserts/s, usually looks up recent
keys, and deletes by retention. Compare an LSM candidate's sustained ingest,
compaction backlog, write stalls, filter memory, and retention cleanup with a
page-tree candidate's page locality, log sync, and index writes. Do not select
solely on peak writes/s. Include a long catch-up phase after the burst.

A billing service has many indexed range queries and small updates to a stable
working set. A page-tree candidate may be simpler to tune, but measure secondary
index cost and cache misses. An LSM can also be appropriate if range behavior and
maintenance fit. The choice follows workload evidence rather than labels.

## Bloom filters

Under the idealized independent-hash model, a filter with `m` bits, `n` inserted
keys, and `k` hashes has false-positive probability approximately
`(1 - exp(-kn/m))^k`. The near-optimal `k` is `(m/n) ln 2`. Ordinary filters have no
false negatives for correctly inserted keys and intact filter data; versions,
corruption, concurrency, and incorrect lifecycle handling can break that premise.
A positive result means “possibly present,” not “present.” Filters cost memory
and construction CPU, so budget them against the blocks they save.
