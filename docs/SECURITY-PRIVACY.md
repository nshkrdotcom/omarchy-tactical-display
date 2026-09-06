# Security and privacy

The plugin is unsandboxed code inside a trusted, long-lived desktop shell. It is an observational local instrument, not a security boundary or monitoring agent.

## Defaults

No root, sudo, capabilities, privileged eBPF, packet capture, firewall mutation, target/user-application process killing, mount changes, service installation, analytics, endpoint intelligence API or cloud connection. The plugin only terminates its own telemetry/helper processes as part of bounded lifecycle cleanup. Providers only read user-accessible procfs/sysfs/PipeWire. Missing permissions remain explicit. Do not weaken hidepid, ptrace or filesystem permissions to make the graph richer.

Process comm/executable/cgroup/start identity are read, but full argv and environment are not ingested. Executable paths, IPs, process names, audio device identities and mount paths can still be sensitive on screen. No raw telemetry history is persisted. Native user preferences/aliases and first-run/last-mode state are the only ordinary persistence. Runtime hold lock/tombstones contain invocation tokens, not telemetry.

## Optional communication and identity

Local aliases, hosts and services are offline. `tdNaming=dns` opts into PTR resolution through the system resolver, which may make network requests and disclose queried addresses to that resolver. The DNS worker is asynchronous, timeout-bounded, cache-bounded and killed on close/privacy activation. PTR is unverified identity. Offline MMDB requires an explicitly supplied local database and optional maxminddb module; nothing is fetched automatically. MMDB database open/query happens only in a separate timeout-bounded worker and is cancelled on close/privacy activation, so a slow/special filesystem path cannot block the principal telemetry loop.

Privacy mode replaces entity identities with stable session-rendering aliases, hides full details/search input/copy identity fields, and fully obscures the underlying desktop. Normal mode uses a strong dim with opaque readable text planes. Privacy is **not** cryptographic anonymization, isolation from other same-user processes, or a guarantee against reidentification from topology. The raw observations still exist in memory. Explicit CLI redirects, screenshots and native diagnostics are the operator's responsibility.

## Execution boundaries

Runtime subprocesses receive argument arrays, not interpolated shell commands. The principal helper is launched as fixed `/usr/bin/python3` with Quickshell environment clearing, and provider executables are resolved against a fixed system path. Both receive a reduced user-session environment rather than ambient PYTHONPATH/user-site/dynamic-loader overrides; the MMDB worker intentionally permits system site-packages while `PYTHONNOUSERSITE=1` blocks user-site imports. Telemetry has an allowlisted stdin protocol, a 64 KiB command-record ceiling, a real 32-record/second sliding-window limiter, and no execute-command method. Untrusted strings have control/bidi text removed, bounded lengths and QML PlainText treatment. JSON structure, frame size, nested fields, IDs, PipeWire client/port collections and non-finite values are validated before rendering. Provider-specific failures cannot substitute a fake successful frame.

External provider commands have time/output limits and a Linux parent-death guard, with process-group cleanup. `pw-dump` has a provider-specific 2 MiB output ceiling. Capacity probes are isolated and restricted; NFS/FUSE are not synchronously statvfs-probed. `nvidia-smi` is fallback-only when DRM sysfs produced no GPU observation. Hold state uses owned mode-0700 directories, mode-0600 regular one-link files, no symlink following, an atomic replacement and bounded lock acquisition. Release tombstones prevent a late press from reopening an already released hold.

## Audio actions

Observation is default. Opted-in actions require an explicit confirmation and are disabled while frozen. A fresh PipeWire graph revalidates the selected epoch+serial before passing its current numeric ID to wpctl. Mute/default changes have one-step undo where the previous target is known. **wpctl does not provide an atomic serial-conditional mutation here**: a daemon/object change between revalidation and the command remains a narrow race. Do not use these optional controls as a security-sensitive automation API. Rerouting is deliberately not guessed from text output or undocumented commands.

## Denial of service and residual limits

Resource bounds apply to work and internal state as well as emitted frames. Process discovery/reads use one absolute deadline and path-compressed runtime ancestry; socket tables share one global contact/deadline budget; expensive ownership is multi-rate; relationship layers reference one canonical socket-detail store; the per-process network layer is generated only for a bounded set of UI-requested application groups; freeze pins a generation rather than deep-copying it; and transport is constructively budgeted near 1.5 MiB before the 4 MiB emergency ceiling. Sustained high sampler duty automatically backs off cadence and reports the throttle. Incomplete scans do not manufacture exit storms.

Close stops timers/collection, drops live/frozen state and unloads the overlay. The QML supervisor does not treat process spawn as health: a schema-valid first snapshot is required, stalled progress/repeated malformed output request restart, Retry performs a restart, and recovery remains capped at six attempts with exponential backoff. A user-controlled kernel/PipeWire session can still withhold data; a broken Qt/compositor driver is outside the backend's guarantees. Stop/restart sends SIGTERM and escalates to SIGKILL after 1.2 seconds if the helper remains alive; component destruction uses immediate SIGKILL. Actual target-Quickshell signal/reap semantics, Qt teardown, hotplug and long-session resource behavior still require the native lifecycle checks in TESTING.md and HANDOFF.md.

The repository contains no font binaries, secrets or captured endpoint/process history. Test fixtures are explicitly fictional. Before sharing diagnostic output, review it; doctor may report local tool paths and errors, and raw `telemetry.py --once` output is sensitive by design.