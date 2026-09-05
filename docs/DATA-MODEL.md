# Telemetry schema and truth boundaries

## Transport

Schema **3** uses one JSON object per newline. Snapshot fields: `schemaVersion`, `type`, sequence, monotonic seconds, wall-time seconds, active instrument, target sample interval, capabilities, processes/groups, network, system, storage, audio, hardware, events, trend, transport limits and measured sample duration. JSON non-finite numbers are forbidden. Unknown values are null, never fabricated zero. The wall clock is presentation only; deltas, identity lifetimes and history use monotonic time.

The helper accepts only configure, inspect, freeze, audio-action and ping. Commands are at most 64 KiB with a bounded 32-record burst; snapshots at most 4 MiB. A bounded full snapshot is retained for detail while child socket previews and oversized collections are reduced for transport. `limits.omitted` reports truncation. The UI validates section types, unique IDs, nested scalar types, depth, collection limits and non-finite numbers. It does not execute commands from telemetry fields.

| Collection / metric | Source and units | Classification / limitation |
|---|---|---|
| Process identity | PID + `/proc/<pid>/stat` start ticks | Observed instance; PPID parent is revalidated against start identity. |
| Application group | Cgroup/application, executable/UID, runtime ancestry | Derived grouping, with explicit provenance; never generic-name-only merging. |
| Process CPU | `utime + stime` deltas / clock ticks / monotonic seconds | Derived percent; 100% is one logical core, may exceed 100 for multithreading. First sample unavailable. |
| Resident memory | `stat` RSS pages times page size | Observed bytes; RSS sums double-count shared resident pages. Not unique RAM attribution. |
| Process I/O | `/proc/<pid>/io` read_bytes/write_bytes | Storage-accounted bytes and bytes/second; not syscall character counts, not per-mount traffic. Permission-denied remains missing. |
| Sockets | `/proc/net/{tcp,tcp6,udp,udp6}`, optional inet_diag | Current network namespace only; not a packet capture. FD scans only read accessible processes. |
| Socket ownership | Readable `/proc/<pid>/fd` inode associations + start identity | Multiple owners supported; visible sockets without readable owners remain unattributed. |
| Relationship | Application/instance + remote IP + protocol + origin class + service port | Derived aggregation retains child sockets; counts are observations, not flows invented by animation. |
| Origin class | Address, protocol and matching visible listener/binding/owner | Inferred; no claim to observe connect/accept provenance. Loopback is explicit. UDP binding is not a TCP listener. |
| Queues | Kernel socket queues | Established/datagram occupancy in bytes. Listening TCP queue metrics are backlog counts, not bytes. |
| Optional TCP rate/RTT | inet_diag cookie + length-checked tcp_info fields | ACKed/received cumulative byte deltas in B/s; RTT in ms. Not wire speed, not available on all kernels. Shared cross-group ownership suppresses ambiguous per-group rates. |
| Interface RX/TX | `/proc/net/dev`, monotonic counter deltas | B/s; sum of non-loopback interfaces, which can count traffic at more than one virtual interface. Not deduplicated physical wire throughput. |
| Machine CPU/load | `/proc/stat`, `/proc/loadavg` | CPU utilization derives from counters (iowait treated as idle); load is not CPU percent. Per-core/package/core topology where readable. |
| Memory/swap | `/proc/meminfo` | Bytes; used = total minus available, cache and swap shown separately. |
| Pressure | `/proc/pressure/{cpu,memory,io}` | Kernel PSI percentages of stalled time; not inferred causality. Pressure emphasis threshold is 5% avg10 in the UI. |
| Devices/layers | diskstats and `/sys/class/block` | Major:minor IDs, parent partitions, device-mapper/slave associations. Sector accounting uses 512 bytes. |
| Device rate/busy/await | Monotonic diskstats deltas | B/s; busy percent and completion-time averages are accounting proxies, not universal device saturation/latency truth. Physical aggregate excludes logical-layer/partition double-counting. |
| Mounts/capacity | `/proc/self/mountinfo`, timed `statvfs` child | Structural backing device; total/available bytes. Local safe filesystem roots only, cached 15 s, maximum 64. FUSE/NFS and unsafe transformed paths are not probed. |
| FD-to-mount | `/proc/<pid>/fdinfo` mnt_id, matching mount namespace | Dashed **open descriptor** association. Never used to apportion read/write rates across mounts. |
| Audio graph | `pw-dump` JSON nodes/clients/ports/devices/links/default metadata | Actual routes. Serial scoped to PipeWire core epoch defends against daemon restart. PID joins are client-reported, not authentication. |
| Audio mute/volume | PipeWire Props and Format | Mute state; linear gain, not measured level. Sample rate/format only when reported. |
| Optional GPU/thermal/fan | Safe sysfs/hwmon; conservative nvidia-smi fallback | Provider-reported utilization, bytes, degrees C, RPM as available. Missing hardware is not zero utilization. |
| Endpoint name | Explicit alias, `/etc/hosts`, optional system PTR | Local mapping or unverified enrichment, never authenticated server identity. Raw IP retained. |
| Service / offline ASN | Unambiguous `/etc/services`; optional user MMDB | Enrichment, not protocol detection or exact host geography. |

## Cadence and work bounds

Efficient/balanced/responsive target intervals are 1.5 / 0.75 / 0.35 seconds. Sampling duration adds to helper scheduling when collecting is slow; UI and capability timestamps report actual freshness. Audio is cached for at least 2 seconds; optional hardware at least 5; process metadata 5; capacity 15; FD-to-mount scans 3. DNS uses one asynchronous worker, bounded pending/cache entries and a timeout. No provider polls while the overlay is closed.

The process scan caps 8,192 entries and its work budget; sockets cap 20,000 records; ownership and FD scans are separately deadline-limited. Bounded event stores keep short (~4 s) ghosts, at most 512 normal recent events and 256 ghost records per decorated domain. A 60-second/120-sample ring stores only machine aggregate trends. Layout draws at most 160 nodes; adaptive Connection Field budgets are lower when needed, with a maximum 144 connection edges; other fields normally cap 200 edges. Labels have a viewport/font/density-dependent budget with a selected-label reservation. All omissions are discoverable through search/traversal/focus and reported in the field.

**Incomplete observations do not mean entities exited.** Provider capability objects include source, status/level, sampledAt, intervalSeconds, durationMs, complete, reason and suggestion. Providers may be available, partial, stale, unavailable or inactive. Inactive means not needed by the current instrument. A failed audio refresh can retain a stale observed graph with its original success timestamp; it is not relabeled current.

## Freeze and retention

Freeze retains one exact helper-side full snapshot and one bounded UI snapshot; request IDs reject stale replies. Collection continues and bounded aggregate trends progress. A frozen entity detail comes from that frozen snapshot even after live changes. A helper restart invalidates its frozen buffer; the UI retains the displayed capture but deep detail reports unavailable instead of fetching live substitutes. No raw snapshots are written unless the operator explicitly redirects diagnostic CLI output. Close clears session state and subprocesses.
