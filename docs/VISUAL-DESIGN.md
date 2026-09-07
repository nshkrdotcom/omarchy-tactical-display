# Visual system and review evidence

## Semantic composition

All modes share the identity/status rail, field, contextual detail plane and motion vocabulary. Most of the surface remains the field; there is no permanent dashboard grid. Selecting reserves side detail space on wide viewports and a bounded bottom region on narrow ones. Labels remain screen-space text rather than perspective-warped glyphs.

Connection Field uses a shallow local disc, near-plane application groups, a curved remote horizon and boundary apertures. Loopback stays inside the domain. Process Topology uses group islands and real parent branches; small populations expand immediately, large populations expose their members on demand. Machine Anatomy uses resource cutaways and measured contributor edges. Storage uses stacked process/mount/logical/block planes. Audio is a directed signal board whose focus can trace an entire measured route, not only one neighbor.

Shapes reinforce meaning: application stack, process square, remote diamond, listener aperture, mount plane, block-device solid, audio stream triangle, endpoint circle, default double-outline and muted cross. Closed relationships are dashed/ghosted; changed/new entities receive finite static/transition emphasis. Measured read/write notches have opposite orientation. A direction marker represents inferred origin or an observed signal route, not unmeasured bandwidth. There is no scanline, particle swarm, perpetual camera motion or meaningless blinking.

## Layout and motion

Semantic anchors use stable hashes/group identity and viewport-aware zones. A bounded spatial-grid collision pass places nodes at model-change frequency, never per animation frame. A second pass measures labels, budgets their count and reserves selected text. Layout caches are scoped by instrument, zone and focus context. Selected/related entities displace lower-priority labels rather than shrinking all text. Density omissions are counted and remain reachable through full-model search/traversal.

Normal/vivid modes have finite acquisition and mode-change transitions; reduced motion removes transitions. Geometry is not recomputed by an animation timer. A single Canvas paints only when model/layout/theme state changes; ordinary QML objects provide text and hit targets. Contrast-normalized palette roles derive from the active Omarchy colors. Opaque text planes preserve contrast despite the dimmed desktop. Minimum field text is 16 logical pixels and metadata 13, with larger native theme settings honored.

## Executed review (headless, not native)

`node scripts/render-fixtures.js --out /tmp/tactical-fixtures` executes the **same production Model/Layout/Draw/Palette/Inspection code**, with a test-only SVG Canvas adapter and approximate text metrics/chrome. Every image is visibly marked **TEST FIXTURE / NOT A QUATTRO CAPTURE**. It never feeds fixtures to the production helper or Quattro overlay.

The generator creates 50 combinations across all five modes: quiet, normal, dense, selected, search, light, privacy, reduced motion, low-space 1280x720 and high-space 2560x1440. Node tests additionally check geometry/label bounds and pairwise non-overlap at four field/font sizes, deterministic refresh positions, selected-label reservation and bounded stress complexity. The measured model/layout portion of the synthetic stress case must remain below 750 ms headlessly (tightened from the former 3 s guard); the whole test also spends time constructing the deliberately huge fixture. The acceptance matrix is **not** a claim that all Qt/Wayland screenshots were captured.

Representative rendered images were inspected for every instrument, plus dense Connection focus, light Audio focus and low-space Storage. Iteration fixed: process ancestry hidden in small trees; storage rate labels disappearing too early; local annotation/label collision; excessive focus expansion; transitive shared-remote selection leaking to unrelated apps; Audio sink focus failing to reveal upstream applications; Machine focus showing the wrong contributor metric; and insufficient minimum typography.

Generated files under `/tmp/tactical-fixtures` are representative shared-renderer evidence only and are intentionally not committed as native screenshots. They do not establish native antialiasing/font measurement, controls, compositing, high-DPI, GPU timing or active-focus behavior. No production-readiness claim is inferred from fixture SVGs.

## Target matrix and pass criteria

For each mode, capture quiet, normal, dense, selected, search, degraded, light/dark and reduced-motion states on a real Quattro session. Cover 1920x1080, 2560x1440 and available 4K/fractional scaling. Inspect at actual size. Fail on clipped/overlapping primary labels, unreadable selected information, unstable placement, unbounded line spaghetti, misleading flow semantics, a selected entity hidden by details, keyboard traps or frame hitches.

A reviewer should identify who talks to a shared remote, who spawned a process, which subsystem is pressured and by whom, which measured block device is busy (without inventing per-mount attribution), and which application feeds an audio sink. Record answers and actual captures. Fix failures in production code, rerun model/real integrations, and repeat the screenshots before publishing a changed release.
## Native panel density

When opened from the bar, Tactical Display follows the same cockpit frame contract as BEAM Deck. `KeyboardPanel` explicitly owns `padding: Style.space(8)` and the shared shell adds no second native-panel margin or viewport border. The top-level content rhythm uses Omarchy spacing roles instead of raw pixel literals: `xxl` for the major vertical cadence, `huge` for the header split, `xxs` inside the two-line identity block, and host control/input padding for interactive controls. This matters primarily because Omarchy's spacing scale is user/theme configurable; Qt Quick already works in logical coordinates, so tokenization is about host density consistency rather than pretending raw QML coordinates bypass display scaling.

### Header and navigation hierarchy

The native header is a `RowLayout#headerBar`: `identityBlock` on the left, an elastic spacer, and `headerActions` fixed on the right. `TACTICAL DISPLAY` is the primary heading at the same native subtitle role used by BEAM Deck. The second line is operational state plus a middle dot and an eliding context string containing the current instrument and only relevant qualifiers such as `PARTIAL`, `PRIVACY`, or the frozen timestamp. The state remains keyboard/screen-reader discoverable and gains an underline-on-hover cue before opening provider details.

Search, Freeze/Resume, Legend, Settings, and the persistent bordered Close affordance live in the action rail. Legend and Settings collapse at constrained widths while their keyboard routes remain available, preventing the Close control from wrapping away from the expected top-right position. Instrument selection is a separate `instrumentSelectorBar` below the header, followed by a stable separator before live status and workspace content. In fullscreen overlay mode the same hierarchy is retained but the instrument-purpose line and wider spacing remain visible, preserving the HUD character without forking interaction semantics.

### Perimeter, controls, and secondary surfaces

Command sheets now compute their scroll start from `outerGap + header height + headerBodyGap`, which keeps top and side clearances mathematically aligned instead of relying on unrelated magic offsets. The inspection panel, search field, trend panel, separators, and reusable `InstrumentButton` use `Style.spacing.*`, `Style.cornerRadius`, and the host control-padding roles for consistent edges and border weight. The native Close button uses the reusable `bordered` state so its boundary is visible at rest, while ordinary controls retain hover/focus borders.

Raw geometry inside `visual/Field.qml` is intentionally not normalized as desktop chrome: hit targets, node rings, and label boxes are coupled to the production layout/drawing algorithm and fixture geometry. Those values should change only with corresponding visual-layout tests, not as part of a shell-spacing refactor.

### Acceptance contract

Source tests lock the structural hierarchy and token usage, but visual acceptance remains a real Omarchy/Quickshell gate. Validate at the normal 1280×840 target and host-clamped smaller widths; change shell font and spacing scales; cover dark/light themes; and verify the fullscreen overlay separately. Fail the release for clipped identity text, a wrapped/moving Close control, inconsistent left/right perimeter clearances, double outer padding, misaligned search/sheet edges, inaccessible provider status, or keyboard focus regressions.
