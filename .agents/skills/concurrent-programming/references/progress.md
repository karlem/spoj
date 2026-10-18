# Progress and reclamation

## Name the guarantee

| Property | Meaning in the stated model | What it does not ensure |
| --- | --- | --- |
| Deadlock freedom | Some operation/thread can make progress rather than all waiting cyclically | Every waiter eventually succeeds |
| Starvation freedom | Each participating operation eventually completes under stated fairness assumptions | A fixed step bound |
| Obstruction freedom | An operation finishes if it runs in isolation long enough | Progress under arbitrary contention |
| Lock freedom | System-wide completion continues in an infinite execution under the algorithm's assumptions | Every individual operation completes |
| Wait freedom | Each operation completes in a bounded number of its own steps | A fixed wall-clock deadline despite preemption/GC |

State the scheduling and primitive assumptions. A CAS loop can starve a particular
thread while others repeatedly succeed. Its allocation path or reclamation scheme
may block even if the pointer-update core is lock-free. A spin lock uses atomic
instructions but waits for an owner; atomics alone do not make it lock-free.

## ABA and pointer reuse

A thread reads head pointer `A`. Another removes `A`, changes the structure, then
makes the head equal to `A` again. A CAS that checks only the pointer sees equality
but misses the intervening changes. Allocator reuse can produce the same address
for a different object. Tagging/versioning may distinguish generations, but tag
width/wraparound and atomic representation need justification.

Safe reclamation is a separate requirement: a thread can dereference a removed
node before attempting CAS. Hazard pointers, epoch schemes, reference counting,
or garbage collection have different performance and progress costs. Merely
fixing the ABA comparison does not make a freed node safe to read. A stalled
participant in an epoch scheme may delay reclamation and grow retained memory.

## Choose synchronization by invariant and contention

Start with one clear lock for a small object. Measure critical-section duration,
contention, scheduling delay, and tail wait. Sharding can reduce contention if
operations are mostly local; cross-shard invariants reintroduce coordination.
Reader/writer locks help only under suitable reader duration, write frequency,
and implementation fairness. Shared atomic counters can become cache-coherence
bottlenecks even when increments are correct.

Moving updates into thread-local buffers reduces shared writes but delays global
visibility and needs a merge protocol. An approximate metric may permit that;
a strict inventory invariant may not. Specify semantic relaxation explicitly.

## Original exercise

A custom stack pops a node, frees it immediately, and claims “CAS makes it safe.”
Show a schedule where a second thread already holds that node pointer and reads
its `next` after free. Require a reclamation protocol or a simpler protected
implementation before accepting the stack. Then ask how a stalled participant
affects reclamation and whether the final implementation meets its stated
progress claim.
