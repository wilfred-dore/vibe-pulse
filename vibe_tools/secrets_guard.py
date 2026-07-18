"""Vibe pre_tool hook: refuse to read secrets files.

Registered in .vibe/hooks.toml. Receives the PreToolInvocation JSON on
stdin; exiting with code 2 and a JSON deny decision blocks the tool call.
"""

import json
import sys

BLOCKED = ("secret", ".env", "credential", "api_key", "apikey", "token")


def main() -> None:
    inv = json.load(sys.stdin)
    args = inv.get("tool_input") or {}
    haystack = json.dumps(args).lower()
    if any(pattern in haystack for pattern in BLOCKED):
        print(json.dumps({
            "decision": "deny",
            "reason": ("secrets-guard: this file looks like it contains "
                       "credentials; refusing to read it."),
        }))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # never break the agent on guard failure
