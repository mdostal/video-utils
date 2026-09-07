#!/usr/bin/env python3
"""Optional config-file fallback for video-utils tools.

Lookup order: $VIDEO_CONFIG (explicit path) > ./.videorc > ./video.toml > none.
Env vars always win — this only fills in values not already in os.environ.

.videorc format: plain KEY=VALUE lines, '#' comments, blank lines ignored.
video.toml format: a flat [video] table, key = "value" or key = value lines
only (no arrays, no nested tables, no multi-line strings) — parsed with a
small regex, not a full TOML library (see AGENTS.md: depend only on common
tools).

Two entry points:
  - `python3 videoconfig.py --shell` prints `export KEY='VALUE'` lines for
    every config-declared key not already in the environment (bash scripts
    `eval` this via bin/lib/load-config.sh).
  - `apply_defaults()` (importable) sets os.environ[k] = v for the same
    not-already-set keys (review.py calls this directly).
"""
import os
import re
import shlex
import sys

_KV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def _strip_inline_comment(line):
    # Only strip '#' that isn't inside a quoted value.
    in_quotes = False
    quote_char = ""
    for i, ch in enumerate(line):
        if ch in ("'", '"'):
            if not in_quotes:
                in_quotes, quote_char = True, ch
            elif ch == quote_char:
                in_quotes = False
        elif ch == "#" and not in_quotes:
            return line[:i]
    return line


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _find_config_path():
    explicit = os.environ.get("VIDEO_CONFIG")
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for candidate in (".videorc", "video.toml"):
        if os.path.isfile(candidate):
            return candidate
    return None


def _parse_videorc(text):
    result = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = _strip_inline_comment(raw).strip()
        if not line:
            continue
        m = _KV_RE.match(line)
        if not m:
            print(f"[videoconfig] skipping unparseable .videorc line {lineno}: {raw}", file=sys.stderr)
            continue
        result[m.group(1)] = _unquote(m.group(2))
    return result


def _parse_toml_flat(text):
    result = {}
    in_video_table = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = _strip_inline_comment(raw).strip()
        if not line:
            continue
        if line.startswith("["):
            in_video_table = line.strip("[] ") == "video"
            continue
        if not in_video_table:
            continue
        m = _KV_RE.match(line)
        if not m:
            print(f"[videoconfig] skipping unparseable video.toml line {lineno}: {raw}", file=sys.stderr)
            continue
        result[m.group(1)] = _unquote(m.group(2))
    return result


def load_config_file():
    """Returns a dict of KEY -> VALUE declared in the found config file, or {}."""
    path = _find_config_path()
    if not path:
        return {}
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"[videoconfig] could not read {path}: {e}", file=sys.stderr)
        return {}
    if path.endswith(".toml"):
        return _parse_toml_flat(text)
    return _parse_videorc(text)


def unset_defaults():
    """Config-declared keys not already present in the environment."""
    declared = load_config_file()
    return {k: v for k, v in declared.items() if k not in os.environ}


def apply_defaults():
    """Set os.environ for every config-declared key not already set. Env always wins."""
    for k, v in unset_defaults().items():
        os.environ[k] = v


def print_shell_exports():
    for k, v in unset_defaults().items():
        print(f"export {k}={shlex.quote(v)}")


if __name__ == "__main__":
    if "--shell" in sys.argv:
        print_shell_exports()
    else:
        sys.exit("usage: videoconfig.py --shell")
