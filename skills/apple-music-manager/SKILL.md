---
name: apple-music-manager
description: Inspect and manage Apple Music libraries, playlists, catalog matches, and snapshots through a configured Apple Music MCP server or the included offline tools. Use for read-only audits and carefully reviewed account changes.
---

# Apple Music Library and Playlist Workflows

Use the configured Apple Music MCP for supported catalog, library, and playlist operations. Confirm which storefront/profile is active before reading or writing: a result from one storefront does not verify another. Catalog search covers the storefront catalog; library search is limited to the signed-in user's library. MCP setup varies by client, so follow the client's instructions for registering this repository's local server.

## Setup and Profiles

Install `uv` and authenticate the local `applemusic-mcp` server:

```sh
uvx applemusic-mcp login
uvx applemusic-mcp status
uvx applemusic-mcp serve --level full
```

The root `mcp.json` shows a local stdio server entry. Clients may require manual MCP registration. Keep credentials in the MCP's local configuration; never copy tokens into the repository, logs, or chat. For multiple storefronts, configure isolated profiles/data directories and distinct server instances using the MCP's supported options and your client's registration format. Verify each profile with `status` and a harmless catalog lookup. If browser sign-in is unavailable in a headless environment, use a trusted local desktop sign-in flow; do not share passwords in chat.

## Matching and Freshness

Prefer confirmed identity in this order: reviewed source-to-target ID mapping, direct catalog ID, reporting/redelivery ID, and ISRC. Title-and-artist similarity is only a review hint because recordings, edits, remasters, and releases can differ. Use the active storefront's catalog ID when adding an item. Report album differences for review and leave ambiguous tracks unresolved.

After adding an album or batch, allow time for indexing and fetch a fresh full target-library snapshot before reporting omissions. Keep confirmed matches, unresolved candidates, and confirmed regional unavailability separate. A failed search or an ID missing from an old snapshot does not prove regional unavailability.

## Safe Changes and Verification

Before a bulk write or deletion, identify the target profile, fetch current state, and make the exact proposed changes reviewable. Obtain approval for a broad destructive candidate list unless that same scope was already authorized. Preserve account-only content unless its removal is explicitly requested. If clearing or deleting a playlist fails, stop before repopulating it. Treat throttling and transient failures cautiously; check whether an earlier request took effect before retrying.

An accepted API response does not prove that a library or playlist changed. Refetch live state after writes and verify item identity, membership, order, duplicates, extras, and counts against the intended result. Do not report completion from request status, logs, or counts alone. Use another authorized client surface only when the MCP operation is unavailable, and still verify live state. Treat automatically managed or editorial content as read-only unless the user explicitly requests an applicable change.

## Offline Snapshot Tools

Both included Python 3.10+ scripts operate only on supplied JSON and never contact Apple Music. Review their reports before any account write.

Compare source and target library snapshots:

```sh
python3 skills/apple-music-manager/scripts/compare_library_snapshots.py \
  --source source-library.json --target target-library.json \
  --cache reviewed-id-map.json --output library-review-plan.json
```

Inspect `proposed_adds`, `unresolved`, `review_candidates`, and `album_review`; proposed adds require review. The output contract is [library-review-plan.schema.json](assets/library-review-plan.schema.json).

Verify expected and freshly fetched playlist snapshots:

```sh
python3 skills/apple-music-manager/scripts/verify_playlist_snapshots.py \
  --expected expected-playlist.json --actual current-playlist.json \
  --cache reviewed-id-map.json --output playlist-verification.json
```

It checks identity, membership, order, extras, and duplicates using catalog IDs, the ID map, or ISRC—not title and artist alone. See [playlist-verification.schema.json](assets/playlist-verification.schema.json). Small synthetic input examples are in [`tests/fixtures`](../../tests/fixtures).
