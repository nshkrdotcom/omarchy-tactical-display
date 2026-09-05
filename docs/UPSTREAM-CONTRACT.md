# Quattro 4.0.1 runtime verification

Source review: **2026-09-05 UTC**, pinned to Git tag **v4.0.1**, not the moving `quattro` branch. No installed Omarchy/Qt/Quickshell version or local upstream Git commit was available in the build environment. A tag is recorded as a tag, not misrepresented as a tested host commit. Capture the actual workstation versions/commit using doctor before acceptance.

Primary source references:

- https://github.com/basecamp/omarchy/blob/v4.0.1/agents/skills/shell-dev.md
- https://github.com/basecamp/omarchy/blob/v4.0.1/shell/shell.qml
- https://github.com/basecamp/omarchy/blob/v4.0.1/shell/services/PluginRegistry.qml
- https://github.com/basecamp/omarchy/blob/v4.0.1/bin/omarchy-plugin-validate
- https://github.com/basecamp/omarchy/blob/v4.0.1/shell/Ui/BarWidget.qml
- https://github.com/basecamp/omarchy/blob/v4.0.1/shell/Ui/WidgetButton.qml
- https://github.com/basecamp/omarchy/blob/v4.0.1/shell/plugins/bar/README.md
- https://github.com/basecamp/omarchy/blob/v4.0.1/shell/Commons/Style.qml
- https://github.com/basecamp/omarchy/blob/v4.0.1/shell/Commons/Color.qml
- https://github.com/basecamp/omarchy/blob/v4.0.1/bin/omarchy-shell
- https://github.com/basecamp/omarchy/blob/v4.0.1/bin/omarchy-bar
- https://github.com/basecamp/omarchy/blob/v4.0.1/config/hypr/bindings.lua
- https://github.com/basecamp/omarchy/blob/v4.0.1/default/hypr/bindings/utilities.lua
- https://github.com/basecamp/omarchy/blob/v4.0.1/default/hypr/bindings/voxtype.lua

## Decisions supported by that source

The existing shell owns plugin discovery, enablement, process and loaded entry-point instances. Third-party root paths are `~/.config/omarchy/plugins/<id>/`. Hosted entry points are Items with injected manifest/source directory, shell and registry context. Overlay lifecycle is open(payloadJson)/close. Manifest schema 1 pairs kind `bar-widget` with entry point key `barWidget`, not a hyphenated key. No symlinks are allowed in the plugin tree.

Canonical CLI is `omarchy-shell shell summon|hide|toggle`; it forwards to the running host and does not launch a second one. The generic `shell call <id> <method> <arg>` returns a string from an already loaded instance; the new read-only `diagnostics` method uses this existing route. No invented separate bar IPC target is needed.

BarWidget injects bar/moduleName/settings and exposes vertical/barSize. WidgetButton supplies orientation-sensitive implicit size, text style, tooltip and left/right/middle press signals. Native inline configuration is read from host shellConfig and changed through updateEntryInline with unknown fields merged before replacement. Typography uses the verified Style.fontFamily/fontBaseSize and Color palette properties.

Bar placement uses `omarchy bar put` or `omarchy bar move --section ... --index ...`; setting uses `omarchy bar set ... [--json]`. Native enablement can place a widget. The plugin itself never edits the user's layout behind the host. Personal bindings are Lua in Quattro 4.0.1, using the provided o.bind/hl APIs; the printed helper is not a legacy hyprland.conf installer.

## Required target recheck

```bash
printf '%s\n' "$OMARCHY_PATH"
git -C "$OMARCHY_PATH" describe --tags --always
git -C "$OMARCHY_PATH" rev-parse HEAD
quickshell --version
hyprctl version
omarchy plugin validate ~/.config/omarchy/plugins/nshkr.tactical-display
```

Run the installed qmllint against the installed Quattro import tree. Compare any import-metadata warnings with a first-party widget using the same imports; save both exact logs. Do not globally silence warnings or label all warnings upstream noise. There was no native lint execution here and no claimed installed desktop acceptance. The sources above establish the integration contract, not proof that this QML has run on hardware.
