#!/usr/bin/env python3
"""Compare expected and actual playlist snapshots without contacting Apple Music."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON from {path}: {exc}") from exc


def tracks_from(payload: Any, path: Path) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("tracks"), list):
            payload = payload["tracks"]
        elif isinstance(payload.get("data"), list):
            payload = payload["data"]
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} must be a playlist object with tracks or a JSON list of song objects")
    return payload


def track_info(track: dict[str, Any]) -> dict[str, Any]:
    attributes = track.get("attributes", {})
    attributes = attributes if isinstance(attributes, dict) else {}
    params = attributes.get("playParams", {})
    params = params if isinstance(params, dict) else {}
    meta = track.get("meta", {})
    meta = meta if isinstance(meta, dict) else {}
    cid = params.get("catalogId") or meta.get("redeliveryId")
    if not cid and track.get("id") and not str(track["id"]).startswith(("i.", "l.")):
        cid = track["id"]
    return {
        "library_id": track.get("id"),
        "catalog_id": str(cid) if cid else None,
        "catalog_ids": [str(value) for value in (params.get("catalogId"), params.get("reportingId"), meta.get("redeliveryId"), track.get("id")) if value and not str(value).startswith(("i.", "l."))],
        "isrc": str(attributes.get("isrc") or "").strip().upper() or None,
        "name": attributes.get("name"),
        "artist": attributes.get("artistName"),
    }


def verify(expected: list[dict[str, Any]], actual: list[dict[str, Any]], cache: dict[str, Any], labels: tuple[str, str]) -> dict[str, Any]:
    actual_info = [track_info(track) for track in actual]
    used: set[int] = set()
    matched = []
    missing = []
    positions = []

    for expected_track in expected:
        item = track_info(expected_track)
        mapped = cache.get(item["catalog_id"]) if item["catalog_id"] else None
        wanted_id = str(mapped or item["catalog_id"]) if (mapped or item["catalog_id"]) else None
        found_index = None
        method = None
        if wanted_id:
            found_index = next((i for i, candidate in enumerate(actual_info)
                                if i not in used and wanted_id in candidate["catalog_ids"]), None)
            if found_index is not None:
                method = "resolution_cache" if mapped else "catalog_id"
        if found_index is None and item["isrc"]:
            found_index = next((i for i, candidate in enumerate(actual_info)
                                if i not in used and candidate["isrc"] == item["isrc"]), None)
            if found_index is not None:
                method = "isrc"
        if found_index is None:
            missing.append(item)
        else:
            used.add(found_index)
            positions.append(found_index)
            matched.append({"expected": item, "actual": actual_info[found_index], "actual_position": found_index, "method": method})

    extra = [{"position": i, "track": item} for i, item in enumerate(actual_info) if i not in used]
    seen: set[tuple[str, str]] = set()
    duplicates = []
    for i, item in enumerate(actual_info):
        key = ("isrc", item["isrc"]) if item["isrc"] else ("catalog_id", item["catalog_id"] or "")
        if not key[1]:
            continue
        if key in seen:
            duplicates.append({"position": i, "track": item})
        seen.add(key)

    membership_verified = not missing and not extra
    order_verified = membership_verified and positions == list(range(len(expected))) and len(actual) == len(expected)
    return {
        "mode": "read_only_playlist_verification",
        "expected_label": labels[0],
        "actual_label": labels[1],
        "expected_count": len(expected),
        "actual_count": len(actual),
        "matched_count": len(matched),
        "membership_verified": membership_verified,
        "order_verified": order_verified,
        "complete": membership_verified and order_verified,
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "note": "No account changes were made. Matches use catalog IDs, the supplied ID map, or ISRC; title and artist alone are not treated as proof.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", required=True, type=Path, help="Expected playlist object or song-list JSON")
    parser.add_argument("--actual", required=True, type=Path, help="Fresh actual playlist object or song-list JSON")
    parser.add_argument("--cache", type=Path, help="Optional expected catalog ID to actual catalog ID JSON map")
    parser.add_argument("--expected-label", default="expected")
    parser.add_argument("--actual-label", default="actual")
    parser.add_argument("--output", type=Path, help="Write the report here; defaults to stdout")
    args = parser.parse_args()
    try:
        expected = tracks_from(load_json(args.expected), args.expected)
        actual = tracks_from(load_json(args.actual), args.actual)
        cache = load_json(args.cache) if args.cache else {}
        if not isinstance(cache, dict):
            raise ValueError(f"{args.cache} must contain a JSON object")
        report = verify(expected, actual, cache, (args.expected_label, args.actual_label))
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
