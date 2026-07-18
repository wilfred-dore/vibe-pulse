"""Render PlantUML sources as ASCII/Unicode diagrams in the terminal.

Primary: kroki.io (accepts the raw source via POST). Fallback: the official
PlantUML server /txt endpoint (raw-deflate + custom base64 encoding).
Both return plain text — perfect for a terminal agent. No dependencies.
"""

import urllib.request
import zlib

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
KROKI = "https://kroki.io/plantuml/txt"
PLANTUML = "https://www.plantuml.com/plantuml/txt/"
UA = "vibe-pulse/0.1 (terminal diagram renderer)"


def encode(source: str) -> str:
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    data = comp.compress(source.encode("utf-8")) + comp.flush()
    out = []
    for i in range(0, len(data), 3):
        b = list(data[i:i + 3]) + [0] * (3 - len(data[i:i + 3]))
        out.append(ALPHABET[b[0] >> 2])
        out.append(ALPHABET[((b[0] & 0x3) << 4) | (b[1] >> 4)])
        out.append(ALPHABET[((b[1] & 0xF) << 2) | (b[2] >> 6)])
        out.append(ALPHABET[b[2] & 0x3F])
    return "".join(out)


def _fetch(request: urllib.request.Request, timeout: float) -> str:
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace").rstrip()


def render(source: str, timeout: float = 20.0) -> str:
    try:
        return _fetch(urllib.request.Request(
            KROKI, data=source.encode("utf-8"),
            headers={"Content-Type": "text/plain", "User-Agent": UA},
            method="POST"), timeout)
    except Exception:
        pass
    try:
        return _fetch(urllib.request.Request(
            PLANTUML + encode(source), headers={"User-Agent": UA}), timeout)
    except Exception as err:
        return f"vibe-plot: no diagram server reachable ({err})"
