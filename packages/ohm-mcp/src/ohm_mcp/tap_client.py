"""Fail-open true-tap client and per-user hook installer."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

COMMAND = "metrecept-tap"
DEFAULT_BASE_URL = "https://api.metrecept.co.uk/v1"


def _home() -> Path:
    return Path.home()


def _base_url() -> str:
    root = (os.environ.get("OHM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    if not root.endswith("/v1"):
        root = f"{root}/v1"
    return root


def _credentials_path(home: Path | None = None) -> Path:
    return (home or _home()) / ".metrecept" / "credentials.json"


def _read_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _credential_key(home: Path | None = None) -> str:
    try:
        value = _read_object(_credentials_path(home)).get("api_key")
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    return value.strip() if isinstance(value, str) else ""


def _api_key() -> str:
    return (os.environ.get("OHM_API_KEY") or "").strip() or _credential_key()


def post_tap(payload: dict[str, Any], *, timeout: float = 2.0) -> None:
    key = _api_key()
    if not key:
        return
    request = urllib.request.Request(
        f"{_base_url()}/tap",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    urllib.request.urlopen(request, timeout=timeout).read()


def _write_object(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(value, indent=2)}\n", encoding="utf-8")


def _merge_cursor_hook(value: dict[str, Any]) -> bool:
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Cursor hooks must be a JSON object")
    entries = hooks.setdefault("beforeSubmitPrompt", [])
    if not isinstance(entries, list):
        raise ValueError("Cursor beforeSubmitPrompt hooks must be an array")

    for index, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get("command") == COMMAND:
            updated = {**entry, "command": COMMAND, "timeout": 2}
            if updated == entry:
                return False
            entries[index] = updated
            return True
    entries.append({"command": COMMAND, "timeout": 2})
    return True


def _merge_claude_hook(value: dict[str, Any]) -> bool:
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Claude hooks must be a JSON object")
    entries = hooks.setdefault("UserPromptSubmit", [])
    if not isinstance(entries, list):
        raise ValueError("Claude UserPromptSubmit hooks must be an array")

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        commands = entry.get("hooks")
        if not isinstance(commands, list):
            continue
        for index, command in enumerate(commands):
            if isinstance(command, dict) and command.get("command") == COMMAND:
                updated = {**command, "type": "command", "command": COMMAND}
                if updated == command:
                    return False
                commands[index] = updated
                return True
    entries.append({"hooks": [{"type": "command", "command": COMMAND}]})
    return True


def _resolve_install_key(
    flag_key: str | None,
    *,
    home: Path,
    input_func: Callable[[str], str],
) -> str:
    key = (flag_key or "").strip()
    if not key:
        key = (os.environ.get("OHM_API_KEY") or "").strip()
    if not key:
        key = _credential_key(home)
    if not key:
        key = input_func("OHM_API_KEY: ").strip()
    if not key:
        raise ValueError("OHM_API_KEY is required")
    return key


def install(
    *,
    key: str | None = None,
    home: Path | None = None,
    input_func: Callable[[str], str] = input,
) -> list[tuple[Path, bool]]:
    home = home or _home()
    resolved_key = _resolve_install_key(key, home=home, input_func=input_func)
    paths_and_mergers = [
        (home / ".cursor" / "hooks.json", _merge_cursor_hook),
        (home / ".claude" / "settings.json", _merge_claude_hook),
    ]
    results: list[tuple[Path, bool]] = []
    for path, merger in paths_and_mergers:
        value = _read_object(path)
        changed = merger(value)
        if changed or not path.exists():
            _write_object(path, value)
            changed = True
        results.append((path, changed))

    credentials_path = _credentials_path(home)
    credentials = _read_object(credentials_path)
    credentials_changed = credentials.get("api_key") != resolved_key
    if credentials_changed or not credentials_path.exists():
        credentials["api_key"] = resolved_key
        _write_object(credentials_path, credentials)
        credentials_changed = True
    results.append((credentials_path, credentials_changed))
    return results


def _run_install(args: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=f"{COMMAND} install")
    parser.add_argument("--key", help="Metrecept seat API key")
    parsed = parser.parse_args(args)
    try:
        results = install(key=parsed.key)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1

    changed = [str(path) for path, did_change in results if did_change]
    if changed:
        print("Metrecept true-tap configured:")
        for path in changed:
            print(f"- {path}")
    else:
        print("Metrecept true-tap already configured; no changes needed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["install"]:
        return _run_install(args[1:])

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            return 0
        post_tap(payload)
    except (json.JSONDecodeError, urllib.error.URLError, TimeoutError, OSError):
        return 0
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
