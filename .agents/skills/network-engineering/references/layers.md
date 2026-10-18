# Localize forwarding, link, wireless, and security failures

These are selective procedures checked against the public ninth-edition author
slides (Chapters 4–8), not complete coverage of those layers.

## Forwarding versus routing

Forwarding selects an output for a packet using installed rules; routing/control
protocols determine and update those rules. A healthy control-plane adjacency
does not prove a packet's installed forwarding path is correct. Check source and
destination, selected prefix/rule, next hop, interface, and return path. Consider
VRFs, policy routes, tunnels, and network namespaces before interpreting a host's
single default route.

For ordinary destination-prefix forwarding, longest-prefix match selects the
most specific applicable prefix. An aggregate route does not override a more
specific route merely because its metric is numerically smaller. Selection among
routes for the same prefix is implementation/policy specific. BGP includes policy
and path attributes; it is not simply shortest geographical distance. Link-state
and distance-vector protocols have different convergence behaviors. During a
change, transient loops or black holes may exist while nodes disagree.

Original exercise: `10.0.0.0/8` points to A and `10.20.0.0/16` to B. Traffic for
`10.20.4.9` selects B under longest-prefix matching. Before deleting B's route to
“fix latency,” establish ownership, alternate path, and why the route exists.

## LAN and neighbor resolution

An IP destination and an Ethernet destination serve different scopes. For a remote
IP destination, the sender normally resolves the local next-hop MAC rather than
the remote host's MAC. Inspect subnet/prefix, route, neighbor state, VLAN, switch
port, and gateway. IPv4 ARP and IPv6 neighbor discovery are different protocols;
do not apply ARP assumptions to IPv6.

A switch learns forwarding information from observed source MAC addresses. A
broadcast/multicast or unknown-destination frame can have different forwarding
behavior from an established unicast entry. A local reachability failure can
therefore reflect VLAN or neighbor-resolution state even when the DNS answer and
application configuration are correct. Capture at a defined interface/scope and
correlate with counters; one observation point can miss drops elsewhere.

## Wireless

A good nominal link rate or strong signal does not establish low application
latency. Inspect retransmissions, airtime contention, signal/noise, client power
behavior, and roaming. Hidden terminals can interfere at a receiver even when
transmitters do not hear one another. Congestion in the wireless access segment
can dominate a path whose wired backhaul is otherwise idle. Compare a wired
control path, client/AP counters, and the same workload before changing application
retry policy. Extra retries may worsen shared airtime pressure.

## Security boundaries

Separate confidentiality, integrity, peer authentication, and authorization. A TLS
connection that authenticates a server does not authorize a user to read any
record. Certificate verification must bind the expected identity and a valid trust
chain under the selected client policy; do not disable it to fix a connection
problem. Diagnose name mismatch, expiry, chain/trust, time, protocol support, and
intermediary termination explicitly.

A firewall allow rule does not prove an application is safe, and a successful
transport handshake does not prove that application credentials or permissions
are valid. State which hop terminates encryption and which identity each service
actually verifies. For sensitive operations, validate application authorization
and replay/operation semantics in addition to network connectivity.
