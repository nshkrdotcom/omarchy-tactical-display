# Security and Privacy

## Trust boundary

Tactical Display is a third-party Omarchy plugin and therefore runs unsandboxed inside the user's long-lived `omarchy-shell` process. Installing any Omarchy plugin means trusting its user-level code.

This plugin deliberately keeps its own behavior narrow.

## What it reads while open

- `/proc/net/tcp`, `tcp6`, `udp`, `udp6`
- `/proc/net/dev`
- readable `/proc/<pid>/fd` symlinks for socket ownership
- `/proc/<pid>/comm`
- `/proc/<pid>/exe` basename
- `/proc/<pid>/cmdline` **only to extract argv[0]**; all later arguments are discarded

## What it does not do

- no `sudo` or root helper
- no packet capture
- no raw sockets
- no firewall changes
- no process/socket termination
- no DNS lookup
- no GeoIP lookup
- no HTTP/API calls
- no telemetry upload
- no persistent network history
- no clipboard writes
- no Hyprland config mutation

## Why full command lines are not displayed

Process command arguments can contain API keys, bearer tokens, passwords, signed URLs, database credentials, or other secrets. Connection Field only keeps the executable identity / `argv[0]`, process name, and PID. Do not casually broaden this in the UI.

## Process visibility

Linux permissions may expose a socket in `/proc/net/*` while preventing attribution through another process's file-descriptor directory. Such sockets remain visible as unattributed. Do not silently escalate privilege to fill the gap.

## On-screen sensitivity

The overlay can display:

- remote IP addresses;
- process names and PIDs;
- executable identity;
- local/remote ports and service names;
- listener state.

That can still be sensitive during screen sharing or recording. A future presentation-redaction mode may be useful, but it should be explicit and truthful rather than silently replacing values.

## Interpretation boundary

Connection Field is not a vulnerability scanner, firewall monitor, IDS, or attack detector. `inbound` is a best-effort inference based on a local port matching a visible listener. The visual language must never imply that an inbound relationship is inherently malicious.
