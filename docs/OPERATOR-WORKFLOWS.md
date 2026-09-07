# Operator workflows

## Find what needs attention

Open **A Briefing** from the instrument rail, or press `A` while the field has focus. Attention ranks measured symptoms and explains where to inspect next. Choose **Inspect machine** to collect CPU/memory/I/O pressure and local storage capacity. Providers remain demand-scoped to the active instrument.

The starting thresholds are transparent triage heuristics, not Linux recommendations or a health guarantee:

| Observation | Watch | High |
|---|---|---|
| PSI `some avg10` | ≥5% stalled time | ≥20% |
| Memory/I/O PSI `full avg10` | ≥2% stalled time | ≥10% |
| Available RAM / total | <10% | <5% |
| Available filesystem capacity / total | <10% | <3% |

PSI `some` measures time with some tasks stalled; `full` measures time with all non-idle tasks stalled. System-wide CPU `full` has no defined interpretation and is excluded. Full memory/I/O stall findings take priority over their some-stall counterpart. High CPU utilization alone does not prove contention. Follow contributors and trends to investigate; none of these findings executes a host action.

Missing, stale and inactive measurements do not become zero. Provider freshness allows the larger of 3.5 seconds or four provider intervals; capacity observations additionally expire after 30 seconds. Partial measurements are qualified. Optional hardware that is simply absent stays in Data sources rather than generating an attention item. Every finding has an evidence description, provenance and an inspection destination.

## Follow changes over time

The **Activity** tab keeps at most 120 backend-observed lifecycle events for five minutes. Filter by instrument and opened/changed/closed state. **Event: opened + closed** hides routine state changes without deleting retained history. Change rows explain which observed fields changed (state, parent, route, mute/default, socket count or pressure band), without retaining the old/new identity-bearing values. Initial observations establish a baseline rather than generating an “opened” event for every existing process. Only sampled providers contribute; incomplete or truncated observations never prove disappearance. The record cap can shorten the visible history on a high-churn host.

Repeated event frames are deduplicated. A restarted helper starts a new timeline. Freeze holds the displayed event history alongside the exact snapshot; live collection continues independently. A late freeze acknowledgement cannot pull newer events into the held history. Selecting an event follows its exact key, including relationship edges. If it has ended or is outside collected scope, the interface says so instead of selecting another process with the same PID.

## Keep entities together

Select an entity in any instrument and press `W`, or choose **Pin** in its inspection panel. The **Pins** tab keeps up to eight lightweight identities and their original instrument routes. It displays current scalar observations when available; a process's CPU uses 100% for one logical core, and RSS can include shared pages. “Not observed” can mean a departed entity, inactive provider or collection limit. Stale metrics are not presented as current.

Use **Inspect in …** to return to the entity; network process pins preserve the application scope needed to collect instance relationships. **Unpin** removes one entry; **Clear pins** clears the set. Resetting a field view preserves pins, while closing Tactical Display clears them.

Privacy aliases match the field, including PipeWire sink/source/stream classes, and remain searchable. Enabling privacy also masks names retained before it was enabled. Pins and activity are not saved to disk. Mount-pin capacity has its own 30-second expiry even while the storage provider remains fresh.

## Compare before and after

In the **Baseline** tab, capture a baseline before changing a workload. It retains one compact set of aggregate values and provider timestamps, rather than a complete telemetry frame. Compare host CPU, used/available memory, CPU/memory/I/O PSI, host receive/transmit and device-level storage read/write rates. **Replace baseline** starts a new comparison; **Clear baseline** removes it.

CPU and PSI changes use percentage points (`pp`); memory changes use bytes; throughput changes use bytes per second. Unavailable measurements yield an em dash, with provider quality shown alongside the row. A decrease is not automatically an improvement: workload context still matters. Virtual interfaces can double-count host traffic; device I/O does not establish per-mount attribution.

**Copy report** copies observation time, live/frozen status, findings, baseline comparisons, pins and the 20 most recent events. In privacy mode it copies a deliberate redacted projection, never raw retained objects. The desktop clipboard is outside the plugin's session lifetime and may be retained by a clipboard manager. Copying is always an explicit action.

## Inspect the graphics

Each trace has a separate, wrapping numeric legend so paired read/write or receive/transmit values remain visible at compact widths.

In Machine Anatomy, press `T` to open the trend. Select CPU, memory, storage or network to select its series; choose 15, 30 or 60 seconds. **Usage / PSI avg10** switches to stall history for CPU/memory/storage. CPU utilization has a fixed 0–100% host scale; other plots share a measured scale across their traces. PSI is already a kernel rolling average, sampled into the displayed window.

Brackets show measured minimum and maximum. Paired series use names plus solid/dashed line styles. Gaps mean missing data or acquisition interruption; the renderer does not bridge them. Hover to inspect a nearby real sample, click to hold the cursor, or choose **Inspect ← →** for keyboard focus. `Left`/`Right` move by sample, `Home`/`End` choose the first/last, and `Space` returns the cursor to the latest value. A held cursor can expire as the live window advances; freeze the snapshot to keep it indefinitely within the open session.

`F6` returns between controls and field navigation. `Backspace` returns from the briefing. `Escape` closes Tactical Display immediately. Motion settings and the absence of an animation heartbeat are unchanged.
