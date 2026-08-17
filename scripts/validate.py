"""Validate widgets.json the way a Tesserae server will read it.

Four checks, in the order that catches mistakes earliest:

  1. The index matches ``schema/marketplace.schema.json``.
  2. No ASCII-escaped characters — the file keeps em-dashes and accents
     literal, so a scripted edit that re-serialises with ``ensure_ascii=True``
     doesn't churn every entry it never touched.
  3. Every screenshot an entry declares exists and really is a PNG.
  4. Every release tarball is fetchable, hashes to the pinned sha256, and (when
     the entry declares ``folders``) contains exactly those plugin folders —
     the same layout detection ``app/marketplace.py`` does on install.

Run it with ``mise run validate``. ``--offline`` skips the network checks.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TIMEOUT_S = 30


def detect_layout(buf: bytes, primary_id: str) -> list[str]:
    """Mirror ``_detect_layout``: unwrap one GitHub-style envelope, then either
    single-widget (``plugin.json`` at the root) or bundle (subfolders that each
    hold one)."""
    with tarfile.open(fileobj=io.BytesIO(buf), mode="r:*") as tar:
        names = [m.name for m in tar.getmembers() if not m.isdir()]
    top = sorted({n.split("/", 1)[0] for n in names if "/" in n})
    prefix = f"{top[0]}/" if len(top) == 1 and all("/" in n for n in names) else ""
    stripped = [n[len(prefix) :] for n in names]
    if "plugin.json" in stripped:
        return [primary_id]
    return sorted(
        n.split("/", 1)[0]
        for n in stripped
        if n.endswith("/plugin.json") and n.count("/") == 1
    )


def check_screenshots(entry: dict, failures: list[str]) -> None:
    wid = entry["id"]
    names = [f"{size}.png" for size in entry.get("screenshot_sizes", [])]
    names += [f"extra-{n}.png" for n in range(1, int(entry.get("extra_screenshot_count") or 0) + 1)]
    for name in names:
        path = ROOT / "screenshots" / wid / name
        if not path.exists():
            failures.append(f"{wid}: missing screenshot {path.relative_to(ROOT)}")
        elif path.read_bytes()[:8] != PNG_MAGIC:
            failures.append(f"{wid}: {path.relative_to(ROOT)} is not a PNG")


def check_release(entry: dict, failures: list[str]) -> None:
    wid = entry["id"]
    release = entry["release"]
    try:
        with urllib.request.urlopen(release["tarball_url"], timeout=TIMEOUT_S) as resp:
            body = resp.read()
    except Exception as err:  # noqa: BLE001 - any transport failure is one failure line
        failures.append(f"{wid}: tarball fetch failed: {err}")
        return

    actual = hashlib.sha256(body).hexdigest()
    if actual != release["sha256"].lower():
        failures.append(
            f"{wid}: sha256 mismatch (declared {release['sha256'][:12]}…, got {actual[:12]}…)"
        )
        return

    if "folders" in entry and entry.get("kind") != "theme":
        declared = sorted(entry["folders"])
        try:
            found = detect_layout(body, wid)
        except Exception as err:  # noqa: BLE001
            failures.append(f"{wid}: could not read tarball: {err}")
            return
        if declared != found:
            failures.append(f"{wid}: declares folders {declared} but tarball has {found}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="skip tarball fetch + hash checks")
    args = parser.parse_args()

    raw = (ROOT / "widgets.json").read_text(encoding="utf-8")
    index = json.loads(raw)

    try:
        import jsonschema
    except ModuleNotFoundError:
        print("jsonschema is missing; run 'mise install' or 'uv pip install jsonschema'")
        return 2
    jsonschema.validate(index, json.loads((ROOT / "schema/marketplace.schema.json").read_text()))

    failures: list[str] = []
    escaped = re.findall(r"\\u[0-9a-fA-F]{4}", raw)
    if escaped:
        failures.append(
            f"widgets.json has {len(escaped)} ASCII-escaped character(s), first {escaped[0]}. "
            "Edit the file directly, or pass ensure_ascii=False when scripting it."
        )

    entries = index.get("widgets", [])
    for entry in entries:
        check_screenshots(entry, failures)
        if not args.offline:
            check_release(entry, failures)

    if failures:
        print("\n".join(failures))
        return 1
    scope = "offline" if args.offline else "with tarballs"
    print(f"OK: {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} validated ({scope})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
