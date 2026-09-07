#!/usr/bin/env bash
# Source this to load .videorc/video.toml defaults for keys not already set in
# the environment. Env always wins — see bin/lib/videoconfig.py. Safe no-op if
# python3 or the config file are missing.
_VC_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  _VC_EXPORTS="$(python3 "$_VC_HERE/videoconfig.py" --shell 2>/dev/null)" || _VC_EXPORTS=""
  [ -n "$_VC_EXPORTS" ] && eval "$_VC_EXPORTS"
  unset _VC_EXPORTS
fi
unset _VC_HERE
