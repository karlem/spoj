# Keep one failing dependency from exhausting the service

## Bulkheads and admission

Assign a finite concurrent-call budget to a dependency or workload class. Limit
both running work and waiting work. A semaphore with an unbounded waiter queue
can still exhaust memory or let requests expire while waiting. Choose a maximum
queue age from the remaining deadline, and reject or shed work explicitly.

A single global pool allows one noisy tenant or optional dependency to starve
critical traffic. Separate pools or fair admission can contain that effect, but
partitioning too rigidly strands capacity. Measure per-class demand and rejected
work before allocating permanent quotas.

Little's law is a mean steady-state relation, not a justification to multiply
arrival rate by p99 and declare a perfect worker count. Pool sizing also depends
on downstream capacity, burstiness, timeouts, and scheduling.

## Circuit breaker state machine

- **Closed:** calls are allowed and outcomes are measured.
- **Open:** calls fail fast or take an explicitly defined fallback.
- **Half-open:** a bounded number of probes tests recovery.

Specify which errors count, measurement window, minimum sample size, thresholds,
open interval, probe concurrency, and transitions. Client mistakes such as invalid
input should not necessarily trip the same breaker as dependency failure. If every
instance probes together, recovery itself can overload the dependency. Limit and
spread probes, then ramp traffic rather than releasing a large backlog at once.
A breaker does not by itself stop an already slow call from occupying a worker;
use deadlines and concurrency bounds as well.

## Deploy and restart safely

Startup establishes whether a process can initialize. Readiness establishes
whether it should receive traffic. Liveness should detect a process that needs
restart; tying liveness to a shared dependency can restart the whole fleet during
one dependency outage. The exact probes are platform/application specific.

For termination: stop admission, signal draining, finish/cancel in-flight work
within a finite window, release resources, and let the supervisor enforce the
remaining termination deadline. Replayed work must preserve operation identity.
Test mixed-version compatibility before rolling deployments; code rollback may
be unsafe after an irreversible schema change.

## Original failure drill

A catalog service has 100 workers. An optional recommendation call hangs until a
30-second timeout, eventually occupying every worker. Test a separate 10-call
recommendation bulkhead, short deadline chosen from the user budget, and an
explicit empty recommendation result. Verify catalog p99 and error rate under
recommendation failure, maximum queue length, and recovery after service returns.
The number 10 is a test parameter; production values require capacity evidence.

Exercise: a breaker opens correctly but heap use keeps growing. Inspect queues,
retained response buffers, pending futures, and canceled work. “The breaker is
open” does not prove bounded resource consumption.
