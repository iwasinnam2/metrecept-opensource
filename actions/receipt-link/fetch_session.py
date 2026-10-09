#!/usr/bin/env python3
"""GET /v1/sessions/{id} and write the PR comment markdown. Stdlib only.

Env:  METRECEPT_API_KEY  (required)
Args: --api-base https://api.metrecept.co.uk --session-id <id> --out comment.md

Exit 0 and write a comment in every reachable case, including a session with
zero events (the comment then says so). Exit 1 only when the API is
unreachable or rejects the key; the action step surfaces that line.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comment_body import build_comment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="https://api.metrecept.co.uk")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    key = os.environ.get("METRECEPT_API_KEY", "").strip()
    if not key:
        print("receipt-link: METRECEPT_API_KEY is not set", file=sys.stderr)
        return 1

    url = args.api_base.rstrip("/") + "/v1/sessions/" + urllib.parse.quote(args.session_id, safe="")
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json",
                 "User-Agent": "metrecept-receipt-link-action/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            session = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"receipt-link: {url} returned HTTP {exc.code}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"receipt-link: could not reach {url} ({exc})", file=sys.stderr)
        return 1

    Path(args.out).write_text(build_comment(session), encoding="utf-8")
    print(f"receipt-link: wrote {args.out} (event_count={session.get('event_count')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
