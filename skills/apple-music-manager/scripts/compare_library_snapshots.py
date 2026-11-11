#!/usr/bin/env python3
"""Build a read-only review plan from two Apple Music library snapshots."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON from {path}: {exc}") from exc


def tracks_from(payload: Any, path: Path) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        payload = payload["data"]
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} must contain a JSON list of song objects")
    return payload


def attrs(track: dict[str, Any]) -> dict[str, Any]:
    value = track.get("attributes", {})
    return value if isinstance(value, dict) else {}


def play_params(track: dict[str, Any]) -> dict[str, Any]:
    value = attrs(track).get("playParams", {})
    return value if isinstance(value, dict) else {}


def catalog_id(track: dict[str, Any]) -> str | None:
    params = play_params(track)
    value = params.get("catalogId")
    if value:
        return str(value)
    raw_id = track.get("id")
    if raw_id and not str(raw_id).startswith(("i.", "l.")):
        return str(raw_id)
    return None


def catalog_ids(track: dict[str, Any]) -> set[str]:
    params = play_params(track)
    meta = track.get("meta", {})
    meta = meta if isinstance(meta, dict) else {}
    values = (catalog_id(track), params.get("reportingId"), meta.get("redeliveryId"))
    return {str(value) for value in values if value}


def normalized(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(char for char in value if char.isalnum())


def identity(track: dict[str, Any]) -> tuple[str, str]:
    info = attrs(track)
    return normalized(info.get("name")), normalized(info.get("artistName"))


def summary(track: dict[str, Any]) -> dict[str, Any]:
    info = attrs(track)
    return {
        "library_id": track.get("id"),
        "catalog_id": catalog_id(track),
        "isrc": info.get("isrc"),
        "name": info.get("name"),
        "artist": info.get("artistName"),
        "album": info.get("albumName"),
    }


def compare(
    source: list[dict[str, Any]],
    target: list[dict[str, Any]],
    cache: dict[str, Any],
    source_label: str,
    target_label: str,
) -> dict[str, Any]:
    target_ids: dict[str, dict[str, Any]] = {}
    target_isrc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    target_title_artist: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for track in target:
        for cid in catalog_ids(track):
            target_ids[cid] = track
        isrc = str(attrs(track).get("isrc") or "").strip().upper()
        if isrc:
            target_isrc[isrc].append(track)
        key = identity(track)
        if all(key):
            target_title_artist[key].append(track)

    matched: list[dict[str, Any]] = []
    proposed: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    review_candidates: list[dict[str, Any]] = []
    album_review: list[dict[str, Any]] = []
    methods: dict[str, int] = defaultdict(int)

    for track in source:
        item = summary(track)
        source_id = item["catalog_id"]
        mapped_value = cache.get(source_id) if source_id else None
        mapped_id = str(mapped_value) if mapped_value else None
        direct_id = mapped_id or source_id
        isrc = str(item["isrc"] or "").strip().upper()
        found: dict[str, Any] | None = target_ids.get(direct_id) if direct_id else None
        method = "resolution_cache" if found and mapped_id else "catalog_id"
        if not found and isrc and target_isrc.get(isrc):
            found = target_isrc[isrc][0]
            method = "isrc"

        if found:
            methods[method] += 1
            matched.append({"source": item, "target": summary(found), "method": method})
            source_album = normalized(item["album"])
            target_album = normalized(attrs(found).get("albumName"))
            if source_album and target_album and source_album != target_album:
                album_review.append({
                    "source": item,
                    "target": summary(found),
                    "reason": "same catalog ID or ISRC, but album titles differ; confirm the recording/release is intended",
                })
            continue

        title_matches = target_title_artist.get(identity(track), []) if all(identity(track)) else []
        if title_matches:
            review_candidates.append({
                "source": item,
                "candidates": [summary(candidate) for candidate in title_matches],
                "reason": "title and artist match, but catalog ID and ISRC did not confirm the same recording",
            })

        if mapped_id:
            proposed.append({
                "source": item,
                "target_catalog_id": mapped_id,
                "status": "candidate_add_review_required",
            })
        else:
            unresolved.append({
                "source": item,
                "reason": "no confirmed target match or storefront catalog ID mapping",
            })

    return {
        "mode": "read_only_review_plan",
        "source": {"label": source_label, "track_count": len(source)},
        "target": {"label": target_label, "track_count": len(target)},
        "matched_count": len(matched),
        "matched_by": dict(methods),
        "proposed_adds": proposed,
        "unresolved": unresolved,
        "review_candidates": review_candidates,
        "album_review": album_review,
        "note": "No account changes were made. Review every proposed add, unresolved match, and album difference before any write.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Source library song snapshot JSON")
    parser.add_argument("--target", required=True, type=Path, help="Target library song snapshot JSON")
    parser.add_argument("--cache", type=Path, help="Optional source catalog ID to target catalog ID JSON map")
    parser.add_argument("--source-label", default="source")
    parser.add_argument("--target-label", default="target")
    parser.add_argument("--output", type=Path, help="Write the plan here; defaults to stdout")
    args = parser.parse_args()

    try:
        source = tracks_from(read_json(args.source), args.source)
        target = tracks_from(read_json(args.target), args.target)
        cache = read_json(args.cache) if args.cache else {}
        if not isinstance(cache, dict):
            raise ValueError(f"{args.cache} must contain a JSON object")
        plan = compare(source, target, cache, args.source_label, args.target_label)
        rendered = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
