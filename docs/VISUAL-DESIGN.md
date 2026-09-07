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

When opened from the bar, Tactical Display follows the same Omarchy popup chrome contract as BEAM Deck: `KeyboardPanel` owns the outer frame and content box, Tactical adds no second frame or outer content margin, popup background/text tokens are used, native title/body/caption font sizes are used, and major internal gaps follow the same compact 12px-scale rhythm. Fullscreen summon keeps the Tactical-specific viewport frame and wider monitor-space breathing room.

### Header alignment

The identity and session-status areas share one two-column baseline grid. The live/provider state aligns with the instrument title row, while `LOCAL SESSION` / `PRIVACY ON` aligns with the purpose row. Interactive status text uses a hit target without Button padding, so clickability never changes the visible typographic alignment.
