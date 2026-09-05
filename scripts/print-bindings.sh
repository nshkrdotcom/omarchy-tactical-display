#!/usr/bin/env bash
set -euo pipefail

cat <<'LUA'
-- Tactical Display: add to ~/.config/hypr/bindings.lua
-- SUPER+N is only a suggested chord. Check `omarchy menu keybindings --print`
-- first and choose an unused chord if needed.

o.bind("SUPER + N", "Tactical Display: Connection Field", "omarchy-shell shell summon nshkr.tactical-display '{}'")
o.bind("SUPER + N", nil, "omarchy-shell shell hide nshkr.tactical-display", { release = true })

-- Toggle alternative if release ordering is unreliable on your workflow:
o.bind("SUPER + CTRL + N", "Tactical Display: Connection Field (toggle)", "omarchy-shell shell toggle nshkr.tactical-display '{}'")
LUA
