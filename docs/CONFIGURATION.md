# Configuration

Current settings schema: **tdVersion = 1**. Runtime authority is `model/Settings.js`; the machine-readable current-version schema is `config/settings.schema.json`.

Settings live in the existing native Quattro entry for `com.nshkr.tactical-display`: first the bar layout entry, otherwise the top-level plugins entry. `Configuration.qml` uses `shell.updateEntryInline` with the complete merged previous entry. Unknown keys remain intact. It does not rewrite shell.json independently, and installation does not silently rearrange the bar. Missing host/entry gives an explicit session-only notice. A newer tdVersion is read-only rather than overwritten by a downgrade.

| Native key | Default | Values / behavior |
|---|---|---|
| tdVersion | 1 | Current schema. |
| tdDefaultInstrument | connection | First-run mode. |
| tdLastInstrument | connection | Remembered mode after selection/explicit invocation. |
| tdAnimation | normal | reduced, normal, vivid; no infinite animation. |
| tdRefreshProfile | balanced | efficient, balanced, responsive target cadences (1.5 / 0.75 / 0.35 s). Sustained high sampler duty can temporarily back off the effective cadence; telemetry reports the actual interval/throttle. |
| tdLoopback / tdListeners | true / true | Visibility, not provider falsification. |
| tdNaming | local | raw, local, dns. DNS explicitly opts into system-resolver PTR requests. |
| tdLabels | balanced | minimal, balanced, dense; changes budgets, not text into unreadable sizes. |
| tdPrivacy | false | Opaque desktop treatment and stable anonymized identifiers; suppresses DNS/offline identity enrichment. |
| tdBarMode | icon | icon or label; vertical bar stays compact. |
| tdIntroSeen | false | First-run acknowledgement; help can reopen introduction. |
| tdAudioActions | false | Explicit opt-in to confirmed mute/default/undo. |
| tdAliases | {} | At most 512 IP-address -> local name entries. No executable commands. |
| tdOfflineDb | empty | Explicit local MMDB path; optional Python maxminddb module required. Open/lookup occurs only in a timeout-bounded worker, never the principal helper. No automatic download. |

For a bar-hosted entry, native CLI examples:

```bash
omarchy bar set com.nshkr.tactical-display tdAnimation reduced
omarchy bar set com.nshkr.tactical-display tdRefreshProfile efficient
omarchy bar set com.nshkr.tactical-display tdPrivacy true --json
omarchy bar set com.nshkr.tactical-display tdAliases '{"192.0.2.20":"Lab service"}' --json
omarchy bar set com.nshkr.tactical-display tdNaming dns
# Return to local-only naming:
omarchy bar set com.nshkr.tactical-display tdNaming local
```

`192.0.2.20` is a documentation example, not a real recommended endpoint. Use the settings sheet for a plugin-only entry without a bar placement. Direct editing while the host is running can conflict with its in-memory configuration; prefer the host APIs or stop the shell first and retain a backup.

Invocation payloads accept `instrument`, `mode` (toggle/hold), `monitor` (legacy `screen` also accepted), `picker`, `help`, optional `privacy`, typed `focus` and `filters`. Unknown keys are inert. Payloads over 32 KiB or malformed JSON yield defaults and a notice, not execution.

```bash
omarchy-shell shell summon com.nshkr.tactical-display '{"instrument":"connection","monitor":"DP-1","privacy":true,"filters":{"protocol":"tcp","state":"live"}}'
omarchy-shell shell summon com.nshkr.tactical-display '{"instrument":"processes","focus":{"processKey":"process:1234:98765"}}'
```

The process key above is illustrative. Obtain the actual full instance key from current detail, not merely a PID. Actual provider keys are opaque identities; never synthesize an action target from a displayed PID. Filter keys are direction/protocol/state/emphasis/lens and use the choices shown in the instrument's lens rail. Per-instrument transient lenses are session state, not persisted raw observations.