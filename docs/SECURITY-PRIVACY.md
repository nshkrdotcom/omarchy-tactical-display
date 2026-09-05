# Security and privacy

The plugin is unsandboxed code inside a trusted, long-lived desktop shell. It is an observational local instrument, not a security boundary or monitoring agent.

## Defaults

No root, sudo, capabilities, privileged eBPF, packet capture, firewall mutation, process killing, mount changes, service installation, analytics, endpoint intelligence API or cloud connection. Providers only read user-accessible procfs/sysfs/PipeWire. Missing permissions remain explicit. Do not weaken hidepid, ptrace or filesystem permissions to make the graph richer.

Process comm/executable/cgroup/start identity are read, but full argv and environment are not ingested. Executable paths, IPs, process names, audio device identities and mount paths can still be sensitive on screen. No raw telemetry history is persisted. Native user preferences/aliases and first-run/last-mode state are the only ordinary persistence. Runtime hold lock/tombstones contain invocation tokens, not telemetry.

## Optional communication and identity

Local aliases, hosts and services are offline. `tdNaming=dns` opts into PTR resolution through the system resolver, which may make network requests and disclose queried addresses to that resolver. The worker is asynchronous, timeout-bounded, cache-bounded and killed on close/privacy activation. PTR is unverified identity. Offline MMDB requires an explicitly supplied local database and optional maxminddb module; nothing is fetched automatically.

Privacy mode replaces entity identities with stable session-rendering aliases, hides full details/search input/copy identity fields, and fully obscures the underlying desktop. Normal mode uses a strong dim with opaque readable text planes. Privacy is **not** cryptographic anonymization, isolation from other same-user processes, or a guarantee against reidentification from topology. The raw observations still exist in memory. Explicit CLI redirects, screenshots and native diagnostics are the operator's responsibility.

## Execution boundaries

Runtime subprocesses receive argument arrays, not interpolated shell commands. Telemetry has an allowlisted stdin protocol and no execute-command method. Untrusted strings have control/bidi text removed, bounded lengths and QML PlainText treatment. JSON structure, frame size, nested fields, IDs and non-finite values are validated before rendering. Provider-specific failures cannot substitute a fake successful frame.

External provider commands have time/output limits and a Linux parent-death guard, with process-group cleanup. Capacity probes are isolated and restricted; NFS/FUSE are not synchronously statvfs-probed. Optional vendor tools are conservatively polled. Hold state uses owned mode-0700 directories, mode-0600 regular one-link files, no symlink following, an atomic replacement and bounded lock acquisition. Release tombstones prevent a late press from reopening an already released hold.

## Audio actions

Observation is default. Opted-in actions require an explicit confirmation and are disabled while frozen. A fresh PipeWire graph revalidates the selected epoch+serial before passing its current numeric ID to wpctl. Mute/default changes have one-step undo where the previous target is known. **wpctl does not provide an atomic serial-conditional mutation here**: a daemon/object change between revalidation and the command remains a narrow race. Do not use these optional controls as a security-sensitive automation API. Rerouting is deliberately not guessed from text output or undocumented commands.

## Denial of service and residual limits

Scans, frames, nesting, command bursts, event/trend retention, layout and labels have bounds. Incomplete scans do not manufacture exit storms. Close stops timers/collection, drops state and unloads the overlay. The helper restarts with a finite backoff budget, not a hot loop. A user-controlled kernel/PipeWire session can still withhold data; a broken Qt/compositor driver is outside the backend's guarantees. Actual Qt teardown, hotplug and long-session resource behavior require the native lifecycle checks in TESTING.md.

The repository contains no font binaries, secrets or captured endpoint/process history. Test fixtures are explicitly fictional. Before sharing diagnostic output, review it; doctor may report local tool paths and errors, and raw `telemetry.py --once` output is sensitive by design.
