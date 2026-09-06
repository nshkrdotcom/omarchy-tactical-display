#!/usr/bin/env bash
# Prints only. The user reviews and adds this Lua block to personal bindings.lua.
set -euo pipefail
cat <<'LUA'
-- Tactical Display / Omarchy Quattro Lua bindings.
-- Review collisions: omarchy menu keybindings --print
-- Add this block ONCE to ~/.config/hypr/bindings.lua, then hyprctl reload.
do
  local hold_token = nil
  local sequence = 0
  local helper = os.getenv("HOME") .. "/.config/omarchy/plugins/nshkr.tactical-display/scripts/invoke.py"
  local function quote(s) return "'" .. s:gsub("'", "'\\''") .. "'" end
  local function invoke(action, token)
    hl.dispatch(hl.dsp.exec_cmd("/usr/bin/python3 -B " .. quote(helper) .. " " .. action .. " --token " .. quote(token)))
  end
  o.bind("SUPER + F10", "Tactical Display toggle", "omarchy-shell shell toggle nshkr.tactical-display '{}'")
  o.bind("SUPER + F11", "Tactical Display hold", function()
    if hold_token then return end
    sequence = sequence + 1
    hold_token = tostring(os.time()) .. ":" .. tostring(sequence) .. ":" .. string.format("%.6f", os.clock())
    invoke("hold-press", hold_token)
  end)
  -- Release is matched even when Super was released first. An unrelated F11
  -- release is a no-op and is not consumed by this binding.
  o.bind("F11", "Tactical Display release", function()
    local token = hold_token
    hold_token = nil
    if token then invoke("hold-release", token) end
  end, { release = true, ignore_mods = true, non_consuming = true })
end
-- Emergency close after compositor/keymap reload during a hold:
-- omarchy-shell shell hide nshkr.tactical-display
LUA